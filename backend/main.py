from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

# Load env
load_dotenv()

# Supabase
from supabase import create_client, Client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
if not url or not key:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
supabase: Client = create_client(url, key)

app = FastAPI()

# CORS for Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://quizzy-tg-mini-app-frontend.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADSTERRA_DL_URL = os.getenv("ADSTERRA_DL_URL", "https://go.adsterra.com/your-dl-id/")

# === ROUTES ===


@app.get("/api/user")
async def get_user(telegram_id: int):
    """Get or create user"""
    # Check if user exists
    user = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    if len(user.data) == 0:
        # Create user
        new_user = {
            "telegram_id": telegram_id,
            "first_name": "Anonymous",
            "virtual_stars": 0,
            "real_stars_redeemed": 0,
            "surveys_completed": 0,
            "last_active": datetime.utcnow().isoformat(),
        }
        supabase.table("users").insert(new_user).execute()
        return new_user
    else:
        # Update last_active
        supabase.table("users").update(
            {"last_active": datetime.utcnow().isoformat()}
        ).eq("telegram_id", telegram_id).execute()
        return user.data[0]


@app.post("/api/start-survey")
async def start_survey(request: Request):
    """Start new survey session"""
    data = await request.json()
    telegram_id = data.get("telegram_id")

    # Create survey session
    session = {
        "user_id": telegram_id,
        "started_at": datetime.utcnow().isoformat(),
        "current_step": 1,
        "answers": {},
    }
    result = supabase.table("survey_sessions").insert(session).execute()
    session_id = result.data[0]["id"]

    return {"session_id": session_id, "step": 1}


@app.post("/api/submit-answer")
async def submit_answer(request: Request):
    """Submit answer → redirect to Adsterra DL"""
    data = await request.json()
    telegram_id = data.get("telegram_id")
    session_id = data.get("session_id")
    step = data.get("step")
    answer = data.get("answer")

    # Update survey session
    current = (
        supabase.table("survey_sessions")
        .select("answers")
        .eq("id", session_id)
        .execute()
    )
    answers = current.data[0]["answers"] if current.data else {}
    answers[f"q{step}"] = answer

    supabase.table("survey_sessions").update(
        {"current_step": step + 1, "answers": answers}
    ).eq("id", session_id).execute()

    # Redirect to Adsterra DL
    dl_url = f"{ADSTERRA_DL_URL}?user_id={telegram_id}&step={step}&action=survey"
    return RedirectResponse(dl_url)


@app.get("/webhook/adsterra-return")
async def adsterra_return(user_id: int, step: int):
    """Adsterra return URL → redirect to frontend"""
    # Log click (optional)
    print(f"Adsterra click logged: user_id={user_id}, step={step}")

    # Redirect to frontend with step
    frontend_url = f"https://quizzy-tg-mini-app-frontend.onrender.com?user_id={user_id}&step={step}"
    return RedirectResponse(frontend_url)


@app.post("/api/complete-survey")
async def complete_survey(request: Request):
    """Mark survey complete → schedule star reward"""
    data = await request.json()
    telegram_id = data.get("telegram_id")
    session_id = data.get("session_id")

    # Mark survey complete
    supabase.table("survey_sessions").update(
        {"completed_at": datetime.utcnow().isoformat()}
    ).eq("id", session_id).execute()

    # Increment surveys_completed
    user = supabase.table("users").select("surveys_completed").eq("telegram_id", telegram_id).execute()
    current_completed = user.data[0]["surveys_completed"] if user.data else 0
    supabase.table("users").update(
        {"surveys_completed": current_completed + 1}
    ).eq("telegram_id", telegram_id).execute()

    return {"message": "Survey completed. Check back in 2h for 20 Stars!"}


@app.get("/api/claim-reward")
async def claim_reward(telegram_id: int):
    """Claim 20 Virtual Stars after 2h wait"""
    # For MVP — grant stars immediately (in real app, check 2h delay)
    # Fetch current stars
    user = (
        supabase.table("users")
        .select("virtual_stars")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    current_stars = user.data[0]["virtual_stars"] if user.data else 0
    supabase.table("users").update(
        {"virtual_stars": current_stars + 20}
    ).eq("telegram_id", telegram_id).execute()

    # Log transaction
    supabase.table("star_transactions").insert(
        {
            "user_id": telegram_id,
            "amount": 20,
            "type": "survey_reward",
            "description": "Completed survey",
        }
    ).execute()

    return {"stars": 20, "message": "🎉 20 Virtual Stars Credited!"}


@app.post("/api/spend-stars")
async def spend_stars(request: Request):
    """Spend stars to unlock feature → redirect to Adsterra DL"""
    data = await request.json()
    telegram_id = data.get("telegram_id")
    amount = data.get("amount", 10)
    action = data.get("action", "skip_wait")

    # Check balance
    user = (
        supabase.table("users")
        .select("virtual_stars")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    if len(user.data) == 0 or user.data[0]["virtual_stars"] < amount:
        raise HTTPException(status_code=400, detail="Not enough stars")

    # Deduct stars
    new_stars = user.data[0]["virtual_stars"] - amount
    supabase.table("users").update(
        {"virtual_stars": new_stars}
    ).eq("telegram_id", telegram_id).execute()

    # Log transaction
    supabase.table("star_transactions").insert(
        {
            "user_id": telegram_id,
            "amount": -amount,
            "type": action,
            "description": f"Spent {amount} stars to {action}",
        }
    ).execute()

    # Redirect to Adsterra DL
    dl_url = f"{ADSTERRA_DL_URL}?user_id={telegram_id}&action={action}"
    return RedirectResponse(dl_url)


@app.post("/api/redeem-stars")
async def redeem_stars(request: Request):
    """Redeem 500 Virtual Stars for real Telegram Stars"""
    data = await request.json()
    telegram_id = data.get("telegram_id")

    # Check balance
    user = (
        supabase.table("users")
        .select("virtual_stars")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    if len(user.data) == 0 or user.data[0]["virtual_stars"] < 500:
        raise HTTPException(status_code=400, detail="Need 500 stars to redeem")

    # Deduct stars
    user_data = (
        supabase.table("users")
        .select("virtual_stars", "real_stars_redeemed")
        .eq("telegram_id", telegram_id)
        .execute()
    )
    current_virtual_stars = user_data.data[0]["virtual_stars"]
    current_real_stars_redeemed = user_data.data[0]["real_stars_redeemed"]
    supabase.table("users").update(
        {
            "virtual_stars": current_virtual_stars - 500,
            "real_stars_redeemed": current_real_stars_redeemed + 500,
        }
    ).eq("telegram_id", telegram_id).execute()

    # Create redemption request
    supabase.table("redemptions").insert(
        {"user_id": telegram_id, "amount": 500, "status": "pending"}
    ).execute()

    return {
        "message": "✅ Redemption request received! We'll send 500 REAL Telegram Stars within 24h."
    }
