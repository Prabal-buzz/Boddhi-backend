"""
Payments Router
===============
Handles payment processing for:
- eSewa (Nepal digital wallet)
- Khalti (Nepal digital wallet)  
- Stripe (International credit/debit cards)
- Cash on Delivery (Nepal only)

Payment Flow:
1. POST /payments/initiate  → Returns payment URL or client secret
2. User completes payment on gateway
3. POST /payments/verify    → Verifies payment and updates order status
"""

import uuid
import hmac
import hashlib
import base64
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.order import Order, OrderStatus
from ..models.payment import Payment, PaymentMethod, PaymentStatus
from ..models.user import User
from ..schemas.schemas import (
    PaymentInitiate, PaymentResponse, ESewaVerifyRequest,
    KhaltiVerifyRequest, StripePaymentIntent, MessageResponse,
    ESewaInitResponse, KhaltiInitResponse
)
from ..security import get_current_user
from ..config import settings

router = APIRouter()


def generate_transaction_id() -> str:
    """Generate unique transaction ID."""
    return f"HC-TXN-{uuid.uuid4().hex[:12].upper()}"


# ─────────────────────────────────────────────
# eSewa Payment (Nepal)
# ─────────────────────────────────────────────

def generate_esewa_signature(total_amount: float, transaction_uuid: str, product_code: str) -> str:
    """
    Generate HMAC-SHA256 signature for eSewa v2 API.
    
    eSewa requires: total_amount,transaction_uuid,product_code
    """
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    key = settings.ESEWA_SECRET_KEY.encode("utf-8")
    msg = message.encode("utf-8")
    signature = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.b64encode(signature).decode("utf-8")


def initiate_esewa_payment(order: Order, transaction_id: str) -> dict:
    """
    Prepare eSewa payment form data.
    
    eSewa v2 uses a signed form POST to their endpoint.
    Returns form_data to be submitted by frontend as POST.
    
    Docs: https://developer.esewa.com.np/
    """
    amount = order.total_npr
    product_code = settings.ESEWA_MERCHANT_CODE

    signature = generate_esewa_signature(amount, transaction_id, product_code)

    form_data = {
        "amount": str(int(amount)),  # eSewa expects integer NPR (paisa not needed)
        "tax_amount": "0",
        "total_amount": str(int(amount)),
        "transaction_uuid": transaction_id,
        "product_code": product_code,
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "success_url": f"{settings.FRONTEND_URL}/payment/esewa/success?order_id={order.id}",
        "failure_url": f"{settings.FRONTEND_URL}/payment/esewa/failure?order_id={order.id}",
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature": signature,
    }

    return {
        "payment_url": f"{settings.ESEWA_BASE_URL}/api/epay/main/v2/form",
        "form_data": form_data,
    }


def verify_esewa_payment(ref_id: str, transaction_id: str, amount: float) -> dict:
    """
    Verify eSewa payment status via their API.
    
    eSewa returns encoded response that must be decoded and verified.
    """
    product_code = settings.ESEWA_MERCHANT_CODE
    url = f"{settings.ESEWA_BASE_URL}/api/epay/transaction/status/"
    params = {
        "product_code": product_code,
        "total_amount": str(int(amount)),
        "transaction_uuid": transaction_id,
    }

    # Note: In production, use async httpx. Using sync here for simplicity.
    import urllib.request
    import urllib.parse

    full_url = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full_url, timeout=10) as response:
            data = json.loads(response.read())
            return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"eSewa verification failed: {str(e)}")


# ─────────────────────────────────────────────
# Khalti Payment (Nepal)
# ─────────────────────────────────────────────

