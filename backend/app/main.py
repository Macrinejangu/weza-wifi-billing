from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.billing import router as billing_router
from app.api.health import router as health_router
from app.api.mock_mode import require_mock_mode
from app.api.packages import router as packages_router
from app.api.router import router as router_status_router
from app.api.sessions import router as sessions_router

app = FastAPI(title="Weza Wi-Fi Billing API")

app.include_router(health_router)
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
