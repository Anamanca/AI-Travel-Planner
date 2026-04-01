import os
import sys
import logging
import asyncio

# Thêm thư mục gốc của project vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv
from src.graph.workflow import create_travel_graph
from src.agents.reporting import PDFExporter, save_execution_log

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CÁC HÀM TRỢ GIÚP ---

async def send_large_message(update: Update, text: str):
    """Chia nhỏ tin nhắn lớn để gửi tránh lỗi giới hạn 4096 ký tự của Telegram. Có fallback nếu lỗi Markdown."""
    parts = []
    if len(text) <= 4000:
        parts = [text]
    else:
        temp_text = text
        while len(temp_text) > 0:
            if len(temp_text) <= 4000:
                parts.append(temp_text)
                break
            chunk = temp_text[:4000]
            last_newline = chunk.rfind('\n')
            if last_newline != -1 and last_newline > 3000:
                parts.append(temp_text[:last_newline])
                temp_text = temp_text[last_newline:].lstrip()
            else:
                parts.append(temp_text[:4000])
                temp_text = temp_text[4000:]

    for part in parts:
        try:
            await update.effective_message.reply_text(part, parse_mode='Markdown')
        except Exception as e:
            logger.warning(f"Markdown parsing failed, sending as plain text: {e}")
            await update.effective_message.reply_text(part)

# --- CÁC BỘ XỬ LÝ CHÍNH ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Khởi tạo phiên làm việc mới và gửi lời chào."""
    chat_id = str(update.effective_chat.id)
    
    # Khởi tạo TravelState trống
    state = {
        "chat_id": chat_id,
        "user_info": {},
        "results": {},
        "evaluator_feedback": [],
        "retry_counts": {},
        "final_report": "",
        "current_agent": [], 
        "execution_logs": [],
        "user_feedback": "",
        "intent": []
    }
    context.user_data['graph_state'] = state
    
    welcome_msg = (
        "Chào mừng bạn đến với **AI Travel Planner**! 🌍✈️\n\n"
        "Tôi đã sẵn sàng lên kế hoạch du lịch cho bạn. Hãy cho tôi biết:\n"
        "📍 Bạn muốn đi đâu, từ đâu?\n"
        "📅 Đi vào thời gian nào?\n"
        "👥 Có bao nhiêu người tham gia?\n\n"
        "💡 **Ví dụ:** *'Tôi muốn đi Đà Lạt từ Hà Nội từ 01/05 đến 05/05, 2 người'*."
    )
    await update.effective_message.reply_text(welcome_msg, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý mọi tin nhắn văn bản từ user thông qua LangGraph."""
    user_text = update.message.text
    chat_id = str(update.effective_chat.id)
    
    # 1. Khởi tạo state nếu chưa tồn tại (Dành cho trường hợp user nhắn tin trước khi gõ /start)
    if 'graph_state' not in context.user_data:
        context.user_data['graph_state'] = {
            "chat_id": chat_id,
            "user_info": {},
            "results": {},
            "evaluator_feedback": [],
            "retry_counts": {},
            "final_report": "",
            "current_agent": [], 
            "execution_logs": [],
            "user_feedback": "",
            "intent": []
        }
    
    state = context.user_data['graph_state']
    # Cập nhật tin nhắn mới nhất của user vào state để LangGraph bóc tách
    state['user_feedback'] = user_text
    
    await update.message.reply_text("🔄 AI đang xử lý yêu cầu của bạn... 🚀")
    
    try:
        graph = create_travel_graph()
        # Chạy toàn bộ logic trong Graph: Extract -> Intent -> Research (nếu đủ) -> Report
        final_state = await graph.ainvoke(state)
        
        # Lưu lại state sau khi Graph đã cập nhật (user_info, results, final_report...)
        context.user_data['graph_state'] = final_state
        
        # 2. Kiểm tra nếu user muốn kết thúc (IntentAgent nhận diện được từ user_feedback)
        intents = final_state.get('intent', [])
        if "finish" in (intents if isinstance(intents, list) else [intents]):
            await update.effective_message.reply_text("Chúc bạn có một chuyến đi tuyệt vời! 🌟 Hẹn gặp lại.")
            
            # Xóa state cũ để sẵn sàng cho plan mới
            context.user_data.clear()
            
            # Gửi lại lời chào để bắt đầu plan mới
            welcome_msg = (
                "Tôi đã sẵn sàng lên kế hoạch mới cho bạn. Hãy cho tôi biết:\n"
                "📍 Bạn muốn đi đâu, từ đâu?\n"
                "📅 Đi vào thời gian nào?\n"
                "👥 Có bao nhiêu người tham gia?\n\n"
                "💡 **Ví dụ:** *'Tôi muốn đi Đà Lạt từ Hà Nội từ 01/05 đến 05/05, 2 người'*."
            )
            await update.effective_message.reply_text(welcome_msg, parse_mode='Markdown')
            return

        # 3. Gửi báo cáo (có thể là báo cáo du lịch hoặc thông báo yêu cầu thêm thông tin)
        report = final_state.get('final_report', 'Xin lỗi, tôi gặp chút trục trặc khi xử lý thông tin.')
        await send_large_message(update, report)
        
        # 4. Nếu đã có kết quả nghiên cứu (nghĩa là không phải đang hỏi thiếu thông tin), xuất PDF
        if final_state.get('results'):
            # Chỉ tạo PDF khi thực sự có dữ liệu du lịch
            pdf_path = f"output/plan_{chat_id}.pdf"
            os.makedirs("output", exist_ok=True)
            from src.agents.reporting import PDFExporter
            PDFExporter.export(report, pdf_path)
            
            with open(pdf_path, 'rb') as f:
                await context.bot.send_document(chat_id=chat_id, document=f, filename="KeHoachDuLich.pdf")
            
            save_execution_log(final_state)
            
            await update.effective_message.reply_text(
                "Bạn có muốn tôi sửa đổi hay giúp nghiên cứu thêm gì nữa không? 🔍\n"
                "Ví dụ: 'Tìm thêm quán cafe', 'Đổi sang đi máy bay'...\n"
                "Nếu đã hài lòng, hãy nhắn **'Kết thúc'**."
            )
            
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text(f"⚠️ Có lỗi xảy ra trong quá trình xử lý: {str(e)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Lỗi: Chưa cấu hình TELEGRAM_BOT_TOKEN trong .env")
        exit(1)
        
    application = (
        ApplicationBuilder()
        .token(token)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )
    
    application.add_error_handler(error_handler)
    
    # Chỉ cần 2 Handler duy nhất: Một cho lệnh /start, một cho mọi tin nhắn văn bản
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot (Thin Wrapper) đang chạy...")
    application.run_polling()
