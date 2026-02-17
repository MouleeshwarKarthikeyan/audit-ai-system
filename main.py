from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import os

from engine_v2 import AuditEngine
import inspect
import engine_v2 as engine # Renamed for verification
print(f"DEBUG: Engine loaded from: {engine.__file__}")
print(f"DEBUG: process_findings signature: {inspect.signature(AuditEngine.process_findings)}")


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

@app.post("/api/upload-plan")
async def upload_plan(file: UploadFile = File(...)):
    try:
        content = await file.read()
        count = engine.process_audit_plan(content)
        return {"status": "success", "message": f"Loaded {count} processes from Audit Plan."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-findings")
async def upload_findings(files: List[UploadFile] = File(...), append: bool = Form(False)):
    try:
        print(f"DEBUG: upload-findings called with {len(files)} files. Append={append}")
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append((file.filename, content))
            
        count = engine.process_findings(files_data, append=append)
        print(f"DEBUG: Processed {count} findings. Calculating scores...")
        
        # EXACT SEQUENCE
        engine.calculate_scores()
        engine.perform_deep_analysis() # Keep this as it's valuable
        
        stats = engine.get_stats()
        print("DEBUG: Scores calculated. Returning stats keys:", stats.keys())
        return {"status": "success", "message": f"Processed {count} findings.", "stats": stats}
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        with open("server_error.log", "w") as f:
            f.write(traceback.format_exc())
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export")
async def export_report():
    try:
        excel_file = engine.export_excel()
        if not excel_file:
            raise HTTPException(status_code=400, detail="No data to export.")
            
        return StreamingResponse(
            excel_file, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Enterprise_Audit_Report.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = engine.chat_query(request.message)
    return {"response": response}

# Serve Static Files (Frontend)
# Ensure the directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    try:
        from pyngrok import ngrok
        
        # Open a HTTP tunnel on the default port 8000
        public_url = ngrok.connect(8000).public_url
        print(f"\n🚀 AUDIT APP IS LIVE ON THE INTERNET!")
        print(f"👉 CLICK THIS LINK TO OPEN: {public_url}")
        print(f"----------------------------------------------------------------")
    except Exception as e:
        print(f"Could not start ngrok tunnel: {e}")
        
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"👉 Local Access: http://localhost:8000")
        print(f"👉 LAN Access: http://{local_ip}:8000")
    except:
        pass
        
    uvicorn.run(app, host="0.0.0.0", port=8000)
