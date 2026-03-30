from langgraph.graph import StateGraph, END
from src.graph.state import TravelState
from src.agents.specialists import TransportAgent, DiscoveryAgent, WeatherAgent
from src.agents.base import EvaluatorAgent, IntentAgent
from src.agents.reporting import ReportingAgent
import logging
import os
import asyncio
from telegram import Bot

logger = logging.getLogger(__name__)

def create_travel_graph():
    workflow = StateGraph(TravelState)
    evaluator = EvaluatorAgent()
    intent_agent = IntentAgent()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    async def notify_user(chat_id, message):
        """Gửi thông báo nhanh cho user qua Telegram."""
        if bot_token and chat_id:
            try:
                bot = Bot(token=bot_token)
                await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error sending notification: {e}")

    # --- ĐỊNH NGHĨA CÁC NODE (Chuyển sang async def) ---
    async def transport_node(state):
        logger.info("--- NODE: Transport ---")
        agent = TransportAgent(mode=state['user_info'].get('transport', 'bus'))
        # Chạy trong thread pool vì agent.run là sync
        res = await asyncio.to_thread(agent.run, state)
        return {**res, "current_agent": [agent.name]}

    async def food_node(state):
        logger.info("--- NODE: Discovery (Food) ---")
        agent = DiscoveryAgent(type="food")
        res = await asyncio.to_thread(agent.run, state)
        return {**res, "current_agent": [agent.name]}

    async def places_node(state):
        logger.info("--- NODE: Discovery (Places) ---")
        agent = DiscoveryAgent(type="places")
        res = await asyncio.to_thread(agent.run, state)
        return {**res, "current_agent": [agent.name]}

    async def weather_node(state):
        logger.info("--- NODE: Weather ---")
        agent = WeatherAgent()
        res = await asyncio.to_thread(agent.run, state)
        return {**res, "current_agent": ["weather"]}

    async def evaluation_node(state):
        logger.info("--- NODE: Evaluation ---")
        agents_to_check = state.get('current_agent', [])
        retry_counts = state.get('retry_counts', {})
        chat_id = state.get('chat_id')
        
        if not agents_to_check:
            return {"is_valid": True}
            
        all_valid = True
        failed_agent = ""
        
        for agent_name in agents_to_check:
            # evaluator.evaluate cũng là sync nên chạy trong thread
            res = await asyncio.to_thread(evaluator.evaluate, state, agent_name)
            if not res['is_valid']:
                current_retry = retry_counts.get(agent_name, 0) + 1
                
                if current_retry <= 2:
                    agent_label = agent_name.replace("discovery_", "").replace("transport_", "")
                    # Thông báo tối đa 2 lần thử
                    await notify_user(chat_id, f"🔍 AI đang kiểm tra lại thông tin về **{agent_label}** (Lần {current_retry}/2)...")
                
                return {
                    "is_valid": False, 
                    "current_agent": [], 
                    "last_failed_agent": agent_name,
                    "retry_counts": {agent_name: current_retry}
                }
        
        return {
            "is_valid": True, 
            "current_agent": [], 
            "last_failed_agent": ""
        }

    async def reporting_node(state):
        logger.info("--- NODE: Reporting ---")
        agent = ReportingAgent()
        res = await asyncio.to_thread(agent.run, state)
        return res

    async def router_node(state):
        logger.info(f"--- NODE: Router (Feedback: {state.get('user_feedback')}) ---")
        feedback = state.get("user_feedback", "")
        if not feedback:
            return {"intent": "finish"}
        
        intent = await asyncio.to_thread(intent_agent.analyze, feedback)
        logger.info(f"Analyzed Intent: {intent}")
        return {"intent": intent}

    # --- THÊM NODE VÀO GRAPH ---
    workflow.add_node("transport", transport_node)
    workflow.add_node("food", food_node)
    workflow.add_node("places", places_node)
    workflow.add_node("weather", weather_node)
    workflow.add_node("evaluator", evaluation_node)
    workflow.add_node("reporting", reporting_node)
    workflow.add_node("router", router_node)

    # --- THIẾT LẬP LUỒNG ĐI (EDGES) ---
    workflow.set_entry_point("transport")
    workflow.add_edge("transport", "food")
    workflow.add_edge("transport", "places")
    workflow.add_edge("transport", "weather")
    workflow.add_edge("food", "evaluator")
    workflow.add_edge("places", "evaluator")
    workflow.add_edge("weather", "evaluator")

    def should_continue(state):
        if state.get("is_valid"):
            return "reporting"
        else:
            failed = state.get("last_failed_agent", "")
            retry_counts = state.get("retry_counts", {})
            # GIỚI HẠN 2 LẦN RETRY
            if retry_counts.get(failed, 0) >= 2:
                logger.warning(f"Max retries reached for {failed}. Moving to reporting.")
                return "reporting"
                
            if "transport" in failed: return "transport"
            if "food" in failed: return "food"
            if "places" in failed: return "places"
            if "weather" in failed: return "weather"
            return "reporting"

    workflow.add_conditional_edges(
        "evaluator",
        should_continue,
        {
            "reporting": "reporting",
            "transport": "transport",
            "food": "food",
            "places": "places",
            "weather": "weather"
        }
    )

    workflow.add_edge("reporting", END)
    workflow.add_edge("router", END) 

    return workflow.compile()
