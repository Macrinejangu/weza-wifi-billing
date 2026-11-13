from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.packages import router as packages_router

app = FastAPI(title="Weza WiFi Billing API")

app.include_router(health_router)
app.include_router(packages_router, prefix="/api")
