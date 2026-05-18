import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import get_settings
from models.database import init_db
from routes.api import router
from tasks.market_open import market_open_task
from tasks.real_time_tracker import real_time_tracker_task
from tasks.market_close import market_close_task

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("nepse_bot.log"),
    ],
)
logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler(timezone="Asia/Kathmandu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting NEPSE Trading Bot...")
    init_db()
    logger.info("Database initialized")

    # Schedule tasks (Nepal Time)
    # Market open: 11:00 AM Mon-Fri
    scheduler.add_job(
        market_open_task, "cron",
        day_of_week="mon-fri", hour=11, minute=0,
        id="market_open", replace_existing=True,
    )

    # Real-time tracker: Every 1 minute during market hours (11:00-15:00)
    scheduler.add_job(
        real_time_tracker_task, "cron",
        day_of_week="mon-fri", hour="11-14", minute="*",
        id="real_time_tracker", replace_existing=True,
    )

    # Final data sync: 3:01 PM Mon-Fri (one last check after market close)
    scheduler.add_job(
        real_time_tracker_task, "cron",
        day_of_week="mon-fri", hour=15, minute=1,
        id="final_sync", replace_existing=True,
    )

    # Market close: 3:15 PM Mon-Fri
    scheduler.add_job(
        market_close_task, "cron",
        day_of_week="mon-fri", hour=15, minute=15,
        id="market_close", replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with NEPSE market hours")

    yield

    # Shutdown
    scheduler.shutdown()
    from services.data_fetcher import data_fetcher
    await data_fetcher.close()
    logger.info("NEPSE Trading Bot stopped")


app = FastAPI(
    title="NEPSE Trading Bot",
    description="Professional Swing Trading Bot for Nepal Stock Exchange",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "NEPSE Trading Bot",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    from utils.validators import is_market_open, is_trading_day
    return {
        "status": "healthy",
        "market_open": is_market_open(),
        "trading_day": is_trading_day(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
