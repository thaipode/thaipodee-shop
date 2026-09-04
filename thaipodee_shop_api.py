from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, Integer, ForeignKey, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import uuid
import json
import os

# ==============================================
# 🗄️ DATABASE — ตั้งค่า
# ==============================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./thaipodee_shop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"message": "ยินดีต้อนรับสู่ THAIPODEE SHOP API 🇹🇭🛒"}

# 📊 MODELS — ตารางข้อมูลทั้งหมด
# ==============================================
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    role = Column(String)  # buyer, seller, creator
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String, ForeignKey("users.id"))
    name = Column(String, index=True)
    description = Column(Text)
    price = Column(Float)
    stock = Column(Integer, default=0)
    image_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Video(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    video_url = Column(String)
    thumbnail_url = Column(String)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    views = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String, ForeignKey("users.id"))
    product_id = Column(String, ForeignKey("products.id"))
    quantity = Column(Integer)
    total_price = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class LiveStream(Base):
    __tablename__ = "live_streams"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    host_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    stream_url = Column(String)
    thumbnail_url = Column(String)
    is_live = Column(Boolean, default=True)
    viewer_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class LiveProduct(Base):
    __tablename__ = "live_products"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    live_id = Column(String, ForeignKey("live_streams.id"))
    product_id = Column(String, ForeignKey("products.id"))
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class LiveComment(Base):
    __tablename__ = "live_comments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    live_id = Column(String, ForeignKey("live_streams.id"))
    user_id = Column(String, ForeignKey("users.id"))
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AffiliateLink(Base):
    __tablename__ = "affiliate_links"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(String, ForeignKey("users.id"))
    product_id = Column(String, ForeignKey("products.id"))
    commission_rate = Column(Float, default=0.10)
    click_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class AffiliateTransaction(Base):
    __tablename__ = "affiliate_transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    link_id = Column(String, ForeignKey("affiliate_links.id"))
    order_id = Column(String, ForeignKey("orders.id"))
    amount = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    type = Column(String)
    title = Column(String)
    message = Column(Text)
    data = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id"))
    user_id = Column(String, ForeignKey("users.id"))
    amount = Column(Float)
    method = Column(String)
    status = Column(String, default="pending")
    transaction_id = Column(String, nullable=True)
    slip_image = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ==============================================
# 📋 PYDANTIC SCHEMAS
# ==============================================
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock: int

class VideoCreate(BaseModel):
    title: str
    product_id: Optional[str] = None

class OrderCreate(BaseModel):
    product_id: str
    quantity: int

