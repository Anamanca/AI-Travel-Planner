import os
import sys
import logging

# Thêm thư mục gốc của project vào sys.path để có thể import từ src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from dotenv import load_dotenv
from src.graph.workflow import create_travel_graph
from src.agents.reporting import PDFExporter, save_execution_log
from src.agents.base import InfoExtractorAgent, IntentAgent

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# State definitions for ConversationHandler
COLLECTING, CONFIRMING, FEEDBACK = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bắt đầu cuộc hội thoại và hướng dẫn user cung cấp thông tin."""
    # Reset toàn bộ dữ liệu cũ
    context.user_data.clear()
    
    context.user_data['user_info'] = {
        "from": "", "destination": "", "date_start": "", 
        "date_end": "", "people": "", "purpose": "", "transport": ""
    }
    
    welcome_msg = (
        "Chào mừng bạn đến với **AI Travel Planner**! 🌍✈️\n\n"
        "Tôi đã sẵn sàng cho một kế hoạch mới. Hãy cung cấp các thông tin sau:\n"
        "📍 **Điểm đi & Điểm đến**\n"
        "📅 **Ngày đi & Ngày về**\n"
        "👥 **Số lượng người**\n"
        "🎯 **Mục đích**\n"
        "🚌 **Phương tiện**\n\n"
        "--- \n"
        "💡 **Ví dụ:** *'Tôi muốn đi Đà Lạt từ Hà Nội từ 01/05 đến 05/05, có 2 người đi nghỉ dưỡng bằng máy bay'*."
    )
    
    await update.effective_message.reply_text(welcome_msg, parse_mode='Markdown')
    return COLLECTING

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lệnh /reset để xóa dữ liệu và bắt đầu lại."""
    await update.message.reply_text("♻️ Đã xóa toàn bộ dữ liệu cũ. Chúng ta bắt đầu lại nhé!")
    return await start(update, context)

