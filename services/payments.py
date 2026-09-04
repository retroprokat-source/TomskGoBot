import uuid
import requests

from config import (
    TOCHKA_API_TOKEN,
    TOCHKA_CUSTOMER_CODE,
    TOCHKA_MERCHANT_ID,
    TOCHKA_CLIENT_ID,
    BOT_URL
)


def create_payment_link(
    user_id: str,
    route_id: str,
    amount: str,
    purpose: str,
    webhook_url: str = "https://your-service.onrender.com/webhook/tochka"
) -> str | None:
    """
    Создаёт платёжную ссылку в Точке.

    Возвращает URL для оплаты или None, если что-то пошло не так.
    """

    url = "https://enter.tochka.com/uapi/acquiring/v1.0/payments"

    payment_link_id = str(uuid.uuid4())

    payload = {
        "Data": {
            "customerCode": TOCHKA_CUSTOMER_CODE,
            "merchantId": TOCHKA_MERCHANT_ID,
            "amount": amount,
            "purpose": purpose,
            "redirectUrl": BOT_URL,
            "failRedirectUrl": BOT_URL,
            "webhookUrl": webhook_url,
            "paymentMode": ["sbp", "card"],
            "saveCard": False,
            "preAuthorization": False,
            "ttl": 10080,
            "paymentLinkId": payment_link_id
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {TOCHKA_API_TOKEN}"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
            verify="russian_certs.pem"
        )
    except Exception as e:
        print(f"Ошибка при запросе к Точке: {e}")
        return None

    if response.status_code == 200:
        try:
            data = response.json()
        except Exception:
            return None

        payment_data = data.get("Data", {})
        payment_url = payment_data.get("paymentUrl") or payment_data.get("paymentLink")
        return payment_url

    print(f"Точка вернула статус {response.status_code}")
    print(f"Тело ответа: {response.text}")
    return None


def process_webhook(raw_body: str):
    """
    Обрабатывает входящий вебхук от Точки.

    Возвращает dict с данными платежа или None.
    """

    try:
        import json
        data = json.loads(raw_body)
    except Exception:
        return None

    return data
