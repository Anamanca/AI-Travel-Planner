from typing import List, Dict, Any
from src.agents.base import BaseAgent
from src.graph.state import TravelState, AgentResult
from src.tools.research_tools import ResearchTools
import json

class TransportAgent(BaseAgent):
    """Agent chuyên tìm kiếm vé xe khách và máy bay."""
    def __init__(self, mode: str, model: str = "openai/gc/gemini-3-flash-preview"):
        super().__init__(name=f"transport_{mode}", model=model)
        self.mode = mode # 'bus' hoặc 'flight'
        self.tools = ResearchTools()

    def format_prompt(self, state: TravelState) -> str:
        return ""

    def run(self, state: TravelState) -> Dict[str, Any]:
        user_info = state['user_info']
        dest = user_info.get('destination')
        origin = user_info.get('from')
        date = user_info.get('date_start')
        
        query = f"Giá vé {self.mode} từ {origin} đến {dest} ngày {date}"
        search_data = self.tools.search_web(query)
        
        prompt = f"""
        Bạn là chuyên gia tìm kiếm vé {self.mode}. 
        Nhiệm vụ: Tìm vé từ {origin} đến {dest} cho ngày {date}.
        
        Dữ liệu thô từ web: {search_data}
        
        YÊU CẦU BẮT BUỘC:
        1. Phải trả về đúng lựa chọn cho 3 phân loại: 'Low' (Giá rẻ/Tiết kiệm), 'Mid' (Phổ thông/Trung cấp), 'High' (Thương gia/VIP). Mỗi phân loại có thể có nhiều lựa chọn
        2. Mỗi lựa chọn phải có GIÁ CỤ THỂ (ước tính bằng số VNĐ), không được để bằng 0.
        3. 'description' phải bao gồm: Tên hãng, giờ khởi hành (nếu có), và ưu điểm.
        4. 'source' phải là tên trang web bạn tìm thấy thông tin.
        
        TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON LIST:
        [
            {{"category": "Low", "title": "Tên hãng/Chuyến đi", "description": "...", "price": 500000, "link": "url", "source": "tên nguồn"}},
            {{"category": "Mid", "title": "...", "description": "...", "price": 1000000, "link": "url", "source": "tên nguồn"}},
            {{"category": "High", "title": "...", "description": "...", "price": 2000000, "link": "url", "source": "tên nguồn"}}
        ]
        """
        response = self.llm.call(prompt)
        try:
            res_content = response.strip()
            if "```json" in res_content:
                res_content = res_content.split("```json")[1].split("```")[0]
            results = json.loads(res_content)
            return {"results": {self.name: results}}
        except:
            return {"results": {self.name: []}}

class DiscoveryAgent(BaseAgent):
    """Agent chuyên tìm kiếm Đồ ăn (Food) và Địa điểm vui chơi (Places)."""
    def __init__(self, type: str, model: str = "openai/gc/gemini-3-flash-preview"):
        super().__init__(name=f"discovery_{type}", model=model)
        self.type = type # 'food' hoặc 'places'
        self.tools = ResearchTools()

    def format_prompt(self, state: TravelState) -> str:
        return ""

    def run(self, state: TravelState) -> Dict[str, Any]:
        dest = state['user_info'].get('destination')
        # Tìm trên 3 nguồn khác nhau
        tiktok_data = self.tools.search_tiktok(f"{self.type} ngon nổi tiếng tại {dest}")
        fb_data = self.tools.search_facebook(f"Review {self.type} {dest}")
        web_data = self.tools.search_web(f"Top các địa điểm {self.type} phải thử tại {dest}")
        
        type_label = "Quán ăn/Món ngon" if self.type == "food" else "Địa điểm tham quan/Cafe"
        
        prompt = f"""
        Bạn là chuyên gia review du lịch. Nhiệm vụ: Tìm {type_label} tại {dest}.
        
        Dữ liệu tổng hợp:
        - TikTok: {tiktok_data}
        - Facebook: {fb_data}
        - Web (Google/Blogs): {web_data}
        
        YÊU CẦU BẮT BUỘC:
        1. Phải trả về đúng lựa chọn cho 3 phân loại: 'Low' (Bình dân/Vỉa hè), 'Mid' (Tầm trung/Nhà hàng), 'High' (Sang trọng/Cao cấp). Mỗi phân loại có thể có nhiều lựa chọn
        2. Với mỗi địa điểm, hãy ước tính 'price' (chi phí trung bình mỗi người bằng VNĐ). Không để bằng 0.
        3. 'description' phải tóm tắt lý do tại sao nơi này nổi tiếng.
        4. 'source' phải ghi rõ nguồn gốc thông tin (TikTok, Facebook, link web cụ thể).
        
        TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON LIST:
        [
            {{"category": "Low", "title": "Tên nơi", "description": "...", "price": 50000, "link": "...", "source": "..."}},
            {{"category": "Mid", "title": "...", "description": "...", "price": 300000, "link": "...", "source": "..."}},
            {{"category": "High", "title": "...", "description": "...", "price": 1500000, "link": "...", "source": "..."}}
        ]
        """
        response = self.llm.call(prompt)
        try:
            res_content = response.strip()
            if "```json" in res_content:
                res_content = res_content.split("```json")[1].split("```")[0]
            results = json.loads(res_content)
            return {"results": {self.name: results}}
        except:
            return {"results": {self.name: []}}

class WeatherAgent(BaseAgent):
    """Agent kiểm tra thời tiết."""
    def __init__(self, model: str = "openai/gc/gemini-3-flash-preview"):
        super().__init__(name="weather", model=model)
        self.tools = ResearchTools()

    def format_prompt(self, state: TravelState) -> str:
        return ""

    def run(self, state: TravelState) -> Dict[str, Any]:
        dest = state['user_info'].get('destination')
        date = state['user_info'].get('date_start')
        weather_data = self.tools.search_web(f"Thời tiết tại {dest} ngày {date}")
        
        prompt = f"Tóm tắt tình hình thời tiết tại {dest} dựa trên: {weather_data}. Trả về 1 đoạn văn ngắn kèm lời khuyên trang phục, thuốc, vật dụng cần thiết."
        response = self.llm.call(prompt)
        return {"results": {"weather": [{"category": "Info", "title": "Thời tiết", "description": response, "price": 0, "source": "Web"}]}}
