from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routes.feedbackRoutes import feedback_bp
from Routes.lbscore360Routes import lbscore360_bp
from Routes.FeedbackSummaryRoute import feedback_summary_bp
from Routes.userRoute import user_bp
from Routes.loginRoute import login_bp
from Routes.feedbackDraftRoute import feedback_draft_router
from Routes.categoryConfigRoutes import category_config_bp
from Utils.middleware import AuthMiddleware

from Utils.db import connect_to_db
from Utils.seeder import seed_category_configs
from Utils.exceptionHandler import exception_handler, default_exception_handler
from Utils.apiException import ApiException

import uvicorn
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from mongoengine.connection import get_db

load_dotenv()


@asynccontextmanager
async def startup_db(app:FastAPI):
    connect_to_db()
    seed_category_configs()
    yield
    print("Application shutdown")

app = FastAPI(lifespan = startup_db)

app.add_middleware(AuthMiddleware)

app.add_exception_handler(ApiException, exception_handler)
app.add_exception_handler(Exception, default_exception_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

app.include_router(feedback_bp)
app.include_router(lbscore360_bp)
app.include_router(feedback_summary_bp)
app.include_router(user_bp)
app.include_router(login_bp)
app.include_router(feedback_draft_router)
app.include_router(category_config_bp)




@app.get("/health")
def health_check():
    try:
        db = get_db()
        db.command("ping")
        status_code = 200
        return {"status": "healthy", "backend": "connected"}, status_code

    except Exception as e:
        db_status = f"error: {str(e)}"
        status_code = 500
        return {"status": "unhealthy", "backend": db_status}, status_code

    

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7204))  
    print(f"Running on port: {port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)