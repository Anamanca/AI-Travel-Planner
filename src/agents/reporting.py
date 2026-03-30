from typing import Dict, List, Any
from src.agents.base import BaseAgent
from src.graph.state import TravelState
from fpdf import FPDF
import os

class ReportingAgent(BaseAgent):
    """Agent tổng hợp báo cáo và tính toán ngân sách."""
    def __init__(self, model: str = "openai/gc/gemini-3-flash-preview"):
        super().__init__(name="reporting", model=model)

    def format_prompt(self, state: TravelState) -> str:
        results = state['results']
        user_info = state['user_info']
        
        prompt = f"""
        Dựa trên kết quả từ các Agent: {results}.
        Yêu cầu người dùng: {user_info}.
        
        Hãy thực hiện:
        1. Tổng hợp lịch trình chi tiết theo từng ngày (từ {user_info.get('date_start')} đến {user_info.get('date_end')}).
        2. Tạo ra 3 Phương án Ngân sách (Budget Options) riêng biệt, trình bày THỨ TỰ NHƯ SAU:
           
           ### 1. Phương án TIẾT KIỆM (Low Budget)
           - Chọn toàn bộ các lựa chọn thuộc category 'Low'.
           - Tổng kết chi phí dự kiến cho phương án này.
           
           ### 2. Phương án VỪA PHẢI (Standard Budget)
           - Chọn toàn bộ các lựa chọn thuộc category 'Mid'.
           - Tổng kết chi phí dự kiến cho phương án này.
           
           ### 3. Phương án THOẢI MÁI (Premium Budget)
           - Chọn toàn bộ các lựa chọn thuộc category 'High'.
           - Tổng kết chi phí dự kiến cho phương án này.
        
        Yêu cầu trình bày:
        - Sử dụng Markdown chuyên nghiệp với các tiêu đề rõ ràng.
        - Không trộn lẫn các phương án với nhau.
        - Mỗi phương án cần có danh sách chi tiết (Vận chuyển, Ăn uống, Tham quan).
        """
        return prompt

    def run(self, state: TravelState) -> Dict[str, Any]:
        prompt = self.format_prompt(state)
        response = self.llm.call(prompt)
        return {"final_report": response}

class PDFExporter:
    """Công cụ xuất báo cáo ra PDF hỗ trợ Unicode (Tiếng Việt)."""
    @staticmethod
    def export(report_content: str, output_path: str):
        pdf = FPDF()
        pdf.add_page()
        
        # Thêm font Unicode hỗ trợ tiếng Việt
        font_path = "fonts/DejaVuSans.ttf"
        
        try:
            if os.path.exists(font_path):
                pdf.add_font("DejaVu", "", font_path)
                pdf.set_font("DejaVu", size=11)
            else:
                pdf.set_font("Helvetica", size=10)
                report_content = "LỖI: Chưa cài đặt font Unicode (fonts/DejaVuSans.ttf). Nội dung tiếng Việt sẽ bị lỗi hiển thị.\n\n" + report_content
        except Exception as e:
            print(f"Lỗi load font PDF: {e}")
            pdf.set_font("Helvetica", size=10)

        pdf.set_margins(15, 15, 15)
        
        # Title
        pdf.set_font_size(16)
        pdf.cell(0, 10, "KẾ HOẠCH DU LỊCH CỦA BẠN", ln=True, align='C')
        pdf.ln(10)
        
        # Body
        pdf.set_font_size(11)
        pdf.multi_cell(0, 8, txt=report_content)
            
        pdf.output(output_path)
        return output_path

def save_execution_log(state: TravelState, log_dir: str = "logs"):
    """Lưu logs thực thi của toàn bộ quá trình."""
    import json
    from datetime import datetime
    
    trip_id = f"trip_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"{trip_id}.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)
    return log_file