def initiate_khalti_payment(order: Order, transaction_id: str) -> dict:
    """
    Initiate Khalti payment via their Lookup API.
    
    Returns payment URL for redirect.
    Docs: https://docs.khalti.com/khalti-epayment/
    """
    # Khalti uses paisa (1 NPR = 100 paisa)
    amount_paisa = int(order.total_npr * 100)

    payload = {
        "return_url": f"{settings.FRONTEND_URL}/payment/khalti/verify?order_id={order.id}",
        "website_url": settings.FRONTEND_URL,
        "amount": amount_paisa,
        "purchase_order_id": str(order.id),
        "purchase_order_name": f"Order {order.order_number}",
        "customer_info": {
            "name": order.shipping_name,
            "email": order.user.email if order.user else "",
            "phone": order.shipping_phone or "9800000000",
        },
        "amount_breakdown": [
            {
                "label": "Order Items",
                "amount": int(order.subtotal_npr * 100),
            },
            {
                "label": "Shipping",
                "amount": int(order.shipping_cost_npr * 100),
            },
        ],
    }

    headers = {
        "Authorization": f"key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    import urllib.request
    import urllib.parse

    req = urllib.request.Request(
        f"{settings.KHALTI_BASE_URL}/api/epayment/initiate/",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return {
                "payment_url": data.get("payment_url"),
                "pidx": data.get("pidx"),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Khalti initiation failed: {str(e)}")


def verify_khalti_payment(pidx: str) -> dict:
    """Verify Khalti payment using pidx."""
    headers = {
        "Authorization": f"key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    import urllib.request

    req = urllib.request.Request(
        f"{settings.KHALTI_BASE_URL}/api/epayment/lookup/",
        data=json.dumps({"pidx": pidx}).encode(),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Khalti verification failed: {str(e)}")


# ─────────────────────────────────────────────
# Stripe Payment (International)
# ─────────────────────────────────────────────

def initiate_stripe_payment(order: Order, transaction_id: str) -> dict:
    """
    Create a Stripe PaymentIntent for international payments.
    
    Returns client_secret for frontend Stripe.js to complete payment.
    Docs: https://stripe.com/docs/payments/payment-intents
    """
    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Amount in smallest currency unit (cents for USD)
        amount_cents = int((order.total_usd or order.total_npr * 0.0075) * 100)

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            metadata={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "transaction_id": transaction_id,
            },
            description=f"Nepali Handicrafts Order #{order.order_number}",
        )

        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "amount": amount_cents / 100,
            "currency": "usd",
        }
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Stripe not configured. Install: pip install stripe"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@router.post(
    "/initiate",
    summary="Initiate payment",
    description="""
Initiate a payment for an order.

**Payment Methods:**

🇳🇵 **Nepal (NPR):**
- `esewa` - eSewa digital wallet. Returns `payment_url` and `form_data` for POST redirect.
- `khalti` - Khalti digital wallet. Returns `payment_url` for redirect.
- `cod` - Cash on delivery. Order confirmed immediately.

🌍 **International (USD):**
- `stripe` - Credit/debit cards. Returns `client_secret` for Stripe.js frontend.

**Integration Guide:**

**eSewa:** Submit `form_data` as HTML form POST to `payment_url`.
```html
<form action="{payment_url}" method="POST">
  <!-- iterate form_data fields as hidden inputs -->
</form>
```

**Khalti:** Redirect user to `payment_url`.

**Stripe:** Use `client_secret` with Stripe.js:
```javascript
stripe.confirmCardPayment(client_secret, {
  payment_method: { card: cardElement }
})
```
    """
)
async def initiate_payment(
    data: PaymentInitiate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get and validate order
    order = db.query(Order).filter(Order.id == data.order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be paid. Status: {order.status.value}"
        )

    # Check if payment already exists
    existing_payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if existing_payment and existing_payment.status == PaymentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Order is already paid")

    transaction_id = generate_transaction_id()

    # Handle Cash on Delivery
    if data.method == "cod":
        if order.shipping_country.lower() not in ["nepal", "np"]:
            raise HTTPException(
                status_code=400,
                detail="Cash on delivery is only available for Nepal"
            )

        payment = Payment(
            order_id=order.id,
            method=PaymentMethod.CASH_ON_DELIVERY,
            status=PaymentStatus.PENDING,
            amount=order.total_npr,
            currency="NPR",
            transaction_id=transaction_id,
        )
        db.add(payment)
        order.status = OrderStatus.CONFIRMED
        db.commit()

        return {
            "method": "cod",
            "message": "Cash on delivery order confirmed",
            "order_number": order.order_number,
            "amount_npr": order.total_npr,
            "transaction_id": transaction_id,
        }

    # Handle eSewa
    if data.method == "esewa":
        esewa_data = initiate_esewa_payment(order, transaction_id)

        payment = Payment(
            order_id=order.id,
            method=PaymentMethod.ESEWA,
            status=PaymentStatus.INITIATED,
            amount=order.total_npr,
            currency="NPR",
            transaction_id=transaction_id,
        )
        db.add(payment)
        db.commit()

        return ESewaInitResponse(
            payment_url=esewa_data["payment_url"],
            form_data=esewa_data["form_data"],
        )

    # Handle Khalti
    if data.method == "khalti":
        khalti_data = initiate_khalti_payment(order, transaction_id)

        payment = Payment(
            order_id=order.id,
            method=PaymentMethod.KHALTI,
            status=PaymentStatus.INITIATED,
            amount=order.total_npr,
            currency="NPR",
            transaction_id=transaction_id,
            khalti_pidx=khalti_data.get("pidx"),
        )
        db.add(payment)
        db.commit()

        return KhaltiInitResponse(
            payment_url=khalti_data["payment_url"],
            pidx=khalti_data["pidx"],
        )

    # Handle Stripe
    if data.method == "stripe":
        stripe_data = initiate_stripe_payment(order, transaction_id)

        payment = Payment(
            order_id=order.id,
            method=PaymentMethod.STRIPE,
            status=PaymentStatus.INITIATED,
            amount=order.total_usd or round(order.total_npr * 0.0075, 2),
            currency="USD",
            transaction_id=transaction_id,
            stripe_payment_intent_id=stripe_data["payment_intent_id"],
            stripe_client_secret=stripe_data["client_secret"],
        )
        db.add(payment)
        db.commit()

        return StripePaymentIntent(
            client_secret=stripe_data["client_secret"],
            payment_intent_id=stripe_data["payment_intent_id"],
            publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
            amount=stripe_data["amount"],
            currency="usd",
        )

    raise HTTPException(status_code=400, detail="Invalid payment method")


@router.post(
    "/verify/esewa",
    response_model=PaymentResponse,
    summary="Verify eSewa payment",
    description="""
Verify an eSewa payment after redirect from eSewa gateway.

After successful payment, eSewa redirects to your `success_url` with query params.
Extract `refId` from query params and call this endpoint.
    """
)
def verify_esewa(
    data: ESewaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == data.order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    payment = db.query(Payment).filter(
        Payment.order_id == order.id,
        Payment.method == PaymentMethod.ESEWA
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Decode eSewa's encoded response
    try:
        decoded = json.loads(base64.b64decode(data.encoded_data).decode())
        response_status = decoded.get("status")
        gateway_ref_id = decoded.get("transaction_code")  # eSewa's transaction code
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid eSewa response data")

    if response_status == "COMPLETE":
        payment.status = PaymentStatus.COMPLETED
        payment.gateway_ref_id = gateway_ref_id
        payment.esewa_ref_id = data.ref_id
        payment.gateway_response = json.dumps(decoded)
        order.status = OrderStatus.CONFIRMED

        db.commit()
        db.refresh(payment)
        return payment
    else:
        payment.status = PaymentStatus.FAILED
        payment.gateway_response = json.dumps(decoded)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Payment failed. Status: {response_status}")


@router.post(
    "/verify/khalti",
    response_model=PaymentResponse,
    summary="Verify Khalti payment",
    description="""
Verify a Khalti payment after redirect.

After payment, Khalti redirects to your `return_url` with `pidx` query param.
Call this endpoint with the `pidx` to verify.
    """
)
def verify_khalti(
    data: KhaltiVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == data.order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    payment = db.query(Payment).filter(
        Payment.order_id == order.id,
        Payment.method == PaymentMethod.KHALTI
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Verify with Khalti
    khalti_response = verify_khalti_payment(data.pidx)

    if khalti_response.get("status") == "Completed":
        payment.status = PaymentStatus.COMPLETED
        payment.gateway_ref_id = khalti_response.get("transaction_id")
        payment.gateway_response = json.dumps(khalti_response)
        order.status = OrderStatus.CONFIRMED

        db.commit()
        db.refresh(payment)
        return payment
    else:
        payment.status = PaymentStatus.FAILED
        payment.gateway_response = json.dumps(khalti_response)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Khalti payment failed. Status: {khalti_response.get('status')}"
        )


@router.post(
    "/verify/stripe",
    response_model=PaymentResponse,
    summary="Verify Stripe payment",
    description="""
Verify a Stripe payment after frontend completes the payment.

After `stripe.confirmCardPayment()` succeeds on frontend, call this endpoint
with the `payment_intent_id` to confirm the order.
    """
)
def verify_stripe(
    order_id: int,
    payment_intent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    payment = db.query(Payment).filter(
        Payment.order_id == order.id,
        Payment.method == PaymentMethod.STRIPE
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if intent.status == "succeeded":
            payment.status = PaymentStatus.COMPLETED
            payment.gateway_ref_id = payment_intent_id
            payment.gateway_response = json.dumps({"status": intent.status, "id": intent.id})
            order.status = OrderStatus.CONFIRMED

            db.commit()
            db.refresh(payment)
            return payment
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Payment not completed. Stripe status: {intent.status}"
            )
    except ImportError:
        raise HTTPException(status_code=500, detail="Stripe not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/webhook/stripe",
    include_in_schema=False,
    summary="Stripe webhook handler"
)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhooks for asynchronous payment events.
    Configure this endpoint in your Stripe dashboard as a webhook.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]
        order_id = pi.get("metadata", {}).get("order_id")
        if order_id:
            order = db.query(Order).filter(Order.id == int(order_id)).first()
            payment = db.query(Payment).filter(
                Payment.order_id == int(order_id),
                Payment.method == PaymentMethod.STRIPE
            ).first()

            if order and payment and payment.status != PaymentStatus.COMPLETED:
                payment.status = PaymentStatus.COMPLETED
                payment.gateway_ref_id = pi["id"]
                order.status = OrderStatus.CONFIRMED
                db.commit()

    return {"received": True}


@router.get(
    "/{order_id}",
    response_model=PaymentResponse,
    summary="Get payment status",
    description="Get payment information for a specific order."
)
def get_payment(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    from models.user import UserRole
    if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment