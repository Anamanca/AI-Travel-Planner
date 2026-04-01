from typing import Annotated, TypedDict, List, Dict, Optional
import operator

class AgentResult(TypedDict):
    """Cấu trúc kết quả từ mỗi Specialist Agent."""
    category: str  # 'Low', 'Mid', 'High'
    title: str
    description: str
    price: float
    link: Optional[str]
    source: str  # 'TikTok', 'Facebook', 'Web', 'API'

class TravelState(TypedDict):
    """Trạng thái tổng thể của luồng LangGraph."""
    # ID người dùng để gửi thông báo trực tiếp
    chat_id: str
    
    # Thông tin đầu vào từ người dùng
    user_info: Dict[str, str]
    
    # Tin nhắn phản hồi mới nhất của user (Dùng cho Interactive Mode)
    user_feedback: str
    
    # Ý định của user (được RouterNode phân tích: 'food', 'transport', 'weather', 'finish', 'other')
    intent: List[str]
    
    # Kết quả tích lũy từ các Agent (Dùng Annotated với operator.ior để merge dict)
    # Key sẽ là tên agent (ví dụ: 'bus', 'flight', 'food')
    # Value là danh sách các AgentResult
    results: Annotated[Dict[str, List[AgentResult]], operator.ior]
    
    # Phản hồi từ Evaluator cho từng bước
    evaluator_feedback: Annotated[List[Dict[str, str]], operator.add]
    
    # Đếm số lần retry của từng Agent
    retry_counts: Annotated[Dict[str, int], operator.ior]
    
    # Báo cáo cuối cùng dạng Markdown
    final_report: str
    
    # Danh sách các Agent đang/vừa xử lý (Sử dụng Annotated với operator.add để cộng dồn list)
    current_agent: Annotated[List[str], operator.add]
    
    # Lịch sử logs chi tiết (dùng cho debug và tài liệu)
    execution_logs: Annotated[List[Dict], operator.add]
