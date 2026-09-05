
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
from datetime import datetime

os.makedirs("uploads/videos", exist_ok=True)

app = FastAPI(title="Thaipodee Shop API")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

videos_db = []

@app.post("/videos/", summary="อัปโหลดวิดีโอ")
async def upload_video(
    title: str = Query(..., description="ชื่อวิดีโอ"),
    creator_id: str = Query(..., description="รหัสผู้สร้าง"),
    product_id: str = Query(None),
    video_file: UploadFile = File(...)
):
    ext = os.path.splitext(video_file.filename)[1]
    new_filename = f"{uuid.uuid4()}_{datetime.now().strftime('%Y-%m-%d-%H%M%S')}{ext}"
    file_path = f"uploads/videos/{new_filename}"
    
    with open(file_path, "wb") as f:
        content = await video_file.read()
        f.write(content)
    
    video_data = {
        "id": str(uuid.uuid4()),
        "video_url": f"uploads/videos/{new_filename}",
        "product_id": product_id,
        "likes_count": 0,
        "creator_id": creator_id,
        "thumbnail_url": None,
        "title": title,
        "views": 0,
        "created_at": datetime.now().isoformat()
    }
    videos_db.insert(0, video_data)
    
    return JSONResponse(status_code=201, content=video_data)

@app.get("/videos/feed", summary="ดูรายการวิดีโอ")
async def get_feed(skip: int = 0, limit: int = 10):
    return videos_db[skip : skip + limit]
