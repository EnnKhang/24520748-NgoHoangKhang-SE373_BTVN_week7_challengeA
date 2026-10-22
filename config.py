"""Cấu hình project: hằng số hiển thị, giới hạn thực thi và settings đọc từ .env."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

import paths

PROJECT_NAME = "challenge-a-persistent-memory"
APP_TITLE = "Challenge A: persistent memory"
CAPABILITY_TEXT = (
    "Mục tiêu: agent nhớ được quy ước dự án qua nhiều session, và cập nhật khi quy ước thay đổi. "
    "Memory: workspace/output/MEMORY.md, nạp vào system prompt ở mọi session. "
    "Agent dùng lại stage 04: read_file, write_file, bash, skill weekly-report và csv-quality."
)
DEMO_GUIDE = """**Chứng minh 1**: session mới vẫn dùng đúng quy ước đã thống nhất
1. Gõ: `Quy ước dự án từ nay: mọi báo cáo phải bắt đầu bằng dòng "Mã dự án: LAB-AGENT", mọi ngày viết dạng DD/MM/YYYY.`
2. Bấm **Session mới**, gõ: `Tạo báo cáo tuần.` → báo cáo có `Mã dự án: LAB-AGENT`, ngày DD/MM/YYYY.

**Chứng minh 2**: quy ước đổi thì các session sau dùng quy ước mới
3. Bấm **Session mới**, gõ: `Quy ước dự án thay đổi: mã dự án đổi thành LAB-MEMORY, mọi ngày viết dạng MM/DD/YYYY.`
4. Bấm **Session mới**, gõ: `Tạo báo cáo tuần.` → báo cáo có `Mã dự án: LAB-MEMORY`, ngày MM/DD/YYYY.

Theo dõi panel **Memory dự án** bên phải sau mỗi bước."""

# Giới hạn số lần gọi model trong một lượt chat (ModelCallLimitMiddleware).
MODEL_CALL_LIMIT = 8
# Giới hạn số tool calls trong một lượt chat (ToolCallLimitMiddleware).
TOOL_CALL_LIMIT = 20
# Giới hạn số bước của LangGraph (recursion limit), không phải số tool calls.
RECURSION_LIMIT = 50


@dataclass(frozen=True)
class Settings:
    api_key: str
    model_name: str
    base_url: str | None


def load_settings() -> tuple[Settings | None, list[str]]:
    """Đọc .env của project này. Trả (settings, []) hoặc (None, danh sách biến còn thiếu)."""
    load_dotenv(paths.ENV_PATH, override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model_name = os.getenv("MODEL_NAME", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    missing = [name for name, value in (("OPENAI_API_KEY", api_key), ("MODEL_NAME", model_name)) if not value]
    if missing:
        return None, missing
    return Settings(api_key=api_key, model_name=model_name, base_url=base_url), []
