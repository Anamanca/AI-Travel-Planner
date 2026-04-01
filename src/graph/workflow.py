from langgraph.graph import StateGraph, END
from src.graph.state import TravelState
from src.agents.specialists import TransportAgent, DiscoveryAgent, WeatherAgent
from src.agents.base import EvaluatorAgent, IntentAgent, InfoExtractorAgent
from src.agents.reporting import ReportingAgent
import logging
import os
import asyncio
from telegram import Bot

logger = logging.getLogger(__name__)

def print_agent_status(name, reasoning, action):
    """In log trạng thái Agent ra Terminal theo yêu cầu của user."""
    print(f"\n{'='*80}")
    print(f"🤖 AGENT_NAME : {name}")
    print(f"🧠 REASONING  : {reasoning}")
    print(f"➡️ ACTION      : {action}")
    print(f"{'='*80}\n")

def create_travel_graph():
    workflow = StateGraph(TravelState)
    
    # Khởi tạo các Agent
    evaluator = EvaluatorAgent()
    intent_agent = IntentAgent()
    extractor = InfoExtractorAgent()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    async def notify_user(chat_id, message):
        """Gửi thông báo nhanh cho user qua Telegram."""
        if bot_token and chat_id:
            try:
                bot = Bot(token=bot_token)
                await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error sending notification: {e}")

    # --- ĐỊNH NGHĨA CÁC NODE ---

    async def info_extractor_node(state):
        logger.info("--- NODE: Info Extractor ---")
        user_feedback = state.get("user_feedback", "")
        current_info = state.get("user_info", {})
        
        if user_feedback:
            updated_info = await asyncio.to_thread(extractor.extract, user_feedback, current_info)
            print_agent_status(
                "InfoExtractorAgent", 
                f"Đã trích xuất thông tin từ tin nhắn: '{user_feedback[:50]}...'", 
                "Chuyển sang IntentAgent để phân tích bước tiếp theo."
            )
            return {"user_info": updated_info}
            
        print_agent_status("InfoExtractorAgent", "Không có thông tin mới để trích xuất.", "Chuyển sang IntentAgent.")
        return {"user_info": current_info}

    async def intent_node(state):
        logger.info("--- NODE: Intent Agent ---")
        user_info = state.get("user_info", {})
        
        # 1. Kiểm tra thiếu thông tin bắt buộc
        required_fields = ["destination", "from", "date_start", "date_end", "people_among", "transport","purpose"]
        missing = [f for f in required_fields if not user_info.get(f)]
        
        if missing:
            print_agent_status(
                "IntentAgent", 
                f"Phát hiện thiếu thông tin: {', '.join(missing)}", 
                "Chuyển đến Reporting để yêu cầu User bổ sung."
            )
            return {"intent": ["ask_info"]}
            
        # 2. Nếu đã đủ thông tin nhưng chưa có kết quả research -> Research lần đầu
        if not state.get("results"):
            print_agent_status(
                "IntentAgent", 
                "Thông tin đã đủ. Bắt đầu giai đoạn nghiên cứu đa nguồn (Fan-out).", 
                "Kích hoạt Transport, Food, Places, Weather Nodes."
            )
            return {"intent": ["transport", "food", "places", "weather"]}
            
        # 3. Nếu đã có kết quả và có feedback mới -> Phân tích feedback
        user_feedback = state.get("user_feedback", "")
        if user_feedback:
            intents = await asyncio.to_thread(intent_agent.analyze, user_feedback)
            # Normalize intents to list
            if isinstance(intents, str):
                possible_intents = ['transport', 'food', 'places', 'weather', 'finish', 'other']
                found_intents = [i for i in possible_intents if i in intents.lower()]
                intents = found_intents if found_intents else ["other"]
            
            print_agent_status(
                "IntentAgent", 
                f"Phân tích ý định người dùng: {intents}", 
                f"Chuyển hướng đến các node: {intents}"
            )
            return {"intent": intents}
            
        print_agent_status("IntentAgent", "Không có yêu cầu mới.", "Chuyển sang Reporting.")
        return {"intent": ["reporting"]}

    async def transport_node(state):
        mode = state['user_info'].get('transport', 'bus')
        agent = TransportAgent(mode=mode)
        res = await asyncio.to_thread(agent.run, state)
        print_agent_status(
            "TransportAgent", 
            f"Đã tìm kiếm phương tiện {mode} cho chặng {state['user_info'].get('from')} - {state['user_info'].get('destination')}.", 
            "Chuyển sang eva_transport để kiểm tra chất lượng dữ liệu."
        )
        return {**res}

    async def food_node(state):
        agent = DiscoveryAgent(type="food")
        res = await asyncio.to_thread(agent.run, state)
        print_agent_status(
            "FoodAgent", 
            f"Đã tìm kiếm quán ăn ngon tại {state['user_info'].get('destination')} từ TikTok, Facebook và Web.", 
            "Chuyển sang eva_food để đánh giá."
        )
        return {**res}

    async def places_node(state):
        agent = DiscoveryAgent(type="places")
        res = await asyncio.to_thread(agent.run, state)
        print_agent_status(
            "PlacesAgent", 
            f"Đã tổng hợp các địa điểm vui chơi/cafe tại {state['user_info'].get('destination')}.", 
            "Chuyển sang eva_places để đánh giá."
        )
        return {**res}

    async def weather_node(state):
        agent = WeatherAgent()
        res = await asyncio.to_thread(agent.run, state)
        print_agent_status(
            "WeatherAgent", 
            f"Đã cập nhật dự báo thời tiết tại {state['user_info'].get('destination')}.", 
            "Chuyển sang eva_weather để kiểm tra."
        )
        return {**res}

    async def _generic_evaluator(state, agent_name):
        res = await asyncio.to_thread(evaluator.evaluate, state, agent_name)
        status = "HỢP LỆ ✅" if res['is_valid'] else "KHÔNG ĐẠT ❌"
        
        # Determine next action text
        next_action = "Hội tụ về Reporting."
        if not res['is_valid']:
            count = state.get('retry_counts', {}).get(agent_name, 0) + 1
            if count <= 2:
                next_action = f"Yêu cầu {agent_name} làm lại (Lần {count})."
            else:
                next_action = "Đã hết lượt retry, chấp nhận dữ liệu và đi đến Reporting."

        print_agent_status(
            f"Evaluator ({agent_name})", 
            f"Kết quả đánh giá: {status}. {res.get('feedback', '')}", 
            next_action
        )
        
        if not res['is_valid']:
            current_retry = state.get('retry_counts', {}).get(agent_name, 0) + 1
            if current_retry <= 2:
                return {
                    "evaluator_feedback": [{"agent": agent_name, "is_valid": False, "feedback": res['feedback']}],
                    "retry_counts": {agent_name: current_retry}
                }
        
        return {"evaluator_feedback": [{"agent": agent_name, "is_valid": True, "feedback": "OK"}]}

    async def eva_transport(state):
        # Lấy chính xác tên agent transport đang chạy dựa trên mode
        mode = state['user_info'].get('transport', 'bus')
        agent_name = f"transport_{mode}"
        return await _generic_evaluator(state, agent_name)

    async def eva_food(state): return await _generic_evaluator(state, "discovery_food")
    async def eva_places(state): return await _generic_evaluator(state, "discovery_places")
    async def eva_weather(state): return await _generic_evaluator(state, "weather")

    async def reporting_node(state):
        intents = state.get("intent", [])
        if "ask_info" in intents:
            print_agent_status("ReportingAgent", "Thông tin chưa đủ để lập kế hoạch.", "Gửi yêu cầu bổ sung thông tin cho User.")
            user_info = state.get("user_info", {})
            required = {"destination": "Điểm đến", "from": "Điểm đi", "date_start": "Ngày đi", "date_end": "Ngày về","people_among": "Số người", "transport": "Phương tiện", "purpose": "Mục đích"}
            missing = [label for field, label in required.items() if not user_info.get(field)]
            msg = f"Tôi đã ghi nhận thông tin. Tuy nhiên, tôi vẫn còn thiếu: **{', '.join(missing)}**.\n\nHãy cung cấp thêm nhé!"
            return {"final_report": msg, "user_feedback": ""}

        agent = ReportingAgent()
        res = await asyncio.to_thread(agent.run, state)
        print_agent_status(
            "ReportingAgent", 
            "Đã tổng hợp dữ liệu từ tất cả các Agent thành báo cáo Markdown hoàn chỉnh.", 
            "Gửi báo cáo và PDF cho User. Chờ phản hồi."
        )
        return {**res, "user_feedback": ""}

    # --- LOGIC ĐIỀU HƯỚNG ---

    def route_from_intent(state):
        intents = state.get("intent", [])
        if "finish" in intents: return "end"
        if "ask_info" in intents: return "reporting"
        targets = []
        if "transport" in intents: targets.append("transport")
        if "food" in intents: targets.append("food")
        if "places" in intents: targets.append("places")
        if "weather" in intents: targets.append("weather")
        return targets if targets else ["reporting"]

    def _should_retry(state, agent_type_keyword):
        feedbacks = state.get("evaluator_feedback", [])
        agent_feedback = next((f for f in reversed(feedbacks) if agent_type_keyword in f['agent']), None)
        if agent_feedback and not agent_feedback['is_valid']:
            count = state.get("retry_counts", {}).get(agent_feedback['agent'], 0)
            if count < 2:
                if "transport" in agent_type_keyword: return "transport"
                if "food" in agent_type_keyword: return "food"
                if "places" in agent_type_keyword: return "places"
                if "weather" in agent_type_keyword: return "weather"
        return "reporting"

    def should_retry_transport(state): return _should_retry(state, "transport")
    def should_retry_food(state): return _should_retry(state, "food")
    def should_retry_places(state): return _should_retry(state, "places")
    def should_retry_weather(state): return _should_retry(state, "weather")

    # --- XÂY DỰNG WORKFLOW ---

    workflow.add_node("InfoExtractorAgent", info_extractor_node)
    workflow.add_node("IntentAgent", intent_node)
    workflow.add_node("transport", transport_node)
    workflow.add_node("food", food_node)
    workflow.add_node("places", places_node)
    workflow.add_node("weather", weather_node)
    workflow.add_node("eva_transport", eva_transport)
    workflow.add_node("eva_food", eva_food)
    workflow.add_node("eva_places", eva_places)
    workflow.add_node("eva_weather", eva_weather)
    workflow.add_node("reporting", reporting_node)

    workflow.set_entry_point("InfoExtractorAgent")
    workflow.add_edge("InfoExtractorAgent", "IntentAgent")

    workflow.add_conditional_edges("IntentAgent", route_from_intent, {
        "transport": "transport", "food": "food", "places": "places", 
        "weather": "weather", "reporting": "reporting", "end": END
    })

    workflow.add_edge("transport", "eva_transport")
    workflow.add_edge("food", "eva_food")
    workflow.add_edge("places", "eva_places")
    workflow.add_edge("weather", "eva_weather")

    workflow.add_conditional_edges("eva_transport", should_retry_transport, {"transport": "transport", "reporting": "reporting"})
    workflow.add_conditional_edges("eva_food", should_retry_food, {"food": "food", "reporting": "reporting"})
    workflow.add_conditional_edges("eva_places", should_retry_places, {"places": "places", "reporting": "reporting"})
    workflow.add_conditional_edges("eva_weather", should_retry_weather, {"weather": "weather", "reporting": "reporting"})

    workflow.add_edge("reporting", END)

    return workflow.compile()
