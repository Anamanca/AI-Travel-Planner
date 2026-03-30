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
        # Logic tạo prompt chuyên biệt cho vận chuyển
        return ""

    def run(self, state: TravelState) -> Dict[str, Any]:
        user_info = state['user_info']
        query = f"Giá vé {self.mode} từ {user_info.get('from')} đến {user_info.get('destination')} ngày {user_info.get('date_start')}"
        
        # Gọi tool tìm kiếm
        search_data = self.tools.search_web(query)
        
        prompt = f"""
        Dựa trên dữ liệu tìm kiếm: {search_data}
        Hãy đưa ra 3 lựa chọn vé {self.mode} tốt nhất cho chuyến đi từ {user_info.get('from')} đến {user_info.get('destination')}.
        Phân loại thành: 'Low' (Tiết kiệm), 'Mid' (Trung cấp), 'High' (Cao cấp/Thương gia).
        
        Trả về danh sách các đối tượng JSON theo định dạng:
        [
            {{"category": "Low", "title": "...", "description": "...", "price": 0, "link": "...", "source": "Web"}},
            ...
        ]
        """
        response = self.llm.call(prompt)
        # Parse kết quả và trả về đúng định dạng TravelState
        try:
            # Tìm phần JSON trong response
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
        # Tìm trên TikTok & Facebook
        tiktok_data = self.tools.search_tiktok(f"{self.type} ngon nổi tiếng tại {dest}")
        fb_data = self.tools.search_facebook(f"Review {self.type} {dest}")
        
        prompt = f"""
        Tổng hợp dữ liệu từ TikTok: {tiktok_data} và Facebook: {fb_data}.
        Hãy liệt kê các {self.type} tại {dest}, xếp hạng từ cao đến thấp.
        Phân loại thành: 'Low' (Bình dân), 'Mid' (Tầm trung), 'High' (Sang trọng).
        
        Trả về JSON list:
        [
            {{"category": "Mid", "title": "Tên địa điểm", "description": "Lý do nổi tiếng", "price": 0, "link": "link_social", "source": "TikTok/FB"}},
            ...
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
        
        prompt = f"Tóm tắt tình hình thời tiết tại {dest} dựa trên: {weather_data}. Trả về 1 đoạn văn ngắn kèm lời khuyên trang phục."
        response = self.llm.call(prompt)
        return {"results": {"weather": [{"category": "Info", "title": "Thời tiết", "description": response, "price": 0, "source": "Web"}]}}
