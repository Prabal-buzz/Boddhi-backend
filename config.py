import os
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App Settings
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./handicrafts.db"
    
    # Security Settings
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # eSewa Settings
    ESEWA_MERCHANT_CODE: str = "EPAYTEST"
    ESEWA_SECRET_KEY: str = "8g8M8dg76h8dgYS5D69uY9E3q8u8Snd9"
    ESEWA_BASE_URL: str = "https://rc-epay.esewa.com.np"
    
    # Khalti Settings
    KHALTI_SECRET_KEY: str = "test_secret_key_67890efghij1234567890"
    KHALTI_BASE_URL: str = "https://a.khalti.com"
    
    # Stripe Settings
    STRIPE_SECRET_KEY: str = "sk_test_51Px9..."
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_51Px9..."
    STRIPE_WEBHOOK_SECRET: str = "whsec_..."

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
