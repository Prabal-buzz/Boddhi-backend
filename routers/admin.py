from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
import os
import uuid
import shutil

from ..database import get_db
from ..models.user import User, UserRole
from ..models.order import Order, OrderStatus
from ..models.product import Product
from ..schemas.schemas import UserProfile, OrderResponse, MessageResponse, AdminDashboardResponse
from ..security import get_current_user

router = APIRouter()

@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_dashboard_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    total_users = db.query(User).count()
    total_orders = db.query(Order).count()
    total_revenue = db.query(func.sum(Order.total_npr)).filter(Order.status != OrderStatus.CANCELLED).scalar() or 0.0
    total_products = db.query(Product).count()
    
    recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(5).all()
    
    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_products": total_products,
        "recent_orders": recent_orders
    }

@router.get("/users", response_model=List[UserProfile])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(User).all()

@router.patch("/users/{user_id}/activate", response_model=UserProfile)
def toggle_user_active(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user

@router.get("/orders", response_model=List[OrderResponse])
def list_all_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(Order).order_by(Order.created_at.desc()).all()

@router.get("/products/low-stock", response_model=List[dict])
def get_low_stock_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    products = db.query(Product).filter(Product.stock_quantity < 10).all()
    return [{"id": p.id, "name": p.name, "stock": p.stock_quantity} for p in products]

@router.post("/upload-media")
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Create uploads directory if not exists
    upload_dir = os.path.join("backend", "uploads", "products")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Return accessible URL
    url = f"/uploads/products/{filename}"
    return {"url": url}
