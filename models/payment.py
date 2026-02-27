from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from database import Base

class PaymentMethod(enum.Enum):
    ESEWA = "esewa"
    KHALTI = "khalti"
    STRIPE = "stripe"
    CASH_ON_DELIVERY = "cod"

class PaymentStatus(enum.Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.INITIATED)
    
    amount = Column(Float, nullable=False)
    currency = Column(String, default="NPR")
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    
    # Gateway specific IDs
    gateway_ref_id = Column(String, nullable=True)  # General ref ID from gateway
    esewa_ref_id = Column(String, nullable=True)
    khalti_pidx = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    stripe_client_secret = Column(String, nullable=True)
    
    gateway_response = Column(Text, nullable=True)  # JSON dump of full response

    order = relationship("Order", back_populates="payment")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
