from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from models.user import UserRole
from models.order import OrderStatus
from models.payment import PaymentMethod, PaymentStatus

# --- Generic Responses ---
class MessageResponse(BaseModel):
    message: str

# --- Auth & User Schemas ---
class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    country: Optional[str] = "Nepal"

class UserRegister(UserBase):
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AdminLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    user_role: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserProfile(UserBase):
    id: int
    role: UserRole
    is_active: bool
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

# --- Category & Product Schemas ---
class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class ProductMediaBase(BaseModel):
    url: str
    media_type: str = "image"
    order: int = 0

class ProductMediaCreate(ProductMediaBase):
    pass

class ProductMediaResponse(ProductMediaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    name: str
    slug: str
    description: str
    short_description: Optional[str] = None
    price_npr: float
    price_usd: Optional[float] = None
    discount_percent: float = 0.0
    stock_quantity: int = 0
    sku: Optional[str] = None
    material: Optional[str] = None
    origin: Optional[str] = None
    weight_grams: Optional[float] = None
    dimensions: Optional[str] = None
    image_url: Optional[str] = None
    category_id: int
    is_featured: bool = False
    media: Optional[List[ProductMediaCreate]] = None

class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    media: List[ProductMediaResponse] = []
    model_config = ConfigDict(from_attributes=True)

# --- Cart Schemas ---
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product: ProductResponse
    quantity: int
    model_config = ConfigDict(from_attributes=True)

class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    total_amount_npr: float

# --- Order Schemas ---
class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price_npr: float
    total_price_npr: float
    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    shipping_name: str
    shipping_email: EmailStr
    shipping_phone: str
    shipping_address: str
    shipping_city: str
    shipping_country: str = "Nepal"

class OrderResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    total_npr: float
    total_usd: Optional[float]
    created_at: datetime
    items: List[OrderItemResponse]
    model_config = ConfigDict(from_attributes=True)

# --- Payment Schemas ---
class PaymentInitiate(BaseModel):
    order_id: int
    method: str  # esewa, khalti, stripe, cod

class ESewaInitResponse(BaseModel):
    payment_url: str
    form_data: dict

class KhaltiInitResponse(BaseModel):
    payment_url: str
    pidx: str

class StripePaymentIntent(BaseModel):
    client_secret: str
    payment_intent_id: str
    publishable_key: str
    amount: float
    currency: str

class ESewaVerifyRequest(BaseModel):
    order_id: int
    ref_id: str
    encoded_data: str

class KhaltiVerifyRequest(BaseModel):
    order_id: int
    pidx: str

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    method: PaymentMethod
    status: PaymentStatus
    amount: float
    currency: str
    transaction_id: str
    gateway_ref_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Contact Schemas ---
class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    subject: str
    message: str

class ContactResponse(ContactCreate):
    id: int
    status: str
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Dashboard Schemas ---
class UserDashboardResponse(BaseModel):
    profile: UserProfile
    total_orders: int
    recent_orders: List[OrderResponse]
    total_spent_npr: float
    cart_items_count: int

class AdminDashboardResponse(BaseModel):
    total_users: int
    total_orders: int
    total_revenue: float
    total_products: int
    recent_orders: List[OrderResponse]
    model_config = ConfigDict(from_attributes=True)

# --- Search Schemas ---
class SearchResponse(BaseModel):
    products: List[ProductResponse]
    categories: List[CategoryResponse]
    total_results: int
