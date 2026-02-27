from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.cart import CartItem
from ..models.product import Product
from ..models.user import User
from ..schemas.schemas import CartItemResponse, CartResponse, CartItemCreate, CartItemUpdate
from ..security import get_current_user

router = APIRouter()

@router.get("/", response_model=CartResponse)
def get_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    
    total_amount = sum(item.product.price_npr * item.quantity for item in items)
    
    return {
        "items": items,
        "total_items": sum(item.quantity for item in items),
        "total_amount_npr": total_amount
    }

@router.post("/", response_model=CartItemResponse)
def add_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == item_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product.stock_quantity < item_data.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")
        
    # Check if item already in cart
    cart_item = db.query(CartItem).filter(
        CartItem.user_id == current_user.id,
        CartItem.product_id == item_data.product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += item_data.quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )
        db.add(cart_item)
        
    db.commit()
    db.refresh(cart_item)
    return cart_item

@router.put("/{item_id}", response_model=CartItemResponse)
def update_cart_item(
    item_id: int,
    item_data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
        
    if cart_item.product.stock_quantity < item_data.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")
        
    cart_item.quantity = item_data.quantity
    db.commit()
    db.refresh(cart_item)
    return cart_item

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cart_item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.user_id == current_user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
        
    db.delete(cart_item)
    db.commit()
    return None

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()
    return None
