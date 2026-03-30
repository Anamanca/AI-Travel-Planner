# AI Travel Planner - GEMINI Context

## Project Overview
This project is an advanced AI-powered travel planning assistant delivered via a Telegram Bot. It uses a **Multi-Agent System (MAS)** architecture built on **LangGraph** and **crewai.LLM** to research, evaluate, and interactively refine travel itineraries.

## Core Technologies
- **Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) for stateful, cyclic multi-agent workflows.
- **LLM Engine:** Gemini 3 Flash via **9Router** local proxy (`http://localhost:20128/v1`) using `crewai.LLM`.
- **Interface:** `python-telegram-bot` with `ConversationHandler` and `CallbackQueryHandler`.
- **Search & Scraping:**
    - **Tavily:** Deep web search for travel and weather.
    - **Apify:** Social media research (TikTok, Facebook scrapers).
- **Reporting:** `fpdf2` with Unicode support (`DejaVuSans.ttf`) for Vietnamese PDF export.

## System Architecture & Agents
- `src/main.py`: Entry point; handles NLP-based info collection, confirmation steps, and the interactive feedback loop.
- `src/graph/workflow.py`: Defines the LangGraph state machine.
- `src/agents/`:
    - `InfoExtractorAgent`: Parses unstructured user input into travel details.
    - `TransportAgent`: Researches transport options (Bus/Flight).
    - `DiscoveryAgent`: Scrapes food and attraction recommendations from social media.
    - `WeatherAgent`: Provides localized forecasts.
    - `ReportingAgent`: Compiles data into structured Markdown/PDF reports.
    - `IntentAgent`: Analyzes user feedback to re-trigger specific agents for deeper research.

## Key Workflows
1. **Flexible Info Collection:** User sends free-text messages -> `InfoExtractorAgent` fills `user_info` -> Bot asks only for missing fields.
2. **Confirmation Loop:** Bot summarizes trip details -> User confirms via buttons or corrects info via chat.
3. **Agentic Research:** Sequential execution of Transport, Food, Places, and Weather agents.
4. **Interactive Feedback:** After report delivery, user can ask for more details (e.g., "find more cafes") -> `IntentAgent` routes back to the relevant agent node.

## Operational Notes
- **Starting the Bot:** Run `python src/main.py`. The script automatically adds the project root to `sys.path`.
- **Large Messages:** Uses `send_large_message` to chunk reports exceeding Telegram's 4096-character limit.
- **Resets:** Use `/reset` or `/start` to clear session data and start a new planning cycle.
- **9Router Config:** Ensure `NINE_ROUTER_API_BASE` and `NINE_ROUTER_API_KEY` are set in `.env`.
