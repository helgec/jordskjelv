import json
import os
import requests
import websocket
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
MIN_MAGNITUDE = float(os.getenv("MIN_MAGNITUDE", "5.5"))


def on_message(ws, message):
    try:
        data = json.loads(message)
        props = data.get("data", {}).get("properties", {})

        mag = props.get("mag")
        region = props.get("flynn_region", "Ukjent område")
        depth = props.get("depth")
        time = props.get("time")

        if mag and mag >= MIN_MAGNITUDE:
            payload = {
                "text": (
                    f"🚨 *Nytt jordskjelv registrert!*\n"
                    f"• *Styrke:* M {mag}\n"
                    f"• *Område:* {region}\n"
                    f"• *Dybde:* {depth} km\n"
                    f"• *Tid (UTC):* {time}"
                )
            }
            requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Feil: {e}")


def on_open(ws):
    print("Tilkoblet SeismicPortal. Lytter etter skjelv...")


if __name__ == "__main__":
    if not SLACK_WEBHOOK_URL:
        print("FEIL: SLACK_WEBHOOK_URL mangler i .env")
        exit(1)

    ws = websocket.WebSocketApp(
        "wss://www.seismicportal.eu/standing_order/websocket",
        on_message=on_message,
        on_open=on_open,
    )
    ws.run_forever()
