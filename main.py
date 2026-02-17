from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import os

from engine_v2 import AuditEngine

# ================= APP =================
app = FastAPI(title="Enterprise Audit Intelligence")

# Enable CORS (for frontend calls)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global ML Engine
engine = AuditEngine()


# ================= MODELS =================
class ChatRequest(BaseModel):
    message: str


# ================= API: STATS =================
@app.get("/api/stats")
async def get_stats():
    """
    Returns dashboard statistics for frontend.
    """
    try:
        return engine.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= API: UPLOAD PLAN =================
@app.post("/api/upload-plan")
async def upload_plan(file: UploadFile = File(...)):
    try:
        content = await file.read()
        count = engine.process_audit_plan(content)

        return {
            "status": "success",
            "message": f"Loaded {count} processes from Audit Plan."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= API: UPLOAD FINDINGS =================
@app.post("/api/upload-findings")
async def upload_findings(
    files: List[UploadFile] = File(...),
    append: bool = Form(False)
):
    try:
        files_data = []

        for file in files:
            content = await file.read()
            files_data.append((file.filename, content))

        count = engine.process_findings(files_data, append=append)

        # Required ML processing sequence
        engine.calculate_scores()
        engine.perform_deep_analysis()

        stats = engine.get_stats()

        return {
            "status": "success",
            "message": f"Processed {count} findings.",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= API: EXPORT EXCEL =================
@app.get("/api/export")
async def export_report():
    try:
        excel_file = engine.export_excel()

        if not excel_file:
            raise HTTPException(status_code=400, detail="No data to export.")

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Enterprise_Audit_Report.xlsx"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= API: CHATBOT =================
@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        response = engine.chat_query(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================= FRONTEND SERVING =================

# Serve CSS & JS
app.mount("/static", StaticFiles(directory="."), name="static")


# Root → index.html dashboard
@app.get("/", response_class=HTMLResponse)
def root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>index.html not found. Upload frontend files.</h2>"


# ================= SERVER START =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
