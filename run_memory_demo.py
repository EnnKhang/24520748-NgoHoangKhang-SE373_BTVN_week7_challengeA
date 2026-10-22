"""Demo Challenge A (persistent memory) với model thật trong .env.

Mỗi session = một lần gọi agent với lịch sử rỗng (giống bấm "Cuộc trò chuyện mới").
Kịch bản: A dạy quy ước -> B tạo báo cáo (chứng minh 1) -> C đổi quy ước (memory phải chuyển quy ước cũ
xuống "Đã thay thế", không xóa; slide 12) -> D tạo báo cáo (chứng minh 2).
Chạy ở hai chế độ: memory (MEMORY.md trong system prompt) và baseline (agent gốc, không memory).
Trước mỗi session tạo báo cáo, report cũ bị xóa (MEMORY.md giữ nguyên) để kết quả chỉ phụ thuộc memory.
Mỗi lần chạy xóa workspace/output/ (bản cũ được copy vào bằng chứng), lưu bằng chứng ở evidence/demo_runs/<thời gian>/.

    uv run python run_memory_demo.py            # chỉ chế độ memory (~15 request model)
    uv run python run_memory_demo.py baseline   # chỉ baseline
    uv run python run_memory_demo.py all        # cả hai, rồi in bảng so sánh
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage

import paths
from agent import build_agent, build_model, system_prompt
from config import RECURSION_LIMIT, load_settings

OUTPUT_DIR = paths.WORKSPACE_DIR / paths.OUTPUT_SUBDIR
REPORT = OUTPUT_DIR / "weekly-report.md"
RUNS_DIR = paths.PROJECT_ROOT / "evidence" / "demo_runs"

# Ngày trong data/weekly_notes.md; báo cáo phải viết chúng theo đúng định dạng của quy ước.
SOURCE_DATES = [(2026, 9, 28), (2026, 9, 29), (2026, 9, 30), (2026, 10, 1), (2026, 10, 2)]
DATE_FORMATS = {"DD/MM/YYYY": "{d:02}/{m:02}/{y}", "MM/DD/YYYY": "{m:02}/{d:02}/{y}", "YYYY-MM-DD": "{y}-{m:02}-{d:02}"}

TEACH_1 = 'Quy ước dự án từ nay: mọi báo cáo phải bắt đầu bằng dòng "Mã dự án: LAB-AGENT", mọi ngày viết dạng DD/MM/YYYY.'
TEACH_2 = 'Quy ước dự án thay đổi: mã dự án đổi thành LAB-MEMORY, mọi ngày viết dạng MM/DD/YYYY.'
TASK = "Tạo báo cáo tuần."

# (tên session, tin nhắn, tên check, hàm check trả danh sách vi phạm); None, None = không kiểm tra
SCENARIO = [
    ("Session A", TEACH_1, None, None),
    ("Session B", TASK, "Chứng minh 1", lambda: check_report("LAB-AGENT", "DD/MM/YYYY")),
    ("Session C", TEACH_2, "Memory đánh dấu quy ước cũ",
     lambda: check_memory(active=["LAB-MEMORY", "MM/DD/YYYY"], superseded=["LAB-AGENT", "DD/MM/YYYY"])),
    ("Session D", TASK, "Chứng minh 2", lambda: check_report("LAB-MEMORY", "MM/DD/YYYY")),
]


def check_report(code: str, date_format: str) -> list[str]:
    """Danh sách vi phạm quy ước trong output/weekly-report.md; rỗng = đạt."""
    if not REPORT.is_file():
        return ["không có output/weekly-report.md"]
    text = REPORT.read_text(encoding="utf-8")
    problems = []
    first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
    if first_line != f"Mã dự án: {code}":
        problems.append(f"dòng đầu là {first_line!r}, cần 'Mã dự án: {code}'")
    expected_hits = 0
    for y, m, d in SOURCE_DATES:
        for name, pattern in DATE_FORMATS.items():
            value = pattern.format(y=y, m=m, d=d)
            if value in text:
                if name == date_format:
                    expected_hits += 1
                else:
                    problems.append(f"ngày {y}-{m:02}-{d:02} viết sai dạng: {value} ({name})")
    if expected_hits == 0:
        problems.append(f"không có ngày nào của nguồn theo dạng {date_format}")
    return problems


def check_memory(active: list[str], superseded: list[str]) -> list[str]:
    """Quy ước mới nằm ở mục đang hiệu lực; quy ước cũ chuyển xuống "## Đã thay thế", không bị xóa (slide 12)."""
    path = OUTPUT_DIR / "MEMORY.md"
    if not path.is_file():
        return ["không có output/MEMORY.md"]
    current, _, history = path.read_text(encoding="utf-8").partition("## Đã thay thế")
    problems = [f"mục đang hiệu lực thiếu {v}" for v in active if v not in current]
    problems += [f"{v} vẫn nằm trong mục đang hiệu lực" for v in superseded if v in current]
    problems += [f"{v} bị xóa thay vì chuyển xuống '## Đã thay thế'" for v in superseded if v not in history]
    return problems


def run_session(settings, memory: bool, text: str) -> tuple[str, list[str]]:
    """Một session mới: lịch sử chỉ có tin nhắn này. Trả (câu trả lời cuối, danh sách tool call)."""
    for attempt in range(3):
        try:
            agent = build_agent(build_model(settings), memory=memory)
            result = agent.invoke({"messages": [HumanMessage(content=text)]}, config={"recursion_limit": RECURSION_LIMIT})
            break
        except Exception as exc:  # free model hay bị 429; chờ rồi thử lại
            if attempt == 2 or "429" not in str(exc):
                raise
            print(f"    (bị giới hạn tốc độ, chờ 60s rồi thử lại: {str(exc)[:100]})")
            time.sleep(60)
    messages = result["messages"]
    calls = [
        f"{call['name']}({json.dumps(call['args'], ensure_ascii=False)[:90]})"
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    ]
    answer = next((m.text for m in reversed(messages) if isinstance(m, AIMessage) and not m.tool_calls), "")
    return answer, calls


def clear_output(evidence_dir) -> None:
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        shutil.copytree(OUTPUT_DIR, evidence_dir, dirs_exist_ok=True)
    for child in OUTPUT_DIR.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()


def run_mode(settings, memory: bool, run_dir) -> dict[str, bool]:
    mode = "memory" if memory else "baseline"
    title = "SAU KHI SỬA: có memory" if memory else "BASELINE: agent gốc, không memory"
    print(f"\n{'=' * 78}\n {title}\n{'=' * 78}")
    clear_output(run_dir / mode / "00-output-truoc-khi-chay")
    results = {}
    for index, (session, text, name, check) in enumerate(SCENARIO, start=1):
        prompt = system_prompt(memory)
        print(f"\n--- {session} (cuộc trò chuyện mới, lịch sử rỗng) ---")
        injected = prompt.rpartition("<memory>")[2].partition("</memory>")[0].strip() if memory else "(baseline: không inject)"
        print("  Memory đã inject vào system prompt:\n    " + injected.replace("\n", "\n    "))
        if text == TASK and REPORT.is_file():
            # ponytail: report cũ (theo quy ước cũ) bị model chép lại thay vì theo memory; xóa để chỉ đo memory
            REPORT.unlink()
            print("  (đã xóa output/weekly-report.md cũ; output/MEMORY.md giữ nguyên)")
        print(f"  User: {text}")
        answer, calls = run_session(settings, memory, text)
        print(f"  Tool calls ({len(calls)}):")
        for call in calls:
            print(f"    - {call}")
        print(f"  Agent: {answer.strip()[:300]}")
        step_dir = run_dir / mode / f"{index:02}-{session.replace(' ', '-')}"
        step_dir.mkdir(parents=True)
        (step_dir / "system_prompt.md").write_text(prompt, encoding="utf-8")
        (step_dir / "transcript.md").write_text(
            f"User: {text}\n\nTool calls:\n" + "".join(f"- {c}\n" for c in calls) + f"\nAgent:\n{answer}\n", encoding="utf-8"
        )
        if OUTPUT_DIR.exists():
            shutil.copytree(OUTPUT_DIR, step_dir / "output")
        memory_file = OUTPUT_DIR / "MEMORY.md"
        if memory and memory_file.is_file():
            print("  output/MEMORY.md sau session:\n    " + memory_file.read_text(encoding="utf-8").strip().replace("\n", "\n    "))
        if check:
            problems = check()
            results[name] = not problems
            print(f"\n  >>> {name} [{mode}]: {'PASS' if not problems else 'FAIL'}")
            for problem in problems:
                print(f"      - {problem}")
    return results


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    choice = sys.argv[1] if len(sys.argv) > 1 else "memory"
    modes = {"memory": [True], "baseline": [False], "all": [False, True]}.get(choice)
    if modes is None:
        sys.exit("Dùng: python run_memory_demo.py [memory|baseline|all]")
    settings, missing = load_settings()
    if settings is None:
        sys.exit(f"Thiếu cấu hình trong .env: {', '.join(missing)}")
    run_dir = RUNS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"Model: {settings.model_name} | Bằng chứng: {run_dir}")
    summary = {("memory" if m else "baseline"): run_mode(settings, m, run_dir) for m in modes}

    lines = ["| | " + " | ".join(summary) + " |", "|---|" + "---|" * len(summary)]
    for name in (name for _, _, name, check in SCENARIO if check):
        lines.append(f"| {name} | " + " | ".join("PASS" if r.get(name) else "FAIL" for r in summary.values()) + " |")
    table = "\n".join(lines)
    print(f"\n{'=' * 78}\n KẾT QUẢ\n{'=' * 78}\n{table}")
    (run_dir / "summary.md").write_text(f"# Challenge A: persistent memory\n\nModel: `{settings.model_name}`\n\n{table}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
