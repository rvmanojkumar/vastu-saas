import razorpay
from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["Payments"])

client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_SECRET"))


@router.post("/create-order")
def create_order(data: dict):
    amount = data.get("amount", 49900)  # ₹499 in paise

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return {
        "order_id": order["id"],
        "amount": amount,
        "key": "YOUR_KEY_ID"
    }