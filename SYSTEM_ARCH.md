# AI Travel Planner - System Architecture & Multi-Agent Design

Tài liệu này tổng hợp cấu trúc và nguyên lý hoạt động của hệ thống AI Travel Planner (Version 1.1.0).

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
- **Interface:** `python-telegram-bot` (ConversationHandler).
- **Reporting:** `fpdf2` (Unicode hỗ trợ Tiếng Việt).

---

## 3. Quy trình Multi-Agent Nâng cao (The Parallel Workflow)

Hệ thống sử dụng kiến trúc **Fan-out/Fan-in** kết hợp với **Self-Correction**:

### Giai đoạn 1: Nghiên cứu Song song (Fan-out)
Khi thông tin chuyến đi đã đủ, Bot kích hoạt đồng thời 4 Node nghiên cứu:
- **TransportAgent:** Tìm vé xe/máy bay.
- **DiscoveryAgent (Food):** Tìm quán ăn từ TikTok, Facebook và Web.
- **DiscoveryAgent (Places):** Tìm địa điểm chơi từ TikTok, Facebook và Web.
- **WeatherAgent:** Dự báo thời tiết.
*Lợi ích:* Giảm thời gian chờ xuống ~70%.

### Giai đoạn 2: Kiểm soát Chất lượng (Evaluator Node)
Tất cả kết quả từ giai đoạn 1 hội tụ về **EvaluatorAgent**. 
- **Nhiệm vụ:** Kiểm tra xem dữ liệu có đủ 3 phân khúc (Low/Mid/High), có giá tiền thực tế và đúng địa điểm/thời gian không.
- **Cơ chế Retry (Self-Healing):** Nếu một Agent thất bại, Evaluator sẽ yêu cầu Agent đó làm lại. Giới hạn tối đa **2 lần thử** để tránh lặp vô hạn và tiết kiệm chi phí.
- **Thông báo thời gian thực:** Bot sẽ nhắn tin báo "Đang kiểm tra lại thông tin về..." để người dùng an tâm.

### Giai đoạn 3: Tổng hợp & Phản hồi (Reporting & Interactive)
- **ReportingAgent:** Tổng hợp kết quả Markdown & PDF.
- **Interactive Mode:** Sau báo cáo, Bot vào trạng thái chờ phản hồi. Nếu khách hỏi thêm, **IntentAgent** sẽ điều hướng chỉ đến Node cần thiết (ví dụ: chỉ tìm thêm cafe).

---

## 4. Giải pháp kỹ thuật đặc biệt

- **Async State Updates:** Sử dụng `Annotated[List[str], operator.add]` và `operator.ior` trong `TravelState` để cho phép nhiều Agent cập nhật trạng thái cùng lúc mà không gây xung đột dữ liệu.
- **Thread Pool Execution:** Sử dụng `asyncio.to_thread` để chạy các Agent đồng bộ bên trong luồng bất đồng bộ của LangGraph, đảm bảo Bot luôn mượt mà.
- **Prompt Engineering:** Ép AI trả về JSON nghiêm ngặt với các trường bắt buộc (price, source, description) để phục vụ việc đánh giá tự động.

---

## 5. Tổng kết
Hệ thống hiện tại không chỉ là một Bot chat đơn thuần mà là một **Dây chuyền sản xuất kế hoạch du lịch tự động**. Nó kết hợp tốc độ của tính toán song song với sự khắt khe của quy trình kiểm soát chất lượng, mang lại trải nghiệm chuyên nghiệp cho người dùng cuối.
