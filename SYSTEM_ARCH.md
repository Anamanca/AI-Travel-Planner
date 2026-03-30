# AI Travel Planner - System Architecture & Multi-Agent Design

Tài liệu này tổng hợp cấu trúc và nguyên lý hoạt động của hệ thống AI Travel Planner, được xây dựng trên nền tảng LangGraph, LangChain và Telegram Bot API.

---

## 1. Triết lý Thiết kế (Design Philosophy)
Hệ thống được thiết kế theo mô hình **"Research -> Evaluate -> Report -> Interact"**. Thay vì sử dụng một LLM duy nhất xử lý mọi thứ, chúng ta chia nhỏ nhiệm vụ cho các **Specialist Agents** (Tác nhân chuyên biệt) để tăng độ chính xác và khả năng kiểm soát dữ liệu.

## 2. Công nghệ lõi (Core Tech Stack)
- **Orchestration (Điều phối):** [LangGraph](https://github.com/langchain-ai/langgraph) - Quản lý trạng thái (state) và luồng công việc phức tạp, cho phép lặp lại (loop) và rẽ nhánh.
- **LLM Engine:** Gemini 3 Flash (thông qua **9Router** proxy) sử dụng class `crewai.LLM`.
- **Search & Scraping:** 
    - **Tavily:** Tìm kiếm web chuyên sâu cho Travel.
    - **Apify:** Cào dữ liệu mạng xã hội (TikTok, Facebook) để lấy thông tin thực tế từ cộng đồng.
- **Interface:** `python-telegram-bot` với cơ chế `ConversationHandler`.
- **Reporting:** `fpdf2` để xuất file PDF hỗ trợ Unicode (Tiếng Việt).

---

## 3. Hệ thống Multi-Agent (The Agents Team)

Hệ thống bao gồm các Agent sau:

| Agent | Vai trò | Công cụ sử dụng |
| :--- | :--- | :--- |
| **InfoExtractorAgent** | Đọc hiểu tin nhắn tự do của user, bóc tách JSON (điểm đi, điểm đến, ngày tháng...). | LLM |
| **TransportAgent** | Tìm kiếm vé máy bay, xe khách dựa trên lộ trình. | Tavily Search |
| **DiscoveryAgent** | Tìm kiếm món ngon và địa điểm vui chơi từ mạng xã hội. | Apify (TikTok/FB) |
| **WeatherAgent** | Dự báo thời tiết tại điểm đến. | Tavily Search |
| **EvaluatorAgent** | Kiểm tra chất lượng dữ liệu của các agent khác (có đủ 3 phân khúc Low/Mid/High không). | LLM |
| **ReportingAgent** | Tổng hợp toàn bộ kết quả thành báo cáo Markdown chuyên nghiệp. | LLM |
| **IntentAgent** | Phân tích yêu cầu bổ sung của user (feedback) để tái kích hoạt các agent tương ứng. | LLM |

---

## 4. Luồng công việc (Workflow Detail)

### Giai đoạn 1: Thu thập thông tin linh hoạt (Flexible Collection)
Thay vì hỏi từng câu một cách cứng nhắc, hệ thống sử dụng **InfoExtractorAgent**.
- **User:** Nhắn tin tự do (VD: "Đi Đà Lạt từ HN 2 người").
- **Agent:** Bóc tách thông tin hiện có, đối chiếu với danh sách bắt buộc.
- **Loop:** Nếu thiếu, Bot chỉ hỏi đúng thông tin còn thiếu. Nếu đủ, chuyển sang bước **Confirm**.

### Giai đoạn 2: Điều phối LangGraph (Agentic Execution)
Khi user bấm "Chính xác", LangGraph State được khởi tạo và chạy qua các Node:
1. `transport` -> 2. `food` -> 3. `places` -> 4. `weather` -> 5. `reporting`.
Dữ liệu được tích lũy vào `TravelState` thông qua cơ chế `operator.ior` (merge dictionary), giúp bảo toàn kết quả từ các bước trước.

### Giai đoạn 3: Vòng lặp phản hồi (Interactive Feedback Loop)
Sau khi gửi kết quả và PDF, hệ thống không kết thúc mà chuyển sang trạng thái `FEEDBACK`:
- User yêu cầu: "Tìm thêm quán cafe".
- **IntentAgent** phân tích ý định -> Trả về `places`.
- Hệ thống kích hoạt lại Node `places` trong Graph với query mới.
- Kết quả mới được cộng dồn vào kết quả cũ và tạo báo cáo cập nhật.

---

## 5. Các giải pháp kỹ thuật đặc biệt đã áp dụng

### A. Local 9Router Proxy Integration
Hệ thống được cấu hình để chạy qua proxy cục bộ (`http://localhost:20128/v1`) nhằm tối ưu tốc độ và độ ổn định khi gọi mô hình Gemini từ Việt Nam, sử dụng thư viện `litellm` bên dưới `crewai`.

### B. Xử lý giới hạn tin nhắn Telegram (Large Message Chunking)
Để vượt qua giới hạn 4096 ký tự của Telegram, chúng ta đã xây dựng hàm `send_large_message`. Hàm này tự động chia nhỏ báo cáo tại các vị trí ngắt dòng tự nhiên, đảm bảo trải nghiệm đọc mượt mà.

### C. Unicode PDF Export
Sử dụng font `DejaVuSans.ttf` để đảm bảo file PDF xuất ra không bị lỗi hiển thị tiếng Việt, giải quyết vấn đề phổ biến của các thư viện PDF cũ.

### D. Khả năng Reset (Self-Healing)
Cung cấp lệnh `/reset` và logic tự động xóa `user_data` khi bắt đầu phiên mới, đảm bảo các biến trạng thái của Agent không bị "nhiễm" dữ liệu cũ từ chuyến đi trước.

---

## 6. Tổng kết phương án cuối cùng
Hệ thống hiện tại là sự kết hợp giữa **Chat linh hoạt (NLP)** và **Quy trình nghiên cứu có cấu trúc (Agentic Workflow)**. Nó cho phép người dùng giao tiếp tự nhiên nhưng vẫn nhận được kết quả nghiên cứu sâu, đa nguồn và có thể tùy chỉnh liên tục cho đến khi hài lòng.
