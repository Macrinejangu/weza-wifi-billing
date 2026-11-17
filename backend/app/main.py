from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.router import router as router_status_router

app = FastAPI(title="Weza Wi-Fi Billing API")

app.include_router(health_router)
app.include_router(router_status_router)
