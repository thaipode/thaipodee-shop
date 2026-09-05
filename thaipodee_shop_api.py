from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import shutil
from datetime import datetime

app = FastAPI(title="Thaipodee Shop API")

# เปิดให้เข้าถึงได้จากทุกที่
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# สร้างโฟลเดอร์เก็บวิดีโอ
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ไฟล์เก็บข้อมูลวิดีโอ
VIDEOS_FILE = "videos.json"

# โหลดรายการวิดีโอ
def load_videos():
    if os.path.exists(VIDEOS_FILE):
        with open(VIDEOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# บันทึกรายการวิดีโอ
def save_videos(videos):
    with open(VIDEOS_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

# ✅ หน้าแรก — แสดงหน้าเว็บแทน JSON
@app.get("/")
def read_root():
    return FileResponse("index.html")

# ดึงรายการวิดีโอทั้งหมด
@app.get("/videos/")
def get_videos():
    return load_videos()

# อัปโหลดวิดีโอ
@app.post("/videos/")
def upload_video(file: UploadFile = File(...), title: str = Form(...)):
    try:
        allowed_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์วิดีโอเท่านั้น")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        videos = load_videos()
        new_video = {
            "id": len(videos) + 1,
            "title": title,
            "filename": filename,
            "video_url": f"/uploads/{filename}",
            "created_at": datetime.now().isoformat()
        }
        videos.insert(0, new_video)
        save_videos(videos)
        
        return new_video
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")

# ให้บริการไฟล์วิดีโอ
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