async def handle_collection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    logger.info(f"Collecting info from text: {user_text}")
    
    extractor = InfoExtractorAgent()
    current_info = context.user_data.get('user_info', {})
    
    # Bóc tách thông tin
    updated_info = extractor.extract(user_text, current_info)
    context.user_data['user_info'] = updated_info
    
    # Kiểm tra xem còn thiếu gì không
    missing_fields = []
    field_labels = {
        "from": "Điểm xuất phát",
        "destination": "Điểm đến",
        "date_start": "Ngày đi",
        "date_end": "Ngày về",
        "people": "Số người",
        "purpose": "Mục đích",
        "transport": "Phương tiện"
    }
    
    for field, label in field_labels.items():
        if not updated_info.get(field):
            missing_fields.append(label)
            
    if missing_fields:
        missing_str = ", ".join(missing_fields)
        await update.message.reply_text(
            f"Cảm ơn bạn! Tôi đã ghi nhận thông tin. Tuy nhiên, tôi vẫn còn thiếu: **{missing_str}**.\n\n"
            "Hãy cung cấp thêm các thông tin còn thiếu nhé!"
        )
        return COLLECTING
    
    # Nếu đã đủ thông tin -> Chuyển sang Confirm
    return await show_confirmation(update, context)

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    info = context.user_data['user_info']
    summary = (
        "📍 **XÁC NHẬN THÔNG TIN CHUYẾN ĐI**\n\n"
        f"1. Đi từ: {info['from']}\n"
        f"2. Điểm đến: {info['destination']}\n"
        f"3. Thời gian: {info['date_start']} - {info['date_end']}\n"
        f"4. Số người: {info['people']}\n"
        f"5. Mục đích: {info['purpose']}\n"
        f"6. Phương tiện: {info['transport']}\n\n"
        "Thông tin này đã chính xác chưa? Bạn có thể nhấn nút bên dưới để bắt đầu hoặc nhắn tin để sửa lại."
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Chính xác, bắt đầu ngay!", callback_data="confirm_ok")],
        [InlineKeyboardButton("✏️ Tôi muốn sửa lại", callback_data="confirm_edit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
        
    return CONFIRMING

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_ok":
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.reply_text("Tuyệt vời! Đội ngũ AI Agents đang bắt đầu làm việc. Vui lòng đợi trong giây lát... 🚀")
        
        # Init LangGraph State
        info = context.user_data['user_info']
        state = {
            "user_info": info,
            "results": {},
            "evaluator_feedback": [],
            "retry_counts": {},
            "final_report": "",
            "current_agent": "",
            "execution_logs": [],
            "user_feedback": "",
            "intent": ""
        }
        context.user_data['graph_state'] = state
        return await run_and_report(update, context)
    
    elif query.data == "confirm_edit":
        await query.message.reply_text("Vâng, bạn hãy nhắn lại những thông tin cần thay đổi nhé!")
        return COLLECTING

async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Tái sử dụng handle_collection để cập nhật thông tin
    return await handle_collection(update, context)

# ... (Giữ nguyên run_and_report, handle_feedback, start, etc.)

async def send_large_message(update: Update, text: str):
    """Chia nhỏ tin nhắn lớn để gửi tránh lỗi giới hạn 4096 ký tự của Telegram."""
    if len(text) <= 4000:
        await update.effective_message.reply_text(text)
        return

    # Chia nhỏ theo đoạn văn để tránh cắt giữa chừng câu
    parts = []
    while len(text) > 0:
        if len(text) <= 4000:
            parts.append(text)
            break
        
        # Tìm vị trí ngắt dòng gần nhất trong phạm vi 4000 ký tự
        chunk = text[:4000]
        last_newline = chunk.rfind('\n')
        
        if last_newline != -1 and last_newline > 3000:
            parts.append(text[:last_newline])
            text = text[last_newline:].lstrip()
        else:
            parts.append(text[:4000])
            text = text[4000:]

    for part in parts:
        await update.effective_message.reply_text(part)

async def run_and_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    state = context.user_data['graph_state']
    chat_id = update.effective_chat.id
    
    try:
        graph = create_travel_graph()
        # Chạy toàn bộ graph (hoặc từ điểm cụ thể)
        final_state = await graph.ainvoke(state)
        
        # Cập nhật state vào user_data để dùng cho lần kế tiếp
        context.user_data['graph_state'] = final_state
        
        # Gửi báo cáo Markdown (Sử dụng hàm chia nhỏ tin nhắn)
        report = final_state.get('final_report', 'Không có báo cáo.')
        await update.effective_message.reply_text("✅ **Kế hoạch của bạn đã hoàn thành!**", parse_mode='Markdown')
        await send_large_message(update, report)
        
        # Xuất PDF
        pdf_path = f"output/plan_{chat_id}.pdf"
        PDFExporter.export(report, pdf_path)
        
        # Gửi file PDF
        with open(pdf_path, 'rb') as f:
            await context.bot.send_document(chat_id=chat_id, document=f, filename="KeHoachDuLich.pdf")
            
        # Lưu Log
        save_execution_log(final_state)
        
        await update.effective_message.reply_text(
            "Bạn có muốn tôi sửa đổi hay giúp research thêm gì nữa không? 🔍\n"
            "Ví dụ: 'Tìm thêm quán cafe', 'Đổi sang đi máy bay'...\n"
            "Nếu đã hài lòng, hãy nhắn 'Kết thúc' hoặc 'Xong'."
        )
        return FEEDBACK
        
    except Exception as e:
        logger.error(f"Error running graph: {e}")
        await update.effective_message.reply_text(f"Có lỗi xảy ra trong quá trình xử lý: {str(e)}")
        return ConversationHandler.END

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    logger.info(f"User Feedback received: {user_text}")
    
    state = context.user_data.get('graph_state')
    if not state:
        await update.message.reply_text("Xin lỗi, phiên làm việc đã hết hạn. Vui lòng dùng /start để bắt đầu lại.")
        return ConversationHandler.END

    # Cập nhật feedback vào state
    state['user_feedback'] = user_text
    
    try:
        # Bước 1: Chạy RouterNode để xác định ý định
        graph = create_travel_graph()
        # Chỉ chạy node router
        router_state = await graph.ainvoke(state, {"configurable": {"thread_id": "1"}, "interrupt_after": ["router"]})
        # Note: Do cấu hình graph đơn giản, ta sẽ dùng LLM trực tiếp hoặc invoke router node
        # Để đơn giản và chính xác nhất, ta invoke graph với feedback và để nó tự routing
        # Nhưng vì graph hiện tại kết thúc ở reporting, ta sẽ dùng logic routing ở đây
        
        from src.agents.base import IntentAgent
        intent_agent = IntentAgent()
        intent = intent_agent.analyze(user_text)
        logger.info(f"Detected Intent in main: {intent}")
        
        if intent == "finish":
            await update.message.reply_text("Chúc bạn có một chuyến đi tuyệt vời! 🌟 Hẹn gặp lại.")
            return await start(update, context) # Reset và bắt đầu lại

        # Nếu user muốn research thêm
        await update.message.reply_text(f"Đang thực hiện research thêm về '{intent}'... 🚀")
        
        # Cấu hình node mục tiêu dựa trên intent
        node_map = {
            "transport": "transport",
            "food": "food",
            "places": "places",
            "weather": "weather",
            "other": "food" # Mặc định nếu không rõ
        }
        target_node = node_map.get(intent, "food")
        
        # Chạy lại graph từ node được yêu cầu
        # Trong LangGraph thực tế, ta dùng `update_state` và resume, 
        # nhưng ở đây ta sẽ invoke lại từ node đó bằng cách điều chỉnh workflow nếu cần
        # Cách đơn giản nhất: Chạy lại node đó và chạy tiếp tới reporting
        final_state = await graph.ainvoke(state, {"configurable": {"thread_id": "1"}})
        
        # Để thực sự research THÊM mà không mất cái cũ, kết quả đã được merge nhờ operator.ior trong TravelState
        # Ta chỉ cần chạy lại graph
        return await run_and_report(update, context)

    except Exception as e:
        logger.error(f"Error in handle_feedback: {e}")
        await update.message.reply_text("Có lỗi xảy ra khi xử lý yêu cầu thêm. Vui lòng thử lại.")
        return FEEDBACK

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Đã hủy quy trình lên kế hoạch. Hẹn gặp lại!")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Xin lỗi, có lỗi kết nối với máy chủ Telegram (Timeout). Vui lòng thử lại sau giây lát."
        )

if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Lỗi: Chưa cấu hình TELEGRAM_BOT_TOKEN trong .env")
        exit(1)
        
    # Tăng timeout để tránh lỗi TimedOut khi mạng chậm
    application = (
        ApplicationBuilder()
        .token(token)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    application.add_error_handler(error_handler)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            COLLECTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_collection)],
            CONFIRMING: [
                CallbackQueryHandler(confirm_callback, pattern="^confirm_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit)
            ],
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    
    print("Bot đang chạy...")
    application.run_polling()
