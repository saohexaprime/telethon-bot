import asyncio
import datetime
import re
import requests
from telethon import TelegramClient, events, errors
from datetime import timedelta
from keep_alive import keep_alive
import os
import signal
import sys

# --- Start the web server ---
keep_alive()

# === TELEGRAM BOT CREDENTIALS ===
api_id = int(os.environ.get("26196044"))
api_hash = os.environ.get("5c47c8a9e95d68dbe220965b9e9ce520")
phone = os.environ.get("639973584566")

# === GOOGLE APPS SCRIPT WEBHOOK URL ===
WEBHOOK_URL = os.environ.get("https://script.google.com/macros/s/AKfycbxt3n1C0srFJXxBZ0rpHWdMw_Ps8lih3HkU3DExmy-EageSW4-Ic-gBZN_zXXI979agmQ/exec")

# === GROUP NAME TO LISTEN TO ===
GROUP_NAME = os.environ.get("Hexa Tickets Cancellations")

# === REGEX TO PARSE MESSAGES ===
pattern = re.compile(
    r'IT(?:[\s\w\.]*?-\s*)([\w\s\.]+?)\s+has\s+(approved|denied)\s+the\s+cancellation\s+of\s+ticket\s+([A-Z0-9\-]+)\s*\(([a-z0-9]+)\)\s*requested\s+by\s+([A-Z0-9.\-]+[A-Z0-9])',
    re.IGNORECASE
)

# --- Helper function to convert UTC to PH time ---
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
                chat_title = getattr(chat, 'title', None)
                if chat_title != GROUP_NAME:
                    return

                message = event.raw_text.strip()
                segments = [seg.strip() for seg in re.split(r'\n\s*\n', message) if seg.strip()]

                for seg in segments:
                    match = pattern.search(seg)
                    if not match:
                        continue

                    approver, action, ticket, refcode, booth = match.groups()

                    # --- Map approvers ---
                    full_title = approver.strip()
                    cancelled_by = {
                        "Stefanie Obenza": "STEF",
                        "Michael Romo": "MIKE",
                        "Kedev": "KHEDEV",
                        "Richfield James P. Villanueva": "TROY"
                    }.get(full_title, full_title)

                    status = "APPROVED ✅" if "approved" in action.lower() else "DENIED ❌"
                    booth = booth.strip().upper()

                    # --- Determine area ---
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
                        print(f"✅ Sent to webhook ({response.status_code}): {ticket} by {cancelled_by} in {area}")
                    except Exception as e:
                        print(f"❌ Error sending to webhook: {e}")

            await client.run_until_disconnected()

        except (errors.RPCError, ConnectionError, OSError) as e:
            print(f"⚠️ Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

# --- Graceful shutdown ---
loop = asyncio.get_event_loop()

def shutdown(*args):
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.stop()
    sys.exit(0)

for sig in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(sig, shutdown)

# --- Run the bot ---
loop.run_until_complete(run_bot())
