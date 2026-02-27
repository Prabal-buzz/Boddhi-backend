"""
Handicrafts Business API - Main Application
=============================================
A FastAPI backend for a Nepali handicrafts business with:
- JWT Authentication (User & Admin)
- Product management
- Shopping cart
- Orders
- Nepal payment (eSewa, Khalti) & International payment (Stripe)
- Contact Us
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os

from database import create_tables
from routers import auth, products, cart, orders, payments, contact, admin, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - runs on startup and shutdown."""
    create_tables()
    print("✅ Database tables created/verified")
    yield
    print("🔒 Application shutting down")


app = FastAPI(
    title="Nepali Handicrafts API",
    description="""
## 🎨 Nepali Handicrafts Business API

A comprehensive REST API for managing a Nepali handicrafts e-commerce platform.

### Features
- **JWT Authentication** - Secure user and admin authentication
- **Product Management** - Browse, search, and manage handicraft products
- **Shopping Cart** - Add/remove items, update quantities
- **Orders** - Place and track orders
- **Payments** 
  - 🇳🇵 **Nepal**: eSewa, Khalti
  - 🌍 **International**: Stripe (Credit/Debit Cards)
- **Contact Us** - Customer inquiry system
- **Admin Panel** - Full management capabilities

### Authentication
Use the `/auth/login` endpoint to get a JWT token, then include it in requests:
```
Authorization: Bearer <your_token>
```

### Payment Flow
1. Create an order via `POST /orders/`
2. Initiate payment via `POST /payments/initiate`
3. Verify payment via `POST /payments/verify`
    """,
    version="1.0.0",
    contact={
        "name": "Handicrafts Support",
        "email": "support@nepalihandicrafts.com",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files for Uploads
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(cart.router, prefix="/cart", tags=["Shopping Cart"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(contact.router, prefix="/contact", tags=["Contact Us"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(search.router, prefix="/search", tags=["Search"])


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint with API information."""
    return {
        "message": "Welcome to Nepali Handicrafts API 🎨",
        "docs": "/docs",
        "redoc": "/redoc",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "Nepali Handicrafts API"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)