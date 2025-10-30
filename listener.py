import asyncio
import datetime
import re
import requests
import os
from telethon import TelegramClient, events, errors
from datetime import timedelta

# === TELEGRAM BOT CREDENTIALS ===
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
phone = os.environ.get("PHONE")

# === GOOGLE APPS SCRIPT WEBHOOK URL ===
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# === GROUP NAME TO LISTEN TO ===
GROUP_NAME = os.environ.get("GROUP_NAME")

# === REGEX TO PARSE MESSAGES ===
pattern = re.compile(
    r'IT(?:[\s\w\.]*?-\s*)([\w\s\.]+?)\s+has\s+(approved|denied)\s+the\s+cancellation\s+of\s+ticket\s+([A-Z0-9\-]+)\s*\(([a-z0-9]+)\)\s*requested\s+by\s+([A-Z0-9.\-]+[A-Z0-9])',
    re.IGNORECASE
)

# --- Convert UTC to PH time ---
def ph_time(utc_dt):
    return (utc_dt + timedelta(hours=8)).strftime("%m/%d/%Y %I:%M:%S %p")

# --- Async Telegram bot ---
async def run_bot():
    while True:
        try:
            client = TelegramClient('user_session', api_id, api_hash)
            await client.start(phone)
            print("📡 Connected. Listening for messages…")

            @client.on(events.NewMessage())
            async def handler(event):
                chat = await event.get_chat()
                if getattr(chat, 'title', None) != GROUP_NAME:
                    return

                message = event.raw_text.strip()
                segments = [seg.strip() for seg in re.split(r'\n\s*\n', message) if seg.strip()]

                for seg in segments:
                    match = pattern.search(seg)
                    if not match:
                        continue

                    approver, action, ticket, refcode, booth = match.groups()

                    full_title = approver.strip()
                    cancelled_by = {
                        "Stefanie Obenza": "STEF",
                        "Michael Romo": "MIKE",
                        "Kedev": "KHEDEV",
                        "Richfield James P. Villanueva": "TROY"
                    }.get(full_title, full_title)

                    status = "APPROVED ✅" if "approved" in action.lower() else "DENIED ❌"
                    booth = booth.strip().upper()

                    # Determine area
                    if booth.startswith("R.CDO") or booth.startswith(("CDO", "CDO-PAY")):
                        area = "CDO"
                    elif booth.startswith(("R.MOW", "R.MOE", "MOW", "MOE", "MOW-PAY", "MOE-PAY")):
                        area = "MISOR"
                    else:
                        area = "Unknown"

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
                        print(f"✅ Sent: {ticket} by {cancelled_by} in {area}")
                    except Exception as e:
                        print(f"❌ Error sending webhook: {e}")

            await client.run_until_disconnected()

        except (errors.RPCError, ConnectionError, OSError) as e:
            print(f"⚠️ Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

# --- Run the bot ---
if __name__ == "__main__":
    asyncio.run(run_bot())
