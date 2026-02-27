from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from database import Base

class OrderStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    
    # Financial fields
    subtotal_npr = Column(Float, nullable=False)
    shipping_cost_npr = Column(Float, default=0.0)
    total_npr = Column(Float, nullable=False)
    total_usd = Column(Float, nullable=True)

    # Shipping information
    shipping_name = Column(String, nullable=False)
    shipping_email = Column(String, nullable=False)
    shipping_phone = Column(String, nullable=False)
    shipping_address = Column(Text, nullable=False)
    shipping_city = Column(String, nullable=False)
    shipping_country = Column(String, default="Nepal")
    
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="orders")
    
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    # Snapshot of product details at time of order
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_npr = Column(Float, nullable=False)
    total_price_npr = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
