import os
import sys

import requests
from dotenv import load_dotenv

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT_S = 10


def send_message(token: str, chat_id: str, text: str) -> None:
    url = TELEGRAM_API.format(token=token, method="sendMessage")

    response = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=TIMEOUT_S)
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "respuesta sin descripción"))


def main() -> int:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: falta TELEGRAM_BOT_TOKEN en el .env", file=sys.stderr)
        return 1

    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        print("Error: falta TELEGRAM_CHAT_ID en el .env", file=sys.stderr)
        return 1

    try:
        send_message(token, chat_id, "SmartMine: bot operativo")
    except requests.RequestException as exc:
        print(f"Error de red al contactar con Telegram: {type(exc).__name__}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Telegram rechazó el mensaje: {exc}", file=sys.stderr)
        return 1

    print("Mensaje enviado")
    return 0


if __name__ == "__main__":
    sys.exit(main())