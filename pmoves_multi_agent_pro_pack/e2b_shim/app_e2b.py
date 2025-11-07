import os, time, typing, base64, json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from e2b_code_interpreter import Sandbox

E2B_API_KEY = os.environ.get("E2B_API_KEY","")
if not E2B_API_KEY:
    print("WARNING: E2B_API_KEY is not set; set it to enable remote execution.")

# E2B SDK reads the key from env automatically

app = FastAPI(title="pmoves E2B sandbox runner", version="1.0.0")

class RunBody(BaseModel):
    code: str
    language: typing.Optional[str] = Field(default="python", description="python|javascript|bash")
    envs: typing.Optional[dict] = None
    timeout: typing.Optional[float] = 120.0
    files: typing.Optional[dict] = Field(default=None, description="path->base64 content")
    keep_alive: bool = Field(default=False, description="keep sandbox alive after run")
    cwd: typing.Optional[str] = None

class ExecBody(BaseModel):
    sandbox_id: str
    code: str
    language: typing.Optional[str] = "python"
    timeout: typing.Optional[float] = 120.0

class StopBody(BaseModel):
    sandbox_id: str

# simple in-memory index of sandboxes
SANDBOXES: dict[str, Sandbox] = {}

def _open_sandbox():
    sb = Sandbox.create()
    SANDBOXES[sb.id] = sb
    return sb

@app.post("/sandbox/run")
def sandbox_run(body: RunBody):
    try:
        sb = _open_sandbox()
        if body.cwd:
            ctx = sb.create_code_context(cwd=body.cwd, language=body.language)
        else:
            ctx = sb.create_code_context(language=body.language)
        if body.files:
            for path, b64 in body.files.items():
                data = base64.b64decode(b64)
                sb.files.write(path, data)
        exec_result = sb.run_code(body.code, language=body.language, envs=body.envs, timeout=body.timeout)
        out = {
            "id": sb.id,
            "stdout": "".join([m.output for m in exec_result.console.stdout]) if getattr(exec_result, "console", None) else "",
            "stderr": "".join([m.output for m in exec_result.console.stderr]) if getattr(exec_result, "console", None) else "",
            "result": getattr(exec_result, "result", None).value if getattr(exec_result, "result", None) else None,
            "kept": body.keep_alive
        }
        if not body.keep_alive:
            try:
                sb.close()
                SANDBOXES.pop(sb.id, None)
            except Exception:
                pass
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sandbox/exec")
def sandbox_exec(body: ExecBody):
    sb = SANDBOXES.get(body.sandbox_id)
    if not sb:
        raise HTTPException(status_code=404, detail="sandbox not found")
    exec_result = sb.run_code(body.code, language=body.language, timeout=body.timeout)
    return {
        "id": sb.id,
        "stdout": "".join([m.output for m in exec_result.console.stdout]) if getattr(exec_result, "console", None) else "",
        "stderr": "".join([m.output for m in exec_result.console.stderr]) if getattr(exec_result, "console", None) else "",
        "result": getattr(exec_result, "result", None).value if getattr(exec_result, "result", None) else None
    }

@app.post("/sandbox/stop")
def sandbox_stop(body: StopBody):
    sb = SANDBOXES.pop(body.sandbox_id, None)
    if sb:
        try: sb.close()
        except Exception: pass
        return {"ok": True}
    return {"ok": False, "error": "not found"}