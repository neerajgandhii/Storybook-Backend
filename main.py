from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent
env_file = backend_dir / ".env"
load_dotenv(dotenv_path=env_file)

# Add backend directory to path so routes can be imported
sys.path.insert(0, str(backend_dir))

# Import routes
from routes.storybook import router as storybook_router

# Create FastAPI app
app = FastAPI(
    title="LexiAssist Backend",
    description="Backend API for LexiAssist dyslexia screening app",
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(storybook_router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LexiAssist Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
