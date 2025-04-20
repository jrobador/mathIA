from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import session
from app.core.config import settings # Load settings early
import uvicorn
import os

# Create directories for static files if they don't exist
os.makedirs("static/images", exist_ok=True)
os.makedirs("static/audio", exist_ok=True)

app = FastAPI(
    title="Math Tutor Agent API",
    description="API for the AI Math Tutor using LangGraph",
    version="0.1.0",
)

# CORS Middleware
origins = [
    "http://localhost:3000", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for serving generated content
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routers
app.include_router(session.router, prefix="/session", tags=["Session"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Math Tutor Agent API!"}

# --- Main execution ---
if __name__ == "__main__":
    print("Starting Math Tutor Agent API...")
    print(f"API Host configured for: {settings.API_HOST}")
    if settings.API_HOST == 'azure':
        print(f"Using Azure OpenAI Endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
        print(f"Using Deployment: {settings.AZURE_OPENAI_CHAT_DEPLOYMENT}")
    
    # Static file paths
    print(f"Serving static files from: {os.path.abspath('static')}")
    
    
    uvicorn.run(app, host="0.0.0.0", port=8000)