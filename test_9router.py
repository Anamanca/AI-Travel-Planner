import os
import asyncio
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    api_key = os.getenv("NINE_ROUTER_API_KEY")
    base_url = os.getenv("NINE_ROUTER_API_BASE", "https://api.9router.ai/v1")
    
    if not base_url.startswith("http"):
        base_url = "https://api.9router.ai/v1"
        
    print(f"Testing with Base URL: {base_url}")
    print(f"API Key prefix: {api_key[:5]}...")
    
    llm = ChatOpenAI(
        model="openai/gc/gemini-3-flash-preview",
        temperature=0,
        openai_api_key=api_key,
        openai_api_base=base_url,
        max_retries=1
    )
    
    try:
        response = await llm.ainvoke("Hi")
        print("Success!")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
