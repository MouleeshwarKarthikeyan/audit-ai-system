from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import os

from engine_v2 import AuditEngine


app = FastAPI(title="Enterprise Audit Intelligence")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Engine Instance
engine = AuditEngine()


class ChatRequest(BaseModel):
    message: str


# ================= UPLOAD AUDIT PLAN =================
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


# ================= UPLOAD FINDINGS =================
@app.post("/api/upload-findings")
async def upload_findings(files: List[UploadFile] = File(...), append: bool = Form(False)):
    try:
        files_data = []

        for file in files:
            content = await file.read()
            files_data.append((file.filename, content))

        count = engine.process_findings(files_data, append=append)

        # Required processing sequence
        engine.calculate_scores()
        engine.perform_deep_analysis()

        stats = engine.get_stats()

        return {
            "status": "success",
            "message": f"Processed {count} findings.",
            "stats": stats
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ================= EXPORT REPORT =================
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


# ================= CHAT =================
@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = engine.chat_query(request.message)
    return {"response": response}


# ================= SERVE FRONTEND =================
static_dir = os.path.join(os.path.dirname(__file__), "static")

if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


# ================= RUN SERVER (RENDER SAFE) =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
