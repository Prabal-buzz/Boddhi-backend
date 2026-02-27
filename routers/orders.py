from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models.order import Order, OrderItem, OrderStatus
from models.cart import CartItem
from models.user import User, UserRole
from schemas.schemas import OrderResponse, OrderCreate
from security import get_current_user

router = APIRouter()

@router.get("/", response_model=List[OrderResponse])
def list_my_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    return order

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get cart items
    cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
        
    subtotal = sum(item.product.price_npr * item.quantity for item in cart_items)
    shipping_cost = 100.0  # Flat rate for demo
    total = subtotal + shipping_cost
    
    # Create order
    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        user_id=current_user.id,
        subtotal_npr=subtotal,
        shipping_cost_npr=shipping_cost,
        total_npr=total,
        total_usd=round(total * 0.0075, 2), # Sample conversion
        **order_data.model_dump()
    )
    db.add(order)
    db.flush() # Get order ID
    
    # Create order items and reduce stock
    for item in cart_items:
        if item.product.stock_quantity < item.quantity:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Not enough stock for {item.product.name}")
            
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price_npr=item.product.price_npr,
            total_price_npr=item.product.price_npr * item.quantity
        )
        db.add(order_item)
        item.product.stock_quantity -= item.quantity
    
    # Clear cart
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    
    db.commit()
    db.refresh(order)
    return order

@router.patch("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")
        
    order.status = OrderStatus.CANCELLED
    
    # Restore stock
    for item in order.items:
        if item.product:
            item.product.stock_quantity += item.quantity
            
    db.commit()
    db.refresh(order)
    return order
@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status: OrderStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order.status = status
    db.commit()
    db.refresh(order)
    return order
