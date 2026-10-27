import os
import asyncio
from typing import List, Optional
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
scheduler = AsyncIOScheduler()

class MonitorTarget(BaseModel):
    id: str
    name: str
    url: HttpUrl
    expected_condition: str  # e.g., 'User profile details should be present without error messages'
    interval_seconds: int = 60

targets_db: List[MonitorTarget] = [
    MonitorTarget(
        id="checkout-api",
        name="Checkout Health",
        url="https://httpbin.org/json",
        expected_condition="Must contain valid slideshow details with non-empty author field",
        interval_seconds=60
    )
]

async def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[ALERT] Telegram not configured. Message: {message}")
        return
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as http_client:
        try:
            await http_client.post(telegram_url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            })
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")

async def inspect_target_health(target: MonitorTarget):
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        try:
            response = await http_client.get(str(target.url))
            status_code = response.status_code
            body_snippet = response.text[:2000]
        except Exception as e:
            await send_telegram_alert(f"🚨 *CRITICAL:* Target `{target.name}` unreachable! Error: `{str(e)}`")
            return

    if not client:
        print("OpenAI client not configured. Skipping semantic analysis.")
        return

    prompt = f"""
    Analyze this HTTP response against the expectation criteria.
    Target Name: {target.name}
    Status Code: {status_code}
    Assertion: {target.expected_condition}
    Response Body (truncated):
    ```
    {body_snippet}
    ```
    Does the response satisfy the assertion and indicate normal operation?
    Reply in STRICT format: 'STATUS: OK' or 'STATUS: FAIL | Reason: <brief explanation>'
    """
    try:
        ai_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        result = ai_response.choices[0].message.content.strip()
        if "STATUS: FAIL" in result:
            await send_telegram_alert(
                f"⚠️ *Semantic Outage Detected!*
Target: `{target.name}`
URL: {target.url}
HTTP Status: `{status_code}`
Analysis: `{result}`"
            )
        else:
            print(f"[HEALTHY] {target.name} passed semantic inspection.")
    except Exception as e:
        print(f"LLM assertion error: {e}")

async def run_all_monitors():
    for target in targets_db:
        await inspect_target_health(target)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_all_monitors, "interval", seconds=60)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="UptimePulse AI", lifespan=lifespan)

@app.get("/")
async def root():
    return {"service": "UptimePulse AI", "active_monitors": len(targets_db), "status": "running"}

@app.post("/targets")
async def add_target(target: MonitorTarget):
    targets_db.append(target)
    return {"status": "added", "target": target}

@app.post("/check-now/{target_id}")
async def manual_check(target_id: str, background_tasks: BackgroundTasks):
    target = next((t for t in targets_db if t.id == target_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    background_tasks.add_task(inspect_target_health, target)
    return {"status": "triggered", "target_id": target_id}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT", 8000)), reload=True)
