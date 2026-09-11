import json
import os
import requests
import websocket
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
MIN_MAGNITUDE = float(os.getenv("MIN_MAGNITUDE", "4.0"))
SEEN_FILE = "seen_ids.txt"

# Last inn ID-er fra fil ved oppstart
def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            # Les linjer, fjern whitespace og ignorer tomme linjer
            return set(line.strip() for line in f if line.strip())
    return set()

# Lagre en ny ID til filen
def save_seen_id(unid):
    with open(SEEN_FILE, "a") as f:
        f.write(f"{unid}\n")

# Hent lagrede ID-er når programmet starter
SEEN_UNIDS = load_seen_ids()


def on_message(ws, message):
    try:
        data = json.loads(message)
        props = data.get("data", {}).get("properties", {})

        unid = props.get("unid")
        mag = props.get("mag")
        
        # Hvis ID-en mangler eller vi allerede har sendt den: ignorer!
        if not unid or unid in SEEN_UNIDS:
            return

        region = props.get("flynn_region", "Ukjent område")
        depth = props.get("depth")
        time = props.get("time")

        url = f"https://seismicportal.eu/eventdetails.html?unid={unid}"

        if mag and mag >= MIN_MAGNITUDE:
            # Legg ID-en til i minnet OG lagre den i filen umiddelbart
            SEEN_UNIDS.add(unid)
            save_seen_id(unid)

            link_text = f"\n• *Lenke:* <{url}|Se kart og detaljer>"

            payload = {
                "text": (
                    f"🌋 *Nytt jordskjelv registrert!*\n"
                    f"• *Styrke:* M {mag}\n"
                    f"• *Område:* 🌍 {region}\n"
                    f"• *Dybde:* 🪨 {depth} km\n"
                    f"• *Tid (UTC):* ⏱️ {time}"
                    f"{link_text}"
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

    # Forhindrer at den krasjer og starter på nytt ved midlertidige nettverksfeil
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://www.seismicportal.eu/standing_order/websocket",
                on_message=on_message,
                on_open=on_open,
            )
            ws.run_forever(ping_interval=30, ping_timeout=10) # Holder tilkoblingen i live
        except Exception as e:
            print(f"WebSocket-tilkobling brutt, prøver på nytt... Feil: {e}")
            import time
            time.sleep(5) # Vent litt før vi prøver å koble til igjen
