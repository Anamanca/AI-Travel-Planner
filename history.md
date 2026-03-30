# Project History - AI Travel Planner

## [1.1.0] - 2026-03-30

### Added
- **Parallel Execution (Fan-out/Fan-in):** Các Agent nghiên cứu (Transport, Food, Places, Weather) hiện chạy song song thay vì tuần tự, giúp tăng tốc độ phản hồi đáng kể.
- **Self-Correction (Evaluator):** Thêm Node đánh giá chất lượng kết quả. Nếu Agent trả về dữ liệu thiếu hoặc sai định dạng, hệ thống sẽ yêu cầu thực hiện lại.
- **Real-time Notifications:** Bot gửi tin nhắn thông báo khi AI đang thực hiện kiểm tra lại thông tin (Retry) để người dùng không cảm thấy Bot bị treo.
- **Web Search for Discovery:** Bổ sung công cụ tìm kiếm web cho DiscoveryAgent để tổng hợp dữ liệu từ blog và trang tin bên cạnh TikTok/Facebook.
- **Async Workflow:** Chuyển đổi toàn bộ Graph Nodes sang `async def` và xử lý thread-safe cho các Agent đồng bộ.

### Fixed
- **Concurrent State Conflicts:** Sửa lỗi nhiều Agent cùng cập nhật `current_agent` gây crash bằng cách sử dụng `Annotated` và `operator.add`.
- **Infinite Retry Loop:** Giới hạn số lần thử lại tối đa là 2 lần để đảm bảo tính ổn định và tiết kiệm chi phí API.
- **Type Mismatch:** Sửa lỗi khởi tạo `current_agent` từ chuỗi sang danh sách để tương thích với cơ chế gộp dữ liệu song song.

### Changed
- **Improved Prompts:** Cập nhật Prompt cho tất cả Specialist Agents để đảm bảo trả về JSON chuẩn với 3 phân khúc (Low, Mid, High) và giá tiền thực tế.
- **Architecture Migration:** Chuyển từ mô hình "Chuỗi hạt" sang mô hình "Trung tâm kiểm soát".

---

## [1.0.0] - 2026-03-25
- Bản phát hành đầu tiên với các tính năng cơ bản: Thu thập thông tin, nghiên cứu tuần tự, xuất PDF và tương tác phản hồi.
