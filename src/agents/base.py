import os
from typing import List, Dict, Any, Union
from crewai import LLM
from src.graph.state import TravelState

class BaseAgent:
    """Lớp cơ sở cho tất cả các Agents chuyên biệt sử dụng 9Router (via crewAI)."""
    def __init__(self, name: str, model: str = "openai/gc/gemini-3-flash-preview"):
        self.name = name
        # Sử dụng 9Router (tương thích OpenAI API) qua crewAI LLM
        api_key = os.getenv("NINE_ROUTER_API_KEY")
        base_url = os.getenv("NINE_ROUTER_API_BASE", "http://localhost:20128/v1")
        
        self.llm = LLM(
            model=model, 
            temperature=0.7,
            api_key=api_key,
            base_url=base_url
        )

    def format_prompt(self, state: TravelState) -> str:
        """Tạo prompt chuẩn cho agent dựa trên state."""
        raise NotImplementedError("Cần được override bởi lớp con")

    def run(self, state: TravelState) -> Dict[str, Any]:
        """Thực thi logic của agent."""
        prompt = self.format_prompt(state)
        # Sử dụng crewAI LLM call (chấp nhận string hoặc list messages)
        response = self.llm.call(prompt)
        return {"results": {self.name: response}}

class EvaluatorAgent:
    """Agent chuyên đánh giá kết quả từ các Agent khác sử dụng 9Router (via crewAI)."""
    def __init__(self, model: str = "openai/gc/gemini-3-flash-preview"):
        api_key = os.getenv("NINE_ROUTER_API_KEY")
        base_url = os.getenv("NINE_ROUTER_API_BASE", "http://localhost:20128/v1")
        
        self.llm = LLM(
            model=model, 
            temperature=0,
            api_key=api_key,
            base_url=base_url
        )

    def evaluate(self, state: TravelState, agent_name: str) -> Dict[str, Any]:
        """
        Kiểm tra kết quả của một agent cụ thể.
        Trả về: {'is_valid': bool, 'feedback': str}
        """
        agent_output = state['results'].get(agent_name, [])
        user_info = state['user_info']
        
        prompt = f"""
        Bạn là Travel Planning Evaluator. Nhiệm vụ của bạn là kiểm tra kết quả của Agent: {agent_name}.
        
        Yêu cầu người dùng: {user_info}
        Kết quả Agent: {agent_output}
        
        Hãy kiểm tra:
        1. Kết quả có khớp với thời gian/địa điểm không?
        2. Có đủ 3 phân loại (Low, Mid, High) không?
        3. Thông tin có đầy đủ (giá, mô tả, nguồn) không?
        
        Trả về kết quả theo định dạng JSON:
        {{
            "is_valid": true/false,
            "feedback": "Lý do tại sao không đạt hoặc lời khen nếu tốt",
            "retry_count_increment": 0/1
        }}
        """
        
        response = self.llm.call(prompt)
        # Parse JSON output
        import json
        try:
            # Tìm phần JSON trong output
            res_content = response.strip()
            if "```json" in res_content:
                res_content = res_content.split("```json")[1].split("```")[0]
            result = json.loads(res_content)
        except Exception as e:
            result = {"is_valid": False, "feedback": f"Lỗi parse Evaluator: {str(e)}", "retry_count_increment": 1}
            
        return result

class InfoExtractorAgent(BaseAgent):
    """Agent chuyên bóc tách thông tin chuyến đi từ tin nhắn tự do của user."""
    def __init__(self, model: str = "openai/gc/gemini-3-flash-preview"):
        super().__init__(name="info_extractor", model=model)

    def extract(self, user_text: str, current_info: Dict[str, str]) -> Dict[str, str]:
        """Bóc tách thông tin và cập nhật vào dict hiện tại."""
        prompt = f"""
        Dựa trên tin nhắn của người dùng và thông tin đã thu thập được, hãy trích xuất các thông tin du lịch.
        
        Thông tin đã có: {current_info}
        Tin nhắn mới: "{user_text}"

        Hãy trích xuất các trường sau (nếu có):
        - 'from': Điểm xuất phát
        - 'destination': Điểm đến
        - 'date_start': Ngày đi (định dạng DD/MM/YYYY)
        - 'date_end': Ngày về (định dạng DD/MM/YYYY)
        - 'people': Số lượng người
        - 'purpose': Mục đích (nghỉ dưỡng, khám phá, công tác...)
        - 'transport': Phương tiện (máy bay, xe khách...)

        Trả về DUY NHẤT một đối tượng JSON chứa tất cả các trường trên. 
        Nếu trường nào chưa có thông tin, hãy để giá trị là chuỗi rỗng "".
        Giữ nguyên các thông tin cũ nếu tin nhắn mới không thay đổi chúng.
        
        Ví dụ kết quả:
        {{"from": "Hà Nội", "destination": "Đà Lạt", "date_start": "01/05/2026", "date_end": "05/05/2026", "people": "2 người", "purpose": "nghỉ dưỡng", "transport": "máy bay"}}
        """
        response = self.llm.call(prompt)
        import json
        try:
            res_content = response.strip()
            if "```json" in res_content:
                res_content = res_content.split("```json")[1].split("```")[0]
            return json.loads(res_content)
        except:
            return current_info

class IntentAgent(BaseAgent):
    """Agent chuyên phân tích ý định của user để điều hướng LangGraph."""
    def __init__(self, model: str = "openai/gc/gemini-3-flash-preview"):
        super().__init__(name="intent_router", model=model)

    def analyze(self, user_feedback: str) -> str:
        """Phân tích feedback và trả về key của Agent tương ứng."""
        if not user_feedback:
            return "finish"

        prompt = f"""
        Phân tích tin nhắn của người dùng sau đây và xác định họ muốn làm gì tiếp theo:
        Tin nhắn: "{user_feedback}"

        Hãy chọn MỘT trong các nhãn sau:
        - 'transport': Nếu user muốn đổi phương tiện, hỏi vé máy bay/xe khách, giá vé...
        - 'food': Nếu user muốn tìm thêm quán ăn, món ngon, địa điểm ăn uống...
        - 'places': Nếu user muốn tìm thêm địa điểm tham quan, vui chơi, cafe...
        - 'weather': Nếu user muốn hỏi thêm về thời tiết.
        - 'finish': Nếu user nói 'xong rồi', 'cảm ơn', 'hết rồi' hoặc không muốn làm gì thêm.
        - 'other': Nếu là câu hỏi chung chung hoặc không rõ ràng nhưng vẫn muốn research thêm.

        CHỈ TRẢ VỀ DUY NHẤT TỪ KHÓA NHÃN (Ví dụ: food).
        """
        response = self.llm.call(prompt).strip().lower()
        
        # Cleanup response
        valid_intents = ['transport', 'food', 'places', 'weather', 'finish', 'other']
        for intent in valid_intents:
            if intent in response:
                return intent
        return "other"
