import json
import os
import time
import sys
import requests
import websocket
from dotenv import load_dotenv

# Importer status-hjelperen
sys.path.append("/home/nrknyheter")
from status_helper import update_status

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
        event_time = props.get("time")

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
                    f"• *Tid (UTC):* ⏱️ {event_time}"
                    f"{link_text}"
                )
            }
            requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)

    except Exception as e:
        print(f"Feil ved behandling av jordskjelvmelding: {e}")
        update_status("jordskjelv", "Jordskjelv-overvåker", status="ERROR", error_msg=f"Meldingsfeil: {e}")


def on_open(ws):
    print("Tilkoblet SeismicPortal. Lytter etter skjelv...")
    # Registrerer at tilkoblingen er opprettet og alt er OK
    update_status("jordskjelv", "Jordskjelv-overvåker", status="OK")


def on_error(ws, error):
    print(f"WebSocket-feil: {error}")
    update_status("jordskjelv", "Jordskjelv-overvåker", status="ERROR", error_msg=str(error))


if __name__ == "__main__":
    if not SLACK_WEBHOOK_URL:
        print("FEIL: SLACK_WEBHOOK_URL mangler i .env")
        update_status("jordskjelv", "Jordskjelv-overvåker", status="ERROR", error_msg="Mangler SLACK_WEBHOOK_URL i .env")
        sys.exit(1)

    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://www.seismicportal.eu/standing_order/websocket",
                on_message=on_message,
                on_open=on_open,
                on_error=on_error,
            )
            # Holder tilkoblingen i live
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            print(f"WebSocket-tilkobling brutt, prøver på nytt... Feil: {e}")
            update_status("jordskjelv", "Jordskjelv-overvåker", status="ERROR", error_msg=f"Tilkoblingsbrudd: {e}")
            time.sleep(5)
