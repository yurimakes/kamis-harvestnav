from datetime import date, datetime
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .schemas import Scenario
from .services.portal import PortalClient, configured, KST
from .services.simulation import Infeasible, compare, evaluate, public_result
from .services import ai

PROJECT = Path(__file__).resolve().parents[2]
app = FastAPI(title="HarvestNav", version="0.1.0")
kamis = PortalClient()


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Do not echo arbitrary request values into errors or log bodies.
    return JSONResponse(status_code=422, content={"detail": "입력 범위·배분비율·날짜·필수 항목을 확인하세요.",
                                                "fields": [".".join(map(str, e["loc"])) for e in exc.errors()]})


@app.get("/api/health")
def health():
    return {"service": "HarvestNav", "version": "0.1.0", "kamis_configured": configured(),
            "prediction_model": "not_loaded", "ai_configured": ai.configured()}


@app.post("/api/ai/ask")
async def ai_ask(request: Request):
    return await ai.ask(request)


@app.get("/api/examples/scenario")
def example():
    return json.loads((PROJECT / "examples" / "cabbage.synthetic.json").read_text(encoding="utf-8"))


@app.post("/api/simulation")
def simulation(scenario: Scenario):
    try:
        return public_result(evaluate(scenario))
    except Infeasible as error:
        raise HTTPException(422, str(error)) from None


@app.post("/api/strategies/compare")
def strategies(scenario: Scenario):
    try:
        return compare(scenario)
    except Infeasible as error:
        raise HTTPException(422, str(error)) from None


@app.get("/api/kamis/prices")
async def prices(start: date, end: date, region: str = Query("1101", pattern=r"^\d{4}$"),
                 kind: str = Query("03", pattern=r"^\d{2}$"), rank: str = Query("04", pattern=r"^\d{2}$")):
    if end < start or (end - start).days > 31 or end > datetime.now(KST).date():
        raise HTTPException(422, "조회 기간은 오늘까지 최대 31일 간격이어야 합니다.")
    return await kamis.prices(start, end, region, kind, rank)


@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


if (PROJECT / "frontend" / "dist").is_dir():
    app.mount("/", StaticFiles(directory=PROJECT / "frontend" / "dist", html=True), name="frontend")
