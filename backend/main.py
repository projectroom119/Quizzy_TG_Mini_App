from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
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
    allow_origins=[
        "https://quizzy-tg-mini-app-frontend.onrender.com",  # ← Fixed: no trailing space
        "https://quizzy-tg-mini-app-backend.onrender.com"     # ← Fixed: no trailing space
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ROUTES ===

@app.get("/api/user")
async def get_user(telegram_id: int):
    """Get or create user"""
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
    """Log answer to database — do NOT redirect to Adsterra (frontend handles it)"""
    data = await request.json()
    telegram_id = data.get("telegram_id")
    step = data.get("step")
    answer = data.get("answer")
    
    try:
        # Get current session
        current = supabase.table("survey_sessions").select("answers").eq("user_id", telegram_id).execute()
        if not current.data:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        
        answers = current.data[0]["answers"] if current.data else {}
        answers[f"q{step}"] = answer
        
        # Update session
        supabase.table("survey_sessions").update({
            "current_step": step + 1,
            "answers": answers
        }).eq("user_id", telegram_id).execute()
        
        return {"success": True, "message": "Answer logged"}
    
    except Exception as e:
        print(f"Error logging answer: {e}")
        return JSONResponse({"error": "Failed to log answer"}, status_code=500)

@app.post("/api/complete-survey")
async def complete_survey(request: Request):
    """Mark survey complete → grant stars later"""
    data = await request.json()
    telegram_id = data.get("telegram_id")
    session_id = data.get("session_id")
    
    # Mark survey complete
    supabase.table("survey_sessions").update({
        "completed_at": datetime.utcnow().isoformat()
    }).eq("id", session_id).execute()
    
    # Increment surveys_completed
    user = supabase.table("users").select("surveys_completed").eq("telegram_id", telegram_id).execute()
    current_completed = user.data[0]["surveys_completed"] if user.data else 0
    supabase.table("users").update({
        "surveys_completed": current_completed + 1
    }).eq("telegram_id", telegram_id).execute()
    
    return {"message": "Survey completed."}

@app.get("/api/claim-reward")
async def claim_reward(telegram_id: int):
    """Claim 20 Virtual Stars"""
    # Fetch current stars
    user = supabase.table("users").select("virtual_stars").eq("telegram_id", telegram_id).execute()
    current_stars = user.data[0]["virtual_stars"] if user.data else 0
    
    # Update stars
    supabase.table("users").update({
        "virtual_stars": current_stars + 20
    }).eq("telegram_id", telegram_id).execute()
    
    # Log transaction
    supabase.table("star_transactions").insert({
        "user_id": telegram_id,
        "amount": 20,
        "type": "survey_reward",
        "description": "Completed survey"
    }).execute()
    
    return {"stars": 20, "message": "🎉 20 Virtual Stars Credited!"}

@app.post("/api/spend-stars")
async def spend_stars(request: Request):
    """Spend stars to unlock feature"""
    data = await request.json()
    telegram_id = data.get("telegram_id")
    amount = data.get("amount", 10)
    action = data.get("action", "skip_wait")
    
    # Check balance
    user = supabase.table("users").select("virtual_stars").eq("telegram_id", telegram_id).execute()
    if len(user.data) == 0 or user.data[0]["virtual_stars"] < amount:
        raise HTTPException(status_code=400, detail="Not enough stars")
    
    # Deduct stars
    new_stars = user.data[0]["virtual_stars"] - amount
    supabase.table("users").update({
        "virtual_stars": new_stars
    }).eq("telegram_id", telegram_id).execute()
    
    # Log transaction
    supabase.table("star_transactions").insert({
        "user_id": telegram_id,
        "amount": -amount,
        "type": action,
        "description": f"Spent {amount} stars to {action}"
    }).execute()
    
    return {"success": True, "message": f"Spent {amount} stars"}

@app.post("/api/redeem-stars")
async def redeem_stars(request: Request):
    """Redeem 500 Virtual Stars for real Telegram Stars"""
    data = await request.json()
    telegram_id = data.get("telegram_id")
    
    # Check balance
    user = supabase.table("users").select("virtual_stars").eq("telegram_id", telegram_id).execute()
    if len(user.data) == 0 or user.data[0]["virtual_stars"] < 500:
        raise HTTPException(status_code=400, detail="Need 500 stars to redeem")
    
    # Deduct stars
    current_virtual_stars = user.data[0]["virtual_stars"]
    current_real_stars_redeemed = user.data[0].get("real_stars_redeemed", 0)
    supabase.table("users").update({
        "virtual_stars": current_virtual_stars - 500,
        "real_stars_redeemed": current_real_stars_redeemed + 500
    }).eq("telegram_id", telegram_id).execute()
    
    # Create redemption request
    supabase.table("redemptions").insert({
        "user_id": telegram_id,
        "amount": 500,
        "status": "pending"
    }).execute()
    
    return {"message": "✅ Redemption request received! We'll send 500 REAL Telegram Stars within 24h."}