from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.agents.analysis_agent import AnalysisAgent, AnalysisAgentError
from app.agents.video_insight_agent import VideoInsightAgent
from app.contracts import AnalyzeVideoRequest, VideoAnalysisResponse
from app.contracts_agent import DemoInsightsPayload, VideoInsightRequest, VideoInsightResponse
from app.settings import settings


app = FastAPI(title=settings.app_name, version=settings.app_version)

WEB_DIR = Path(__file__).resolve().parent / "web"
_live_request_count = 0


def _require_live_access_token(token: Optional[str]) -> None:
    if not settings.live_mode_enabled:
        raise HTTPException(status_code=403, detail="Live mode is disabled.")

    if not token:
        raise HTTPException(status_code=401, detail="Missing access token.")

    if token != settings.app_access_token:
        raise HTTPException(status_code=403, detail="Invalid access token.")


def _check_live_request_limit() -> None:
    global _live_request_count

    if _live_request_count >= settings.live_request_limit:
        raise HTTPException(
            status_code=429,
            detail="Live request limit reached for this app session.",
        )


def _load_demo_payload() -> dict:
    demo_path = settings.demo_file_path
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="Demo payload file not found.")

    try:
        return json.loads(demo_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load demo payload: {exc}") from exc


def _load_demo_insights() -> dict:
    demo_path = Path("data/demo/demo_video_insights.json")
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="Demo insights file not found.")

    try:
        return json.loads(demo_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load demo insights: {exc}") from exc


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/demo", response_model=VideoAnalysisResponse)
def demo() -> VideoAnalysisResponse:
    if not settings.demo_mode_enabled:
        raise HTTPException(status_code=403, detail="Demo mode is disabled.")

    payload = _load_demo_payload()
    return VideoAnalysisResponse.model_validate(payload)


@app.get("/demo/insights", response_model=DemoInsightsPayload)
def demo_insights() -> DemoInsightsPayload:
    if not settings.demo_mode_enabled:
        raise HTTPException(status_code=403, detail="Demo mode is disabled.")

    payload = _load_demo_insights()
    return DemoInsightsPayload.model_validate(payload)


@app.post("/unlock")
def unlock(x_access_token: Optional[str] = Header(default=None)) -> dict:
    _require_live_access_token(x_access_token)

    remaining = max(settings.live_request_limit - _live_request_count, 0)

    return {
        "live_mode_enabled": True,
        "remaining_requests": remaining,
    }


@app.post("/analyze", response_model=VideoAnalysisResponse)
def analyze(
    request: AnalyzeVideoRequest,
    x_access_token: Optional[str] = Header(default=None),
) -> VideoAnalysisResponse:
    global _live_request_count

    _require_live_access_token(x_access_token)
    _check_live_request_limit()

    try:
        agent = AnalysisAgent()
        result = agent.run(request)
    except AnalysisAgentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected analyze failure: {exc}") from exc

    _live_request_count += 1
    return result


@app.post("/agent/video-insight", response_model=VideoInsightResponse)
def agent_video_insight(
    request: VideoInsightRequest,
    x_access_token: Optional[str] = Header(default=None),
) -> VideoInsightResponse:
    global _live_request_count

    _require_live_access_token(x_access_token)
    _check_live_request_limit()

    try:
        agent = VideoInsightAgent()
        result = agent.run(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected video insight failure: {exc}") from exc

    _live_request_count += 1
    return result


@app.get("/")
def root():
    index_path = WEB_DIR / "app.html"
    if not index_path.exists():
        return HTMLResponse(
            content=(
                "<h1>YouTube EmotionScope API</h1>"
                "<p>Frontend file app/web/app.html not found yet.</p>"
            )
        )
    return FileResponse(index_path, media_type="text/html")


@app.get("/app.js")
def app_js():
    js_path = WEB_DIR / "app.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="app.js not found.")
    return FileResponse(js_path, media_type="application/javascript")


@app.get("/styles.css")
def styles_css():
    css_path = WEB_DIR / "styles.css"
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="styles.css not found.")
    return FileResponse(css_path, media_type="text/css")


@app.exception_handler(404)
def not_found_handler(_, __):
    return JSONResponse(status_code=404, content={"detail": "Not found"})