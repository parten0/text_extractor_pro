from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routes import router


# Create FastAPI app
app = FastAPI(
    title="Doc Extractor Pro API",
    description="API for document text extraction and processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount static files (frontend)
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    print("🚀 Doc Extractor Pro API is starting...")
    print("📁 Static files directory:", static_dir)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    print("👋 Doc Extractor Pro API is shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
