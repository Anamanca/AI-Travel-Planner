from langgraph.graph import StateGraph, END
from src.graph.state import TravelState
from src.agents.specialists import TransportAgent, DiscoveryAgent, WeatherAgent
from src.agents.base import EvaluatorAgent, IntentAgent
from src.agents.reporting import ReportingAgent
import logging

logger = logging.getLogger(__name__)

def create_travel_graph():
    workflow = StateGraph(TravelState)
    evaluator = EvaluatorAgent()
    intent_agent = IntentAgent()

    # Định nghĩa các Node (Tác nhân)
    def transport_node(state):
        logger.info("--- NODE: Transport ---")
        agent = TransportAgent(mode=state['user_info'].get('transport', 'bus'))
        return agent.run(state)

    def food_node(state):
        logger.info("--- NODE: Discovery (Food) ---")
        agent = DiscoveryAgent(type="food")
        return agent.run(state)

    def places_node(state):
        logger.info("--- NODE: Discovery (Places) ---")
        agent = DiscoveryAgent(type="places")
        return agent.run(state)

    def weather_node(state):
        logger.info("--- NODE: Weather ---")
        agent = WeatherAgent()
        return agent.run(state)

    def evaluation_node(state):
        logger.info("--- NODE: Evaluation ---")
        res = evaluator.evaluate(state, state.get('current_agent', ''))
        return {"evaluator_feedback": [res], "is_valid": res['is_valid']}

    def reporting_node(state):
        logger.info("--- NODE: Reporting ---")
        agent = ReportingAgent()
        return agent.run(state)

    def router_node(state):
        logger.info(f"--- NODE: Router (User Feedback: {state.get('user_feedback')}) ---")
        # Phân tích ý định từ feedback của người dùng
        feedback = state.get("user_feedback", "")
        if not feedback:
            return {"intent": "finish"}
        
        intent = intent_agent.analyze(feedback)
        logger.info(f"Analyzed Intent: {intent}")
        return {"intent": intent}

    # Thêm Node vào Graph
    workflow.add_node("transport", transport_node)
    workflow.add_node("food", food_node)
    workflow.add_node("places", places_node)
    workflow.add_node("weather", weather_node)
    workflow.add_node("evaluator", evaluation_node)
    workflow.add_node("reporting", reporting_node)
    workflow.add_node("router", router_node)

    # Định nghĩa các Edge (Luồng đi)
    workflow.set_entry_point("transport")
    
    # Luồng tuần tự ban đầu
    workflow.add_edge("transport", "food")
    workflow.add_edge("food", "places")
    workflow.add_edge("places", "weather")
    workflow.add_edge("weather", "reporting")
    
    # Sau khi Reporting, Graph sẽ dừng lại để đợi feedback từ main.py
    # Ở phiên bản này, ta sẽ kết thúc Graph và main.py sẽ re-invoke khi có tin nhắn mới
    workflow.add_edge("reporting", END)

    # Các node phục vụ cho Interactive Mode (khi được gọi trực tiếp từ router)
    workflow.add_edge("router", END) # RouterNode sẽ được sử dụng để quyết định node tiếp theo trong main.py

    return workflow.compile()
