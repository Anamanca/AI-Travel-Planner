# 🌍 AI Travel Planner - Telegram Bot (MAS Edition)

**AI Travel Planner** is an advanced travel assistant powered by a robust **Multi-Agent System (MAS)** architecture. Built on **LangGraph**, it orchestrates specialized AI agents to perform parallel research on transportation, food, attractions, and weather, providing users with comprehensive and verified travel itineraries directly on Telegram.

---

## 🚀 Key Features

- **Parallel Research Architecture:** Utilizes Fan-out/Fan-in patterns to gather data from multiple sources concurrently, significantly reducing response time.
- **Self-Correction (Agentic Loop):** An independent `Evaluator Agent` validates research quality. If data is incomplete or inaccurate, it triggers automated retries (up to 2 times).
- **Multi-Source Intelligence:** Integrates deep web search (**Tavily**) with social media scraping (**Apify** for TikTok & Facebook) to capture both official information and real-world community trends.
- **Professional Reporting:** Automatically generates structured Markdown reports and exports high-quality PDFs with full Unicode (Vietnamese) support.
- **Interactive Feedback Loop:** Maintain a flexible conversation flow where users can refine specific parts of the plan (e.g., "find more cafes") without re-running the entire process.

---

## 🛠️ Tech Stack

- **Core:** Python 3.10+
- **Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph)
- **LLM Engine:** Gemini 3 Flash (via 9Router Proxy) using `crewai.LLM`
- **Search & Scraping:** Tavily Search, Apify (TikTok/Facebook Scrapers)
- **Interface:** `python-telegram-bot`
- **PDF Export:** `fpdf2` with Unicode font embedding

---

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/Anamanca/AI-Travel-Planner.git
cd AI-Travel-Planner
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
NINE_ROUTER_API_KEY=your_9router_api_key
NINE_ROUTER_API_BASE=http://localhost:20128/v1
TAVILY_API_KEY=your_tavily_key
APIFY_API_TOKEN=your_apify_key
```

### 4. Run the Bot
```bash
python src/main.py
```

---

## 📐 System Architecture

The project follows the **Parallel Research -> Automated Evaluation -> Interactive Feedback** model. 
For a detailed technical breakdown, see: [SYSTEM_ARCH.md](./SYSTEM_ARCH.md)

---

## 📜 Version History

- **v1.1.0 (Current):** Implemented parallel MAS architecture, Evaluator retry logic, and real-time research notifications.
- **v1.0.0:** Initial release with sequential MAS workflow.

Full changelog available in: [history.md](./history.md)

---

## 🤝 Contributing

Contributions are welcome! Whether it's improving agent prompts, adding new research tools, or optimizing the LangGraph workflow, feel free to open an issue or submit a pull request.

**Author:** [Anamanca](https://github.com/Anamanca)
