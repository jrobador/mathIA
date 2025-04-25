from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import os
from api import http_routes, ws_routes
from config import API_HOST, API_PORT, DEBUG, ALLOWED_ORIGINS
from agents.learning_agent import AdaptiveLearningAgent

# Ensure that static file directories exist
os.makedirs("static/images", exist_ok=True)
os.makedirs("static/audio", exist_ok=True)

app = FastAPI(
    title="Adaptive Learning Agent",
    description="API for an adaptive learning agent", 
    version="1.0.0"
)

# Configure CORS to allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create a global instance of the agent
learning_agent = AdaptiveLearningAgent()

# Configure the app to use the agent instance
app.state.learning_agent = learning_agent

# Include routers
app.include_router(http_routes.router)
app.include_router(ws_routes.router)  

@app.get("/")
async def root():
    """
    Root endpoint to verify the server is running
    """
    return {
        "name": "Math Journey API",
        "version": "1.0.0",
        "status": "online",
        "framework": "LangGraph" 
    }

# Background task to clean up inactive sessions
@app.on_event("startup")
async def startup_event():
    """
    Start background tasks when the application starts
    """
    prompts_dir = os.path.join(os.getcwd(), "prompts")
    print(f"Checking for prompts directory: {prompts_dir}")
    if os.path.exists(prompts_dir):
        prompts_files = [f for f in os.listdir(prompts_dir) if f.endswith('.prompty')]
        print(f"Found {len(prompts_files)} prompty files: {prompts_files}")

    from config import OPENAI_AVAILABLE, DALLE_AVAILABLE, SPEECH_AVAILABLE
    print(f"Starting API with services - OpenAI: {OPENAI_AVAILABLE}, DALL-E: {DALLE_AVAILABLE}, Speech: {SPEECH_AVAILABLE}")

    asyncio.create_task(cleanup_sessions_task(app)) 

async def cleanup_sessions_task(app_instance: FastAPI): 
    """
    Periodic task to clean up inactive sessions
    """
    while True:
        # Clean up sessions every 15 minutes
        await asyncio.sleep(15 * 60)  # Use a variable from config?

        try:
            # Access agent via the passed app instance's state
            agent: AdaptiveLearningAgent = app_instance.state.learning_agent
            cleaned = agent.cleanup_inactive_sessions()
            if cleaned > 0:
                print(f"Scheduled cleanup: {cleaned} inactive sessions removed")
            else:
                print("Scheduled cleanup: No inactive sessions found.")
        except AttributeError:
             print("Error during session cleanup: Could not access the agent in app.state.")
        except Exception as e:
            print(f"Error during session cleanup: {e}")

if __name__ == "__main__":
    """
    Entry point to run the application directly
    """
    uvicorn.run(
        "main:app",  
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG,
    )