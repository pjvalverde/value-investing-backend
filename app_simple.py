import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(title="Value Investing API", description="Simplified API for Railway testing")

# CORS configuration
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Value Investing API - Simplified Version",
        "status": "ok",
        "version": "1.0.1",
        "update": "Latest deployment"
    }

# Health check endpoint
@app.get("/test")
def test():
    return {
        "status": "ok",
        "message": "API working correctly",
        "version": "1.0.1"
    }

# API test endpoint
@app.get("/api/test")
def api_test():
    return {
        "status": "ok",
        "data": {
            "app": "Value Investing API",
            "environment": os.environ.get("ENVIRONMENT", "production"),
            "deployment": "Latest version with updated configuration"
        }
    }

# Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run("app_simple:app", host="0.0.0.0", port=port, log_level="info") 