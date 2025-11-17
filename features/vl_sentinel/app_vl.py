import os, io, base64, requests
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

PROVIDER = os.environ.get("VL_PROVIDER", "ollama").lower()
DEFAULT_MODELS = {
    "ollama": "qwen2.5-vl:14b",
    "openai": "gpt-4o-mini"
}
_env_model = os.environ.get("VL_MODEL")
MODEL = _env_model or DEFAULT_MODELS.get(PROVIDER, "qwen2.5-vl:14b")
OLLAMA = os.environ.get("OLLAMA_BASE_URL","http://host.docker.internal:11434")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY","")

app = FastAPI(title="pmoves VL sentinel", version="1.0.0")

class ImageInput(BaseModel):
    # either url or base64; if both present, base64 wins
    url: Optional[str] = None
    b64: Optional[str] = None

class GuideRequest(BaseModel):
    task: str
    images: Optional[List[ImageInput]] = None
    logs: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None

def fetch_b64(img: ImageInput):
    if img.b64: return img.b64
    if img.url:
        r = requests.get(img.url, timeout=15)
        r.raise_for_status()
        return base64.b64encode(r.content).decode("utf-8")
    return None

def ask_ollama(prompt: str, images_b64: List[str]):
    payload = {"model": MODEL, "prompt": prompt, "images": images_b64, "stream": False}
    r = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=120)
    if not r.ok:
        raise HTTPException(status_code=500, detail=f"Ollama error: {r.text[-500:]}")
    data = r.json()
    return data.get("response","")

def ask_openai(prompt: str, images_b64: List[str]):
    if not OPENAI_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not set")
    headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
    messages = [{"role":"user","content":[{"type":"text","text": prompt}]}]
    for b in images_b64:
        messages[0]["content"].append({"type":"image_url","image_url":{"url": f"data:image/png;base64,{b}"}})
    # OpenAI-compatible chat completions
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      json={"model": MODEL, "messages": messages},
                      headers=headers, timeout=120)
    if not r.ok:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {r.text[-500:]}")
    data = r.json()
    return data["choices"][0]["message"]["content"]

@app.post("/vl/guide")
def vl_guide(body: GuideRequest):
    img_b64s = [fetch_b64(i) for i in (body.images or []) if fetch_b64(i)]
    sys = "You are a vision-language monitoring agent. Given task context, images, and logs, diagnose problems and propose next actions. Answer in bullet points with short steps."
    prompt = f"{sys}\nTask: {body.task}\nLogs: {body.logs or []}\nMetrics: {body.metrics or {}}"
    if PROVIDER == "ollama":
        answer = ask_ollama(prompt, img_b64s)
    else:
        answer = ask_openai(prompt, img_b64s)
    return {"ok": True, "guidance": answer}

@app.get("/health")
def health_check():
    """Health check endpoint for docker-compose health check"""
    return {"status": "healthy", "provider": PROVIDER, "model": MODEL}