from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from database import get_db
from models.product import Product, Category
from schemas.schemas import SearchResponse

router = APIRouter()

@router.get("/", response_model=SearchResponse)
def unified_search(
    q: str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(get_db)
):
    """
    Search across products and categories.
    """
    # Search Products (name and description)
    products = db.query(Product).filter(
        Product.is_active == True,
        or_(
            Product.name.ilike(f"%{q}%"),
            Product.description.ilike(f"%{q}%"),
            Product.short_description.ilike(f"%{q}%")
        )
    ).limit(20).all()
    
    # Search Categories (name and description)
    categories = db.query(Category).filter(
        Category.is_active == True,
        or_(
            Category.name.ilike(f"%{q}%"),
            Category.description.ilike(f"%{q}%")
        )
    ).limit(10).all()
    
    return SearchResponse(
        products=products,
        categories=categories,
        total_results=len(products) + len(categories)
    )
