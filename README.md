# Week 7 — Challenge A: Persistent Memory

**Bản nộp: Ngô Hoàng Khang — 24520748 — SE373**

Agent ghi nhớ quy ước dự án qua nhiều cuộc trò chuyện và sử dụng quy ước mới
sau khi người dùng cập nhật. Project dùng Python, LangChain và Streamlit,
dựa trên nền Agent Tools & Skills Lab, stage 04.

## Cấu trúc source

| File/thư mục | Chức năng |
|---|---|
| `memory_ui.py` | Giao diện chat, các bước model/tool calls, panel State & Context và file đầu ra |
| `agent.py` | Khởi tạo model, đăng ký tools, build agent và nạp memory vào system prompt |
| `prompts.py` | Hướng dẫn agent sử dụng skills, áp dụng và cập nhật memory |
| `config.py` | Cấu hình model/API và giới hạn thực thi |
| `paths.py` | Đường dẫn workspace, traces và file memory |
| `observer.py` | Quan sát request, tool execution, usage và context |
| `trace.py` | Ghi trace phục vụ kiểm tra |
| `skill_catalog.py` | Quét metadata các skill trong workspace |
| `tools/` | Công cụ đọc/ghi file và chạy Bash |
| `workspace/` | Dữ liệu, skills và output khi agent chạy |
| `fixtures/` | Dữ liệu mẫu để khởi tạo workspace |
| `run_memory_demo.py` | Demo tự động 4 session, baseline và lưu bằng chứng |
| `reset_workspace.py` | Khôi phục workspace từ fixtures |
| `tests/` | Kiểm thử tools, agent, giao diện và kiểm tra memory |

## Cơ chế persistent memory

1. Người dùng cung cấp quy ước, agent ghi vào `workspace/output/MEMORY.md` bằng tool.
2. Mỗi lượt chat, harness đọc lại file và inject vào system prompt trong khối `<memory>`.
3. Nút **Session mới** xóa lịch sử chat nhưng giữ memory trên đĩa.
4. Khi đổi quy ước, agent cập nhật phần **Đang hiệu lực** và chuyển quy ước cũ
   xuống phần **Đã thay thế**. Agent được hướng dẫn chỉ áp dụng phần đang hiệu lực.

File memory được đưa vào prompt cùng lịch sử thay thế; việc ưu tiên quy ước active
được điều khiển bằng hướng dẫn, không phải bộ lọc JSON riêng.

## Cài đặt

Yêu cầu Python 3.11 trở lên. Tại thư mục project:

```powershell
python -m uv sync --locked --python 3.11
```

Chỉ tạo `.env` nếu chưa có, sau đó tự điền cấu hình:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Các biến cấu hình: `OPENAI_API_KEY`, `MODEL_NAME`, `OPENAI_BASE_URL`.
Model và endpoint phải hỗ trợ tool calling. Không đưa API key lên GitHub.

## Chạy giao diện

```powershell
.\.venv\Scripts\python.exe -m streamlit run memory_ui.py --server.address 127.0.0.1 --server.port 8501
```

Mở http://127.0.0.1:8501. Nếu cổng đang dùng, dừng server cũ hoặc đổi port.
Lệnh trên không yêu cầu kích hoạt `.venv` và không cần cài uv bên trong `.venv`.

## Kịch bản 4 session

Giữa mỗi bước, bấm **Session mới**.

**Session 1 — dạy quy ước:**

```text
Ghi nhớ quy ước dự án: mã dự án LAB-AGENT, ngày trong báo cáo dùng DD/MM/YYYY.
```

**Session 2 — tạo báo cáo, không nhắc lại quy ước:**

```text
Đọc data/weekly_notes.md, tạo báo cáo tuần và lưu vào output/weekly-report.md.
```

Kiểm tra mã LAB-AGENT và ngày DD/MM/YYYY. Lưu báo cáo trước khi ghi đè ở bước sau.

**Session 3 — cập nhật:**

```text
Đổi mã dự án thành LAB-MEMORY và định dạng ngày báo cáo sang MM/DD/YYYY. Lưu quy ước mới, đánh dấu quy ước cũ đã thay thế.
```

**Session 4:** nhập lại yêu cầu session 2. Kiểm tra mã LAB-MEMORY,
ngày MM/DD/YYYY và memory thực sự inject trong system prompt.

Chỉ xác nhận hoàn thành sau khi tool ghi file thành công và nội dung file đúng.
Tải báo cáo tại phần **File đầu ra**; lưu snapshot/context làm bằng chứng.

## Demo tự động và test

```powershell
.\.venv\Scripts\python.exe run_memory_demo.py
.\.venv\Scripts\python.exe run_memory_demo.py baseline
.\.venv\Scripts\python.exe run_memory_demo.py all
.\.venv\Scripts\python.exe -m pytest -q
```

**Demo gọi API, có thể phát sinh phí.** Script sao lưu output vào evidence rồi xóa
output hiện tại để chạy demo; lưu riêng các báo cáo cần giữ trước khi chạy.
Các session báo cáo trong demo xóa report cũ để cô lập ảnh hưởng của memory.
Bằng chứng được lưu dưới `evidence/demo_runs/`.

Kiểm tra sau đổi tên entry point: 14 test đạt, 2 test liên quan Bash lỗi trên Windows.
Chưa xác nhận lại demo API thật sau đổi tên. Tests dùng model giả không thay thế
bằng chứng LLM thực tế. Chạy lại để lấy bằng chứng của bản nộp hiện tại.

## Lưu ý

- Bash và một số test/script cần POSIX/WSL; không bảo đảm chạy hoàn toàn trên Windows.
- `reset_workspace.py` xóa workspace có marker để khôi phục dữ liệu mẫu; sao lưu trước khi dùng.
- Đổi `.env` có thể cần dừng hẳn server rồi khởi động lại.
- `.gitignore` loại `.env`, `.venv`, caches, traces, output và evidence khỏi commit mới.
  File đã được Git track trước đó không tự bị loại bởi `.gitignore`.
- Kiểm tra `git status` và danh sách file stage trước khi push. Không upload key,
  dữ liệu riêng tư hoặc ghi kết quả kiểm thử chưa thực sự chạy.
