import logging, sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import validate
    from app.services.scheduler import start_scheduler
    validate()
    start_scheduler()
    print("✅ KrishiMitra started!")
    yield
    print("KrishiMitra stopped.")

app = FastAPI(title="KrishiMitra", version="3.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from app.routers import webhook, admin
app.include_router(webhook.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"status": "running", "app": "KrishiMitra 🌾", "version": "3.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ping")
async def ping():
    return "pong"
