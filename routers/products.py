from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.product import Product, Category
from models.user import User, UserRole
from schemas.schemas import ProductResponse, CategoryResponse, ProductBase, CategoryBase
from security import get_current_user

router = APIRouter()

# --- Public Endpoints ---

@router.get("/", response_model=List[ProductResponse])
def list_products(
    category_slug: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)
    
    if category_slug:
        category = db.query(Category).filter(Category.slug == category_slug).first()
        if category:
            query = query.filter(Product.category_id == category.id)
            
    if min_price:
        query = query.filter(Product.price_npr >= min_price)
    if max_price:
        query = query.filter(Product.price_npr <= max_price)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
        
    return query.offset(skip).limit(limit).all()

@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).all()

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/slug/{slug}", response_model=ProductResponse)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# --- Admin Endpoints ---

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    new_product = Product(**product_data.model_dump(exclude={"media"}))
    
    # Handle media
    if product_data.media:
        from ..models.product import ProductMedia
        for media_item in product_data.media:
            new_media = ProductMedia(**media_item.model_dump(), product=new_product)
            db.add(new_media)

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    for field, value in product_data.model_dump(exclude={"media"}).items():
        setattr(product, field, value)
        
    # Handle media update (refresh all)
    if product_data.media is not None:
        from ..models.product import ProductMedia
        # Delete old media
        db.query(ProductMedia).filter(ProductMedia.product_id == product.id).delete()
        
        # Add new media
        for media_item in product_data.media:
            new_media = ProductMedia(**media_item.model_dump(), product_id=product.id)
            db.add(new_media)
        
    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    db.delete(product)
    db.commit()
    return None

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    new_category = Category(**category_data.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category
