import asyncio
import datetime
import re
import requests
from telethon import TelegramClient, events, errors
from datetime import timedelta

from keep_alive import keep_alive  # ✅ keeps Replit awake

# === TELEGRAM BOT CREDENTIALS ===
api_id = 26196044
api_hash = "5c47c8a9e95d68dbe220965b9e9ce520"
phone = "+639973584566"  # your phone number in international format

# === GOOGLE APPS SCRIPT WEBHOOK URL ===
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbxt3n1C0srFJXxBZ0rpHWdMw_Ps8lih3HkU3DExmy-EageSW4-Ic-gBZN_zXXI979agmQ/exec"

# === GROUP NAME TO LISTEN TO ===
GROUP_NAME = "Hexa Tickets Cancellations"

# === REGEX TO PARSE MESSAGES ===
pattern = re.compile(
    r'IT(?:[\s\w\.]*?-\s*)([\w\s\.]+?)\s+has\s+(approved|denied)\s+the\s+cancellation\s+of\s+ticket\s+([A-Z0-9\-]+)\s*\(([a-z0-9]+)\)\s*requested\s+by\s+([A-Z0-9.\-]+[A-Z0-9])',
    re.IGNORECASE
)

# --- Helper function to convert UTC to PH time ---
def ph_time(utc_dt):
    return (utc_dt + timedelta(hours=8)).strftime("%m/%d/%Y %I:%M:%S %p")

# === MAIN ASYNC FUNCTION ===
async def run_bot():
    while True:
        try:
            client = TelegramClient('user_session', api_id, api_hash)
            await client.start(phone)
            print("📡 Connected. Listening for messages…")

            @client.on(events.NewMessage())
            async def handler(event):
                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', None)
                if chat_title != GROUP_NAME:
                    return  # Ignore other groups

                message = event.raw_text.strip()
                segments = [seg.strip() for seg in re.split(r'\n\s*\n', message) if seg.strip()]

                for seg in segments:
                    match = pattern.search(seg)
                    if not match:
                        print("⚪ Ignored non-matching message segment:\n", seg)
                        continue

                    approver, action, ticket, refcode, booth = match.groups()
                    print(f"✅ Matched: Approver={approver}, Action={action}, Ticket={ticket}, Ref={refcode}, Booth={booth}")

                    # --- Inline mapping ---
                    full_title = f"{approver.strip()}"
                    if full_title == "Stefanie Obenza":
                        cancelled_by = "STEF"
                    elif full_title == "Michael Romo":
                        cancelled_by = "MIKE"
                    elif full_title == "Kedev":
                        cancelled_by = "KHEDEV"
                    elif full_title == "Richfield James P. Villanueva":
                        cancelled_by = "TROY"
                    else:
                        cancelled_by = full_title  # fallback

                    status = "APPROVED ✅" if "approved" in action.lower() else "DENIED ❌"

                    booth = booth.strip().upper()
                    if booth.startswith("R.CDO"):
                        area = "CDO"
                    elif booth.startswith("R.MOW") or booth.startswith("R.MOE"):
                        area = "MISOR"
                    elif booth.startswith(("CDO", "CDO-PAY")):
                        area = "CDO"
                    elif booth.startswith(("MOW", "MOE", "MOW-PAY", "MOE-PAY")):
                        area = "MISOR"
                    else:
                        area = "Unknown"

                    # --- Use PH local time for payload ---
                    message_time = ph_time(event.message.date)

                    payload = {
                        "date": message_time,
                        "ticket": ticket,
                        "refcode": refcode,
                        "booth": booth,
                        "status": status,
                        "cancelled_by": cancelled_by,
                        "area": area
                    }

                    try:
                        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
                        print(f"✅ Sent to webhook ({response.status_code}): {ticket} by {cancelled_by} in {area}")
                    except Exception as e:
                        print(f"❌ Error sending to webhook: {e}")

            await client.run_until_disconnected()

        except (errors.RPCError, ConnectionError, OSError) as e:
            print(f"⚠️ Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

# === RUN THE BOT ===
if __name__ == "__main__":
    keep_alive()  # ✅ start Replit webserver to prevent sleep
    asyncio.run(run_bot())
