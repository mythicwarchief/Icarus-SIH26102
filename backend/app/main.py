from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router


app = FastAPI(
    title="MPLADS Anomaly Detection API",
    description="Backend API for the MPLADS anomaly detection system.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    router,
    prefix="/api",
    tags=["MPLADS Anomaly Detection"],
)


@app.get("/")
def root():
    return {
        "message": "Welcome to the MPLADS Anomaly Detection API",
        "api_base": "/api",
        "docs": "/docs",
    }