from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    short_description = Column(String, nullable=True)
    price_npr = Column(Float, nullable=False)
    price_usd = Column(Float, nullable=True)
    discount_percent = Column(Float, default=0.0)
    stock_quantity = Column(Integer, default=0)
    sku = Column(String, unique=True, index=True, nullable=True)
    material = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    weight_grams = Column(Float, nullable=True)
    dimensions = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="products")
    
    # Media relationship
    media = relationship("ProductMedia", back_populates="product", cascade="all, delete-orphan", order_by="ProductMedia.order")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ProductMedia(Base):
    __tablename__ = "product_media"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    url = Column(Text, nullable=False)
    media_type = Column(String, default="image") # image or video
    order = Column(Integer, default=0)

    product = relationship("Product", back_populates="media")
