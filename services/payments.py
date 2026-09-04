import json
import uuid
import base64
import logging
import requests

from config import (
    TOCHKA_API_TOKEN,
    TOCHKA_CUSTOMER_CODE,
    TOCHKA_MERCHANT_ID,
    TOCHKA_CLIENT_ID,
    BOT_URL,
)
from database import add_payment

CERT_FILE = "russian_certs.pem"


def create_payment_link(user_id: str, route_id: str, amount: str, purpose: str):
    """
    Создаёт платёжную ссылку в Точке.
    Возвращает URL оплаты или None.
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
            "webhookUrl": "https://tomskgobot.onrender.com/webhook/tochka",
            "paymentMode": ["sbp", "card"],
            "saveCard": False,
            "preAuthorization": False,
            "ttl": 10080,
            "paymentLinkId": payment_link_id,
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {TOCHKA_API_TOKEN}",
    }

    try:
        logging.info(f"Создание платежа: amount={amount}, purpose={purpose}")
        response = requests.post(url, json=payload, headers=headers, timeout=30, verify=CERT_FILE)

        logging.info(f"Ответ Точки: status={response.status_code}")

        if response.status_code == 200:
            data = response.json()
            payment_url = (
                data.get("Data", {}).get("paymentUrl")
                or data.get("Data", {}).get("paymentLink")
            )

            if payment_url:
                add_payment(user_id, route_id, float(amount), purpose, payment_link_id)
                logging.info(f"✅ Платёжная ссылка создана: {payment_url[:100]}")
                return payment_url, payment_link_id
            else:
                logging.error("❌ Нет paymentUrl в ответе")
                return None
        else:
            logging.error(f"❌ Ошибка Точки: {response.status_code} {response.text[:500]}")
            return None

    except Exception as e:
        logging.error(f"❌ Ошибка создания платежа: {e}")
        return None


def setup_webhook():
    """Регистрирует вебхук Точки."""
    url = f"https://enter.tochka.com/uapi/webhook/v1.0/{TOCHKA_CLIENT_ID}"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {TOCHKA_API_TOKEN}",
    }

    payload = {
        "webhooksList": ["acquiringInternetPayment"],
        "url": "https://tomskgobot.onrender.com/webhook/tochka",
    }

    try:
        response = requests.put(url, json=payload, headers=headers, timeout=15, verify=CERT_FILE)
        logging.info(f"PUT: {response.status_code} {response.text[:300]}")

        if response.status_code == 200:
            logging.info("✅ Вебхук TomskGoBot зарегистрирован")
            return True
        else:
            logging.error(f"❌ Ошибка: {response.status_code} {response.text}")
            return False

    except Exception as e:
        logging.error(f"❌ Ошибка: {e}")
        return False


def process_webhook(raw_body: str) -> dict:
    """Декодирует JWT-вебхук от Точки."""
    try:
        parts = raw_body.split(".")
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        decoded = base64.b64decode(payload_b64).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        logging.error(f"❌ Ошибка декодирования вебхука: {e}")
        return {}
