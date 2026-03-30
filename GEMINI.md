# AI Travel Planner - GEMINI Context (v1.1.0)

## Project Overview
An advanced AI-powered travel planning assistant on Telegram, using a **Parallel Multi-Agent System (MAS)** built on **LangGraph**.

## Core Technologies
- **Orchestration:** LangGraph (Async, Cyclic, Parallel).
- **LLM:** Gemini 3 Flash via 9Router (`crewai.LLM`).
- **Research:** Tavily (Web), Apify (Social Media).
- **Reporting:** fpdf2 (UTF-8 support).

## Advanced Workflow & Agents
- **Parallel Research Node:** Concurrent execution of `Transport`, `Food`, `Places`, and `Weather` agents using Fan-out.
- **Self-Correction Logic:** `EvaluatorAgent` validates all research results. It triggers retries (max 2) if quality thresholds aren't met.
- **Async Execution:** All Graph Nodes are `async def`, wrapping synchronous agent runs in `asyncio.to_thread`.
- **Concurrent State Management:** `TravelState` uses `Annotated` with `operator.ior` and `operator.add` for safe parallel updates.
- **Interaction Loop:** IntentAgent handles user feedback (e.g., "more cafes") to re-trigger specific nodes without re-running the whole graph.

## Key Files
- `src/graph/workflow.py`: Parallel graph definition with retry logic.
- `src/graph/state.py`: Concurrent state schema.
- `src/agents/specialists.py`: Specialist agents with strict JSON prompts.
- `src/main.py`: Telegram ConversationHandler and Async Graph invocation.

## Operational Notes
- **Retries:** Graph sends real-time Telegram notifications during evaluation retries.
- **Reporting:** Automatic PDF generation with Unicode support.
- **Reset:** Use `/reset` or `/start` to clear session context.