# ==============================================
# 🔧 FASTAPI SETUP
# ==============================================
app = FastAPI(title="Thaipodee Shop API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ==============================================
# 🔔 WEBSOCKET — แจ้งเตือนเรียลไทม์
# ==============================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for conn in self.active_connections[user_id]:
                await conn.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/notifications/{user_id}")
async def ws_notifications(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

# ==============================================
# 🛒 API — สินค้า
# ==============================================
@app.post("/products/", status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, seller_id: str, db: Session = Depends(get_db)):
    db_product = Product(**product.dict(), seller_id=seller_id)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/")
def list_products(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.is_active).offset(skip).limit(limit).all()

@app.get("/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product: raise HTTPException(404, "ไม่พบสินค้า")
    return product

# ==============================================
# 🎬 API — วิดีโอ
# ==============================================
@app.post("/videos/")
def upload_video(
    title: str, creator_id: str, product_id: Optional[str] = None,
    video_file: UploadFile = File(...), db: Session = Depends(get_db)
):
    os.makedirs("uploads/videos", exist_ok=True)
    file_path = f"uploads/videos/{uuid.uuid4()}_{video_file.filename}"
    with open(file_path, "wb") as f: f.write(video_file.file.read())
    
    db_video = Video(creator_id=creator_id, title=title, video_url=file_path, product_id=product_id)
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    return db_video

@app.get("/videos/feed")
def get_feed(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Video).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()

# ==============================================
# 📦 API — คำสั่งซื้อ
# ==============================================
@app.post("/orders/", status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, buyer_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).get(order.product_id)
    if not product: raise HTTPException(404, "ไม่พบสินค้า")
    if product.stock < order.quantity: raise HTTPException(400, "สินค้าไม่พอ")
    
    total = product.price * order.quantity
    db_order = Order(buyer_id=buyer_id, product_id=order.product_id,
                     quantity=order.quantity, total_price=total)
    product.stock -= order.quantity
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return {"order": db_order, "total": total}

# ==============================================
# 📡 API — ไลฟ์ขายของ
# ==============================================
@app.post("/lives/")
def create_live(title: str, host_id: str, product_ids: List[str], db: Session = Depends(get_db)):
    stream = LiveStream(title=title, host_id=host_id,
                        stream_url=f"rtmp://localhost/live/{uuid.uuid4()}")
    db.add(stream)
    db.flush()
    for idx, pid in enumerate(product_ids):
        db.add(LiveProduct(live_id=stream.id, product_id=pid, position=idx))
    db.commit()
    db.refresh(stream)
    return stream

@app.get("/lives/active")
def get_active_lives(db: Session = Depends(get_db)):
    return db.query(LiveStream).filter(LiveStream.is_live).order_by(LiveStream.viewer_count.desc()).all()

@app.post("/lives/{live_id}/comments")
def post_comment(live_id: str, user_id: str, text: str, db: Session = Depends(get_db)):
    comment = LiveComment(live_id=live_id, user_id=user_id, text=text)
    db.add(comment)
    db.commit()
    return comment

# ==============================================
# 💰 API — Affiliate
# ==============================================
@app.post("/affiliate/links")
def create_affiliate_link(
    creator_id: str, product_id: str, commission_rate: float = 0.10, db: Session = Depends(get_db)
):
    link = AffiliateLink(
        creator_id=creator_id, product_id=product_id,
        commission_rate=max(0.01, min(commission_rate, 0.50))
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"link_id": link.id, "affiliate_url": f"/product/{product_id}?ref={link.id}"}

@app.get("/affiliate/stats/{creator_id}")
def get_affiliate_stats(creator_id: str, db: Session = Depends(get_db)):
    links = db.query(AffiliateLink).filter(AffiliateLink.creator_id == creator_id).all()
    total_clicks = sum(l.click_count for l in links)
    transactions = db.query(AffiliateTransaction)\
        .join(AffiliateLink).filter(AffiliateLink.creator_id == creator_id)\
        .filter(AffiliateTransaction.status == "paid").all()
    total_earned = sum(t.amount for t in transactions)
    return {
        "total_links": len(links), "total_clicks": total_clicks,
        "total_earned": total_earned,
        "pending_amount": sum(t.amount for t in transactions if t.status == "pending")
    }

# ==============================================
# 🔔 API — แจ้งเตือน
# ==============================================
@app.post("/notifications/", status_code=201)
async def create_notification(
    user_id: str, type: str, title: str, message: str, data: dict = None, db: Session = Depends(get_db)
):
    notification = Notification(
        user_id=user_id, type=type, title=title, message=message,
        data=json.dumps(data) if data else None
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    await manager.send_personal_message({
        "id": notification.id, "type": type, "title": title,
        "message": message, "created_at": notification.created_at.isoformat()
    }, user_id)
    return notification

@app.get("/notifications/{user_id}")
def get_notifications(user_id: str, unread_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only: q = q.filter(Notification.is_read == False)
    return q.order_by(Notification.created_at.desc()).limit(50).all()

@app.patch("/notifications/{notification_id}/read")
def mark_as_read(notification_id: str, db: Session = Depends(get_db)):
    nf = db.query(Notification).get(notification_id)
    if nf: nf.is_read = True; db.commit()
    return {"success": True}

# ==============================================
# 💳 API — ชำระเงิน
# ==============================================
PROMPTPAY_NUMBER = "0000000000"  # 🔑 เปลี่ยนเป็นเบอร์/เลขบัญชีจริง
STRIPE_SECRET_KEY = "sk_test_XXX"  # 🔑 ใส่คีย์จริง

@app.post("/payments/create")
def create_payment(order_id: str, user_id: str, method: str, db: Session = Depends(get_db)):
    order = db.query(Order).get(order_id)
    if not order: raise HTTPException(404, "ไม่พบคำสั่งซื้อ")
    
    payment = Payment(order_id=order_id, user_id=user_id, amount=order.total_price, method=method)
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if method == "promptpay":
        return {
            "payment_id": payment.id, "method": "promptpay",
            "amount": order.total_price,
            "qr_data": f"promptpay://pay?number={PROMPTPAY_NUMBER}&amount={order.total_price}"
        }
    elif method == "stripe":
        return {"payment_id": payment.id, "method": "stripe", "status": "ready"}
    
    return {"payment_id": payment.id, "status": "pending"}

# ==============================================
# 🚀 RUN SERVER
# ==============================================
if __name__ == "__main__":
    import uvicorn
    print("="*50)
    print("  🇹🇭 Thaipodee Shop API — กำลังทำงาน")
    print("  📄 เอกสาร API: http://127.0.0.1:8000/docs")
    print("="*50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
