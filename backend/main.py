from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
if not url or not key:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase: Client = create_client(url, key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://quizzy-tg-mini-app-frontend.onrender.com",
        "https://quizzy-tg-mini-app-backend.onrender.com",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ROUTES ===

@app.get("/api/user")
async def get_user(telegram_id: int):
    user = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    if len(user.data) == 0:
        new_user = {
            "telegram_id": telegram_id,
            "first_name": "Anonymous",
            "virtual_stars": 0,
            "real_stars_redeemed": 0,
            "surveys_completed": 0,
            "first_survey_completed": False,
            "referred_by": None,
            "redeemed_this_week": 0,
            "last_redeem_reset": datetime.utcnow().date().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
        }
        supabase.table("users").insert(new_user).execute()
        return new_user
    else:
        supabase.table("users").update({"last_active": datetime.utcnow().isoformat()}).eq("telegram_id", telegram_id).execute()
        
        # Count referred friends
        referred = supabase.table("users").select("id").eq("referred_by", telegram_id).execute()
        user.data[0]["friends_referred"] = len(referred.data) if referred.data else 0
        
        return user.data[0]

@app.post("/api/start-survey")
async def start_survey(request: Request):
    data = await request.json()
    telegram_id = data.get("telegram_id")
    
    session = {
        "user_id": telegram_id,
        "started_at": datetime.utcnow().isoformat(),
        "current_step": 1,
        "answers": {},
    }
    result = supabase.table("survey_sessions").insert(session).execute()
    return {"session_id": result.data[0]["id"], "step": 1}

@app.post("/api/submit-answer")
async def submit_answer(request: Request):
    data = await request.json()
    telegram_id = data.get("telegram_id")
    step = data.get("step")
    answer = data.get("answer")
    
    try:
        current = supabase.table("survey_sessions").select("answers").eq("user_id", telegram_id).execute()
        if not current.data:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        answers = current.data[0]["answers"] if current.data else {}
        answers[f"q{step}"] = answer
        
        supabase.table("survey_sessions").update({
            "current_step": step + 1,
            "answers": answers
        }).eq("user_id", telegram_id).execute()
        
        return {"success": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/complete-survey")
async def complete_survey(request: Request):
    data = await request.json()
    telegram_id = data.get("telegram_id")
    session_id = data.get("session_id")
    
    supabase.table("survey_sessions").update({
        "completed_at": datetime.utcnow().isoformat()
    }).eq("id", session_id).execute()
    
    user = supabase.table("users").select("surveys_completed, first_survey_completed").eq("telegram_id", telegram_id).execute()
    current_completed = user.data[0]["surveys_completed"] if user.data else 0
    first_completed = user.data[0].get("first_survey_completed", False)
    
    update_data = {"surveys_completed": current_completed + 1}
    if not first_completed:
        update_data["first_survey_completed"] = True
    
    supabase.table("users").update(update_data).eq("telegram_id", telegram_id).execute()
    
    return {"message": "Survey completed"}

@app.get("/api/claim-reward")
async def claim_reward(telegram_id: int):
    user = supabase.table("users").select("virtual_stars, first_survey_completed").eq("telegram_id", telegram_id).execute()
    current_stars = user.data[0]["virtual_stars"] if user.data else 0
    first_completed = user.data[0].get("first_survey_completed", False)
    
    if first_completed:
        reward = 20  # Regular survey
    else:
        reward = 50  # First survey
    
    new_stars = current_stars + reward
    supabase.table("users").update({
        "virtual_stars": new_stars,
        "first_survey_completed": True
    }).eq("telegram_id", telegram_id).execute()
    
    supabase.table("star_transactions").insert({
        "user_id": telegram_id,
        "amount": reward,
        "type": "survey_reward",
        "description": "Completed survey"
    }).execute()
    
    return {"stars": reward, "message": f"🎉 {reward} Virtual Stars Credited!"}

@app.get("/api/claim-channel-reward")
async def claim_channel_reward(telegram_id: int):
    user = supabase.table("users").select("virtual_stars").eq("telegram_id", telegram_id).execute()
    current_stars = user.data[0]["virtual_stars"] if user.data else 0
    
    new_stars = current_stars + 10
    supabase.table("users").update({
        "virtual_stars": new_stars
    }).eq("telegram_id", telegram_id).execute()
    
    supabase.table("star_transactions").insert({
        "user_id": telegram_id,
        "amount": 10,
        "type": "channel_reward",
        "description": "Joined channel"
    }).execute()
    
    return {"stars": 10, "message": "🎉 10 Stars Credited!"}

@app.get("/api/survey-sessions")
async def get_survey_sessions(telegram_id: int):
    sessions = supabase.table("survey_sessions").select("*").eq("user_id", telegram_id).execute()
    return sessions.data if sessions.data else []

@app.post("/api/redeem-stars")
async def redeem_stars(request: Request):
    data = await request.json()
    telegram_id = data.get("telegram_id")
    payment_name = data.get("payment_name")
    payment_email = data.get("payment_email")
    
    user = supabase.table("users").select("virtual_stars, redeemed_this_week, last_redeem_reset").eq("telegram_id", telegram_id).execute()
    if not user.data:
        raise HTTPException(status_code=400, detail="User not found")
    
    current_stars = user.data[0]["virtual_stars"]
    redeemed_this_week = user.data[0]["redeemed_this_week"]
    last_reset = user.data[0]["last_redeem_reset"]
    
    # Reset weekly counter if new week
    today = datetime.utcnow().date()
    if today > last_reset + timedelta(days=7):
        supabase.table("users").update({
            "redeemed_this_week": 0,
            "last_redeem_reset": today.isoformat()
        }).eq("telegram_id", telegram_id).execute()
        redeemed_this_week = 0
    
    # Check limits
    if current_stars < 2000:
        raise HTTPException(status_code=400, detail="Need 2000 Stars to redeem")
    if redeemed_this_week >= 2000:
        raise HTTPException(status_code=400, detail="Max 2000 Stars redeemable per week")
    
    # Process redemption
    supabase.table("users").update({
        "virtual_stars": current_stars - 2000,
        "redeemed_this_week": redeemed_this_week + 2000
    }).eq("telegram_id", telegram_id).execute()
    
    supabase.table("redemptions").insert({
        "user_id": telegram_id,
        "amount": 2000,
        "status": "pending",
        "payment_name": payment_name,
        "payment_email": payment_email
    }).execute()
    
    return {"success": True, "message": "✅ Redemption request received! Processed within 24h."}


@app.post("/api/spend-stars")
async def spend_stars(request: Request):
    data = await request.json()
    telegram_id = data.get("telegram_id")
    amount = data.get("amount", 10)
    action = data.get("action", "skip_wait")
    
    # If action is "watch_ad" → don't deduct stars → just log
    if action == "watch_ad":
        # Log transaction
        supabase.table("star_transactions").insert({
            "user_id": telegram_id,
            "amount": -amount,  # Negative because it's a "spend" action
            "type": "watch_ad",
            "description": f"Watched ad → earned {abs(amount)} stars"
        }).execute()
        return {"success": True, "message": "Ad watched"}
    
    # ... rest of your existing spend-stars logic ...

@app.get("/health")
async def health_check():
    return {"status": "OK"}