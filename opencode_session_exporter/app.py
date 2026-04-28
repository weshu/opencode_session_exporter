import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from exporter import (
    check_opencode_available,
    list_sessions,
    export_session,
    convert_to_markdown,
    save_markdown,
    SessionInfo,
)


app = FastAPI(title="OpenCode Session Exporter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

import inspect
_CURRENT_FILE = inspect.getfile(inspect.currentframe()) if '__file__' not in dir() else __file__
if _CURRENT_FILE:
    _APP_DIR = os.path.dirname(os.path.abspath(_CURRENT_FILE))
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
STATIC_DIR = os.path.join(_APP_DIR, "static")
OUTPUT_DIR = os.path.join(_APP_DIR, "export")
APP_DIR = _APP_DIR


class ExportRequest(BaseModel):
    session_ids: List[str]


@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/api/sessions")
async def get_sessions(project_path: str = None):
    if not check_opencode_available():
        raise HTTPException(status_code=500, detail="opencode command not found")

    sessions = list_sessions(project_path)
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "updated": s.updated,
                "directory": s.directory,
            }
            for s in sessions
        ]
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, project_path: str = None):
    if not check_opencode_available():
        raise HTTPException(status_code=500, detail="opencode command not found")

    data = export_session(session_id, project_path)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")

    return data


@app.post("/api/export")
async def export_sessions(request: ExportRequest, project_path: str = None):
    if not check_opencode_available():
        raise HTTPException(status_code=500, detail="opencode command not found")

    exported = []
    failed = []

    for session_id in request.session_ids:
        data = export_session(session_id, project_path)
        if not data:
            failed.append(session_id)
            continue

        try:
            title = data.get("title", "Untitled")
            updated = data.get("updated", "")
            content = convert_to_markdown(data)
            filename = save_markdown(content, title, updated, OUTPUT_DIR)
            exported.append(filename)
        except Exception as e:
            print(f"Export error for {session_id}: {e}")
            failed.append(session_id)

    return {
        "exported": exported,
        "failed": failed,
    }


@app.get("/api/directories")
async def list_directories(path: str = None):
    if not path:
        return {"directories": [], "exists": False}
    
    if not os.path.exists(path):
        return {"directories": [], "exists": False}
    
    if not os.path.isdir(path):
        return {"directories": [], "exists": False}
    
    try:
        entries = os.listdir(path)
        directories = [
            entry for entry in entries 
            if os.path.isdir(os.path.join(path, entry))
        ]
        directories.sort()
        return {"directories": directories, "exists": True}
    except PermissionError:
        return {"directories": [], "exists": True}


if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)