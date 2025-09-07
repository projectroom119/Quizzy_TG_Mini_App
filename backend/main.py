from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
import uvicorn

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

# ✅ FIXED: Use absolute path for templates
import os
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Set in Render env vars

# Simple session storage (for demo — use Redis in prod)
admin_sessions = set()

def require_admin(request: Request):
    session_id = request.cookies.get("admin_session")
    if session_id not in admin_sessions:
        raise HTTPException(status_code=403, detail="Not authorized")

# ✅ FIXED: Remove trailing spaces in CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://quizzy-tg-mini-app-frontend.onrender.com",  # ← NO TRAILING SPACE
        "https://quizzy-tg-mini-app-backend.onrender.com"     # ← NO TRAILING SPACE
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

# ✅ FIXED: Added error handling to all admin routes

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    try:
        return templates.TemplateResponse("admin_login.html", {"request": request})
    except Exception as e:
        print(f"Template error: {e}")
        return HTMLResponse("Template not found - check backend/templates/ folder", status_code=500)

@app.post("/admin/login")
async def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        session_id = str(uuid.uuid4())
        admin_sessions.add(session_id)
        response = RedirectResponse("/admin/dashboard", status_code=303)
        response.set_cookie(key="admin_session", value=session_id)
        return response
    else:
        try:
            return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid password"})
        except Exception as e:
            print(f"Template error: {e}")
            return HTMLResponse("Template not found", status_code=500)

@app.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    """Simple JSON dashboard — no templates, no errors"""
    require_admin(request)
    
    try:
        # Get total users
        users = supabase.table("users").select("id").execute()
        users_count = len(users.data) if users.data else 0
        
        # ✅ FIXED: Use raw SQL to avoid filter syntax issues
        # Count completed surveys (where completed_at IS NOT NULL)
        surveys_result = supabase.rpc(
            "get_completed_surveys_count"
        ).execute()
        
        # If RPC doesn't exist, fallback to direct query
        if not surveys_result.data:
            # Use raw SQL via select()
            surveys_raw = supabase.table("survey_sessions").select("id").execute()
            # Filter in Python (safe, simple)
            completed_surveys = [
                s for s in surveys_raw.data 
                if s.get("completed_at") is not None
            ] if surveys_raw.data else []
            surveys_count = len(completed_surveys)
        else:
            surveys_count = surveys_result.data[0]["count"] if surveys_result.data else 0
        
        # Get pending redemptions
        pending = supabase.table("redemptions").select("id").eq("status", "pending").execute()
        pending_count = len(pending.data) if pending.data else 0
        
        return {
            "status": "success",
            "users_count": users_count,
            "surveys_count": surveys_count,
            "pending_redemptions": pending_count,
            "message": "Admin dashboard data loaded successfully"
        }
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        return {
            "status": "error",
            "message": f"Failed to load dashboard: {str(e)}"
        }

@app.get("/admin/redemptions")
async def admin_redemptions(request: Request):
    """Return pending redemptions as JSON"""
    require_admin(request)
    
    try:
        redemptions = supabase.table("redemptions").select("*").eq("status", "pending").execute()
        return {
            "status": "success",
            "redemptions": redemptions.data if redemptions.data else []
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
@app.get("/admin/logout")
async def admin_logout(request: Request):
    session_id = request.cookies.get("admin_session")
    if session_id in admin_sessions:
        admin_sessions.remove(session_id)
    response = RedirectResponse("/admin/login")
    response.delete_cookie("admin_session")
    return response

@app.get("/health")
async def health_check():
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=False)