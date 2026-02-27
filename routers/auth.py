"""
Authentication Router
=====================
Handles user registration, login (user & admin), token refresh,
and password management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from database import get_db
from models.user import User, UserRole
from schemas.schemas import (
    UserRegister, UserLogin, AdminLogin, TokenResponse,
    RefreshTokenRequest, UserProfile, UserUpdate, ChangePassword, MessageResponse,
    UserDashboardResponse
)
from models.order import Order, OrderStatus
from models.cart import CartItem
from sqlalchemy import func
from security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user
)
from config import settings

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="""
Register a new user account.

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one digit

After registration, you receive JWT tokens for immediate login.
    """
)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        hashed_password=hash_password(user_data.password),
        country=user_data.country or "Nepal",
        role=UserRole.USER,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate tokens
    token_data = {"sub": new_user.email, "role": new_user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=new_user.id,
        user_role=new_user.role.value,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="""
Authenticate as a regular user and receive JWT tokens.

Use the returned `access_token` as a Bearer token in subsequent requests:
```
Authorization: Bearer <access_token>
```

The `refresh_token` can be used to get new access tokens without re-login.
    """
)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support."
        )

    token_data = {"sub": user.email, "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        user_role=user.role.value,
    )


@router.post(
    "/admin/login",
    response_model=TokenResponse,
    summary="Admin login",
    description="""
Authenticate as an admin. Admin accounts must be created directly in the database
or by another admin. Regular users cannot access this endpoint.
    """
)
def admin_login(credentials: AdminLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    token_data = {"sub": user.email, "role": user.role.value}
    access_token = create_access_token(
        token_data,
        expires_delta=timedelta(hours=8)  # Longer session for admin
    )
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=8 * 3600,
        user_id=user.id,
        user_role=user.role.value,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use a valid refresh token to get a new access token without re-login."
)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(request.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    token_data = {"sub": user.email, "role": user.role.value}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        user_role=user.role.value,
    )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile"
)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get(
    "/dashboard",
    response_model=UserDashboardResponse,
    summary="Get unified user dashboard data"
)
def get_user_dashboard(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Total orders
    total_orders = db.query(Order).filter(Order.user_id == current_user.id).count()
    
    # Recent orders
    recent_orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    # Total spent
    total_spent = db.query(func.sum(Order.total_npr)).filter(
        Order.user_id == current_user.id,
        Order.status != OrderStatus.CANCELLED
    ).scalar() or 0.0
    
    # Cart items count
    cart_items_count = db.query(CartItem).filter(
        CartItem.user_id == current_user.id
    ).count()
    
    return UserDashboardResponse(
        profile=current_user,
        total_orders=total_orders,
        recent_orders=recent_orders,
        total_spent_npr=total_spent,
        cart_items_count=cart_items_count
    )


@router.put(
    "/me",
    response_model=UserProfile,
    summary="Update current user profile"
)
def update_my_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    for field, value in update_data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post(
    "/me/change-password",
    response_model=MessageResponse,
    summary="Change password"
)
def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return MessageResponse(message="Password changed successfully")


# Swagger UI compatible login (form-based)
@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible form-based login for Swagger UI."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    token_data = {"sub": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        user_role=user.role.value,
    )