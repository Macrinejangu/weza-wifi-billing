import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.billing import customer_router
from app.api.billing import router as billing_router
from app.api.health import router as health_router
from app.api.mock_mode import require_mock_mode
from app.api.packages import router as packages_router
from app.api.router import router as router_status_router
from app.api.sessions import router as sessions_router
from app.api.staff import router as staff_router

from app.api.routes.customers import router as customers_router
from app.api.routes.issues import router as connection_issues_router
from app.api.routes.network import router as network_inventory_router
from app.api.routes.payments import router as mpesa_payments_router
from app.api.routes.mpesa_callback import router as mpesa_callback_router

app = FastAPI(title="Weza Wi-Fi Billing API")

# Lets the two React apps (customer portal :5173, operator dashboard :5174) call this API.
FRONTENDS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", FRONTENDS).split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(staff_router)
app.include_router(customers_router)
app.include_router(connection_issues_router)
app.include_router(network_inventory_router)
app.include_router(mpesa_payments_router)
app.include_router(customer_router)
app.include_router(mpesa_callback_router)
app.include_router(router_status_router)
app.include_router(packages_router, prefix="/api")
app.include_router(billing_router, dependencies=[Depends(require_mock_mode)])
app.include_router(sessions_router, dependencies=[Depends(require_mock_mode)])


# Services raise LookupError (not found) or ValueError (rule broken); turn them into HTTP errors.
@app.exception_handler(LookupError)
async def not_found(request: Request, error: LookupError):
    return JSONResponse({"detail": str(error.args[0])}, status_code=404)


@app.exception_handler(ValueError)
async def rule_broken(request: Request, error: ValueError):
    return JSONResponse({"detail": str(error)}, status_code=400)


@app.get("/")
def home():
    return {"message": "Weza Wi-Fi Billing API is running"}
