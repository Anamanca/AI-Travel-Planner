# AI Travel Planner - System Architecture & Multi-Agent Design

Tài liệu này tổng hợp cấu trúc và nguyên lý hoạt động của hệ thống AI Travel Planner (Version 1.1.1).

---

## 1. Triết lý Thiết kế (Design Philosophy)
Hệ thống được thiết kế theo mô hình **"Parallel Research -> Automated Evaluation -> Interactive Feedback"**. 
Thay vì chạy tuần tự, chúng tôi sử dụng cơ chế **Fan-out/Fan-in** để nghiên cứu đa nguồn cùng lúc và kiểm soát chất lượng bằng một Agent đánh giá độc lập trước khi gửi cho người dùng.

## 2. Công nghệ lõi (Core Tech Stack)
- **Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) - Quản lý trạng thái (State) và luồng công việc bất đồng bộ (Async Workflow).
- **LLM Engine:** Gemini 3 Flash thông qua **9Router** proxy sử dụng class `crewai.LLM`.
- **Search & Scraping:** 
    - **Tavily:** Tìm kiếm web chuyên sâu.
    - **Apify:** TikTok & Facebook scraper.
- **Interface:** `python-telegram-bot` (Resilient Message Delivery).
- **Reporting:** `fpdf2` (Unicode hỗ trợ Tiếng Việt).

---

## 3. Quy trình Multi-Agent Nâng cao (The Parallel Workflow)

Hệ thống sử dụng kiến trúc **Fan-out/Fan-in** kết hợp với **Self-Correction**:

### Giai đoạn 1: Bóc tách & Điều hướng (Extraction & Routing)
- **InfoExtractorAgent:** Sử dụng cơ chế Prompt Engineering để trích xuất dữ liệu từ ngôn ngữ tự nhiên thành JSON Schema chuẩn hóa (destination, date, people_among, etc.).
- **IntentAgent:** Phân tích ý định người dùng và trả về danh sách các tác vụ cần thực hiện (ví dụ: vừa tìm đồ ăn, vừa xem thời tiết).

### Giai đoạn 2: Nghiên cứu Song song (Fan-out)
Khi thông tin chuyến đi đã đủ, Bot kích hoạt đồng thời 4 Node nghiên cứu:
- **TransportAgent:** Tìm vé xe/máy bay theo phương tiện yêu cầu.
- **DiscoveryAgent (Food):** Tìm quán ăn từ TikTok, Facebook và Web.
- **DiscoveryAgent (Places):** Tìm địa điểm chơi từ TikTok, Facebook và Web.
- **WeatherAgent:** Dự báo thời tiết.
*Lợi ích:* Giảm thời gian chờ xuống ~70%.

### Giai đoạn 3: Kiểm soát Chất lượng (Evaluator Node)
Tất cả kết quả từ giai đoạn 2 hội tụ về **EvaluatorAgent**. 
- **Nhiệm vụ:** Kiểm tra xem dữ liệu có đủ 3 phân khúc (Low/Mid/High), có giá tiền thực tế và đúng địa điểm/thời gian không.
- **Cơ chế Retry (Self-Healing):** Nếu một Agent thất bại, Evaluator sẽ yêu cầu Agent đó làm lại. Giới hạn tối đa **2 lần thử**.
- **Thông báo thời gian thực:** Bot sẽ nhắn tin báo trạng thái xử lý qua Telegram để người dùng an tâm.

### Giai đoạn 4: Tổng hợp & Phản hồi (Reporting & Interactive)
- **ReportingAgent:** Tổng hợp kết quả Markdown & PDF.
- **Interactive Mode:** Sau báo cáo, Bot vào trạng thái chờ phản hồi. Nếu user hài lòng và "Kết thúc", hệ thống tự động xóa state cũ và gửi lại lời chào để sẵn sàng cho một kế hoạch mới.

---

## 4. Giải pháp kỹ thuật đặc biệt

- **Resilient Delivery:** Cơ chế fallback tự động cho Telegram. Nếu Markdown bị lỗi parser, hệ thống tự gửi lại dạng Plain Text để đảm bảo thông tin không bị mất.
- **Async State Updates:** Sử dụng `Annotated` với `operator.ior` và `operator.add` trong `TravelState` để cho phép cập nhật trạng thái song song an toàn.
- **Thread Pool Execution:** Sử dụng `asyncio.to_thread` để chạy các Agent đồng bộ bên trong luồng bất đồng bộ của LangGraph.
- **JSON Integrity:** Ép AI trả về JSON nghiêm ngặt với các trường bắt buộc để phục vụ việc đánh giá tự động.

---

## 5. Tổng kết
Hệ thống hiện tại không chỉ là một Bot chat đơn thuần mà là một **Dây chuyền sản xuất kế hoạch du lịch tự động**. Nó kết hợp tốc độ của tính toán song song với sự khắt khe của quy trình kiểm soát chất lượng và sự bền bỉ của hệ thống truyền tin, mang lại trải nghiệm chuyên nghiệp cho người dùng cuối.
