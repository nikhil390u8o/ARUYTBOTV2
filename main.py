# ================================================================
#  ᴀʀᴜ ʏᴛ ᴀᴘɪ — ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ v2
#  ᴅᴇᴠ: ᴘᴀɴᴅᴀ-ʙᴀʙʏ | sᴜᴘᴘᴏʀᴛ: @sxypndu
#  endpoints: new dashboard API (/api/*)
# ================================================================

import os, time, json, asyncio, aiohttp
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery, WebAppInfo
)
try:
    from pyrogram.enums import ButtonStyle
    _PRIMARY = ButtonStyle.PRIMARY
    _SUCCESS = ButtonStyle.SUCCESS
    _DANGER  = ButtonStyle.DANGER
except (ImportError, AttributeError):
    try:
        from pyrogram.types import ButtonStyle
        _PRIMARY = ButtonStyle.PRIMARY
        _SUCCESS = ButtonStyle.SUCCESS
        _DANGER  = ButtonStyle.DANGER
    except (ImportError, AttributeError):
        _PRIMARY = _SUCCESS = _DANGER = None

def btn(text, callback_data=None, url=None, web_app=None, style=None):
    kwargs = {"text": text}
    if callback_data: kwargs["callback_data"] = callback_data
    if url: kwargs["url"] = url
    if web_app: kwargs["web_app"] = web_app
    if style is not None: kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)

# ── ᴄᴏɴꜰɪɢ ───────────────────────────────────────────────────────
API_ID     = int(os.environ.get("API_ID",     "20898349"))
API_HASH   = os.environ.get("API_HASH",       "9fdb830d1e435b785f536247f49e7d87")
BOT_TOKEN  = os.environ.get("BOT_TOKEN",      "8808019830:AAFwOYjpCNGmY_om3vJ9Q0jpe34n6QAN-zA")
CHANNEL_ID = os.environ.get("CHANNEL_ID",     "@sxypndu")
MASTER_KEY = os.environ.get("MASTER_KEY",     "YukiMasterAdmin2026")
API_BASE   = os.environ.get("API_BASE",       "https://pandaapiv2.up.railway.app")
LOG_GROUP  = os.environ.get("LOG_GROUP",      "-1003468477782")
IMG_START  = os.environ.get("IMG_START",      "https://files.catbox.moe/bd3cqo.jpg")

bot = Client("ARUAPIBotV2", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── sᴇssɪᴏɴ + ᴄᴀᴄʜᴇ ──────────────────────────────────────────────
SESSIONS_FILE = "sessions.json"
SESSION_TTL = 86400 * 7  # 7 days

def _load_sessions():
    try:
        with open(SESSIONS_FILE) as f: return json.load(f)
    except: return {}

def _save_sessions(s):
    try:
        with open(SESSIONS_FILE, "w") as f: json.dump(s, f)
    except: pass

_sessions: dict = _load_sessions()

def _get_sess(uid):
    s = _sessions.get(str(uid))
    if s and time.time() - s.get("ts", 0) < SESSION_TTL:
        return s
    if s:
        _sessions.pop(str(uid), None); _save_sessions(_sessions)
    return None

def _set_sess(uid, cookie, username):
    _sessions[str(uid)] = {"cookie": cookie, "username": username, "ts": time.time()}
    _save_sessions(_sessions)

def _del_sess(uid):
    _sessions.pop(str(uid), None)
    _save_sessions(_sessions)

# Pending login state: {uid: "awaiting_username" | "awaiting_password" | "awaiting_register_*"}
_pending: dict = {}
_reg_data: dict = {}  # {uid: {username, email}}

# ── ᴜsᴇʀs ʟᴏɢ ────────────────────────────────────────────────────
USERS_FILE = "users.json"
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f: return set(json.load(f))
    return set()
def save_users(u):
    with open(USERS_FILE,"w") as f: json.dump(list(u),f)
known_users = load_users()

# ── ʜᴛᴛᴘ ──────────────────────────────────────────────────────────
_http: aiohttp.ClientSession = None

async def _sess():
    global _http
    if _http is None or _http.closed:
        _http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
    return _http

async def api_get(endpoint, params=None, cookie=None):
    s = await _sess()
    h = {"Cookie": f"session={cookie}"} if cookie else {}
    try:
        async with s.get(f"{API_BASE}{endpoint}", params=params, headers=h) as r:
            return await r.json(), r.status
    except Exception as e:
        return {"error": str(e)}, 0

async def api_post(endpoint, body=None, cookie=None):
    s = await _sess()
    h = {"Content-Type":"application/json"}
    if cookie: h["Cookie"] = f"session={cookie}"
    try:
        async with s.post(f"{API_BASE}{endpoint}", json=body or {}, headers=h) as r:
            # extract Set-Cookie if login
            new_cookie = None
            raw = r.headers.get("set-cookie","")
            if "session=" in raw:
                new_cookie = raw.split("session=")[1].split(";")[0]
            return await r.json(), r.status, new_cookie
    except Exception as e:
        return {"error": str(e)}, 0, None

# ── ʜᴇʟᴘᴇʀs ──────────────────────────────────────────────────────
async def check_joined(client, uid):
    try:
        m = await client.get_chat_member(CHANNEL_ID, uid)
        return m.status.name not in ["LEFT","BANNED","RESTRICTED"]
    except Exception as e:
        print(f"[JOIN CHECK ERROR] {e}")
        return False

async def log_user(client, user):
    global known_users
    print(f"[LOG] user {user.id} | known: {user.id in known_users}")
    if user.id not in known_users:
        known_users.add(user.id); save_users(known_users)
        un = f"@{user.username}" if user.username else "ɴ/ᴀ"
        if LOG_GROUP:
            try:
                await client.send_message(int(LOG_GROUP),
                    f"**ɴᴇᴡ ᴜsᴇʀ** 🚀\n\n"
                    f"**ɴᴀᴍᴇ:** [{user.first_name}](tg://user?id={user.id})\n"
                    f"**ɪᴅ:** `{user.id}`\n**ᴜsᴇʀɴᴀᴍᴇ:** {un}\n"
                    f"**ᴛᴏᴛᴀʟ:** `{len(known_users)}`",
                    disable_web_page_preview=True)
                print(f"[LOG] sent to group ✅")
            except Exception as e:
                print(f"[LOG ERROR] {e}")

def join_kb():
    return InlineKeyboardMarkup([[
        btn("📢 ᴊᴏɪɴ", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
        btn("✅ ɪ ᴊᴏɪɴᴇᴅ", callback_data="check_join", style=_SUCCESS)
    ]])

def auth_kb():
    return InlineKeyboardMarkup([[
        btn("🔐 ʟᴏɢɪɴ", callback_data="do_login", style=_PRIMARY),
        btn("📝 ʀᴇɢɪsᴛᴇʀ", callback_data="do_register", style=_SUCCESS),
    ]])

def main_kb():
    return InlineKeyboardMarkup([
        [
            btn("🔑 ᴍʏ ᴋᴇʏs", callback_data="my_keys", style=_PRIMARY),
            btn("📈 ᴜsᴀɢᴇ", callback_data="my_usage", style=_PRIMARY),
        ],
        [
            btn("➕ ɴᴇᴡ ᴋᴇʏ", callback_data="gen_key", style=_SUCCESS),
            btn("🏓 ᴘɪɴɢ", callback_data="ping", style=_PRIMARY),
        ],
        [
            btn("💳 ᴜᴘɢʀᴀᴅᴇ", callback_data="plans", style=_SUCCESS),
            btn("📜 ʜɪsᴛᴏʀʏ", callback_data="pay_history", style=_PRIMARY),
        ],
        [
            btn("🌐 ᴡᴇʙ ᴅᴀsʜʙᴏᴀʀᴅ", web_app=WebAppInfo(url=f"{API_BASE}")),
        ],
        [
            btn("🚪 ʟᴏɢᴏᴜᴛ", callback_data="logout", style=_DANGER),
        ]
    ])

def back_kb(cb="main_menu"):
    return InlineKeyboardMarkup([[btn("🏠 ʙᴀᴄᴋ", callback_data=cb, style=_PRIMARY)]])

def main_caption(user, uname):
    return (
        f"**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n"
        f"╔══════════════════╗\n"
        f"║  ʜᴇʟʟᴏ, {user.first_name[:10]}\n"
        f"╚══════════════════╝\n\n"
        f"👤 **ᴀᴄᴄᴏᴜɴᴛ:** `{uname}`\n"
        f"🌐 `{API_BASE}`\n\n"
        f"**ᴅᴇᴠ:** ᴘᴀɴᴅᴀ-ʙᴀʙʏ | @sxypndu"
    )

async def require_joined(client, cb: CallbackQuery) -> bool:
    """Returns True if joined, else shows alert and returns False"""
    if not await check_joined(client, cb.from_user.id):
        await cb.answer(
            "📢 ᴘʜᴇʟᴇ ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴ ᴋᴀʀᴏ!\nhttps://t.me/" + CHANNEL_ID.lstrip('@'),
            show_alert=True
        )
        return False
    return True

# ── /sᴛᴀʀᴛ ───────────────────────────────────────────────────────
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    user = message.from_user
    await log_user(client, user)
    joined = await check_joined(client, user.id)
    if not joined:
        await message.reply_photo(IMG_START,
            caption=(
                f"**⚡ ᴡᴇʟᴄᴏᴍᴇ, {user.mention}!**\n\n"
                f"╔══════════════════╗\n"
                f"║  ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ  ║\n"
                f"╚══════════════════╝\n\n"
                f"📢 ᴘʜᴇʟᴇ ʜᴀᴍᴀʀᴀ ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴ ᴋᴀʀᴏ\n"
                f"ꜰɪʀ **✅ ɪ ᴊᴏɪɴᴇᴅ** ᴅᴀʙᴀᴏ"
            ),
            reply_markup=join_kb())
        return

    sess = _get_sess(user.id)
    if sess:
        await message.reply_photo(IMG_START,
            caption=main_caption(user, sess["username"]),
            reply_markup=main_kb())
    else:
        await message.reply_photo(IMG_START,
            caption=(
                f"**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n"
                f"╔══════════════════╗\n"
                f"║  ʜᴇʟʟᴏ, {user.first_name[:10]}\n"
                f"╚══════════════════╝\n\n"
                f"🔐 ʟᴏɢɪɴ ᴏʀ 📝 ʀᴇɢɪsᴛᴇʀ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ\n\n"
                f"**ᴅᴇᴠ:** ᴘᴀɴᴅᴀ-ʙᴀʙʏ | @sxypndu"
            ),
            reply_markup=auth_kb())

# ── ᴄʜᴇᴄᴋ ᴊᴏɪɴ ───────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("check_join"))
async def check_join_cb(client, cb: CallbackQuery):
    if not await check_joined(client, cb.from_user.id):
        await cb.answer("❌ ᴀʙʜɪ ᴛᴀᴋ ᴊᴏɪɴ ɴᴀʜɪ ᴋɪʏᴀ!", show_alert=True); return
    await cb.answer("✅ ᴠᴇʀɪꜰɪᴇᴅ!")
    sess = _get_sess(cb.from_user.id)
    if sess:
        await cb.message.edit_caption(main_caption(cb.from_user, sess["username"]), reply_markup=main_kb())
    else:
        await cb.message.edit_caption(
            f"**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n🔐 ʟᴏɢɪɴ ᴏʀ 📝 ʀᴇɢɪsᴛᴇʀ",
            reply_markup=auth_kb())

# ── ʟᴏɢɪɴ ꜰʟᴏᴡ ───────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("do_login"))
async def do_login_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    _pending[cb.from_user.id] = "login_username"
    await cb.message.edit_caption(
        "**🔐 ʟᴏɢɪɴ**\n\n✏️ sᴇɴᴅ ʏᴏᴜʀ **ᴜsᴇʀɴᴀᴍᴇ**:",
        reply_markup=back_kb("cancel_input"))

@bot.on_callback_query(filters.regex("do_register"))
async def do_register_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    _pending[cb.from_user.id] = "reg_username"
    _reg_data[cb.from_user.id] = {}
    await cb.message.edit_caption(
        "**📝 ʀᴇɢɪsᴛᴇʀ**\n\n✏️ sᴇɴᴅ ʏᴏᴜʀ **ᴜsᴇʀɴᴀᴍᴇ**:",
        reply_markup=back_kb("cancel_input"))

@bot.on_callback_query(filters.regex("cancel_input"))
async def cancel_input(client, cb: CallbackQuery):
    await cb.answer()
    _pending.pop(cb.from_user.id, None)
    _reg_data.pop(cb.from_user.id, None)
    await cb.message.edit_caption(
        "**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n🔐 ʟᴏɢɪɴ ᴏʀ 📝 ʀᴇɢɪsᴛᴇʀ",
        reply_markup=auth_kb())

# ── ᴛᴇxᴛ ɪɴᴘᴜᴛ ʜᴀɴᴅʟᴇʀ ───────────────────────────────────────────
@bot.on_message(filters.private & filters.text & ~filters.command(["start","stats","mykey"]))
async def text_handler(client, message: Message):
    uid  = message.from_user.id
    step = _pending.get(uid)
    if not step: return
    text = message.text.strip()

    # ── LOGIN FLOW ──
    if step == "login_username":
        _reg_data[uid] = {"username": text}
        _pending[uid] = "login_password"
        await message.reply("✏️ sᴇɴᴅ ʏᴏᴜʀ **ᴘᴀssᴡᴏʀᴅ**:")

    elif step == "login_password":
        uname = _reg_data.get(uid,{}).get("username","")
        _pending.pop(uid, None); _reg_data.pop(uid, None)
        m = await message.reply("**⏳ ʟᴏɢɢɪɴɢ ɪɴ...**")
        d, status, cookie = await api_post("/api/login", {"username": uname, "password": text})
        if d.get("success") and cookie:
            _set_sess(uid, cookie, uname)
            await m.edit_text(
                f"**✅ ʟᴏɢɪɴ sᴜᴄᴄᴇssꜰᴜʟ!**\n\n"
                f"👤 `{uname}`\n\n"
                f"ᴜsᴇ /start ᴛᴏ ᴏᴘᴇɴ ᴍᴇɴᴜ.")
        else:
            err = d.get("detail") or d.get("error") or "ɪɴᴠᴀʟɪᴅ ᴄʀᴇᴅᴇɴᴛɪᴀʟs"
            await m.edit_text(f"**❌ ʟᴏɢɪɴ ꜰᴀɪʟᴇᴅ**\n\n`{err}`\n\n/start ᴛᴏ ʀᴇᴛʀʏ")

    # ── REGISTER FLOW ──
    elif step == "reg_username":
        _reg_data[uid]["username"] = text
        _pending[uid] = "reg_email"
        await message.reply("✏️ sᴇɴᴅ ʏᴏᴜʀ **ᴇᴍᴀɪʟ**:")

    elif step == "reg_email":
        _reg_data[uid]["email"] = text
        _pending[uid] = "reg_password"
        await message.reply("✏️ sᴇɴᴅ ʏᴏᴜʀ **ᴘᴀssᴡᴏʀᴅ** (min 6 chars):")

    elif step == "reg_password":
        r = _reg_data.get(uid,{})
        _pending.pop(uid, None); _reg_data.pop(uid, None)
        m = await message.reply("**⏳ ᴄʀᴇᴀᴛɪɴɢ ᴀᴄᴄᴏᴜɴᴛ...**")
        d, status, cookie = await api_post("/api/register", {
            "username": r.get("username",""),
            "email":    r.get("email",""),
            "password": text
        })
        if d.get("success") and cookie:
            _set_sess(uid, cookie, r["username"])
            await m.edit_text(
                f"**✅ ʀᴇɢɪsᴛᴇʀᴇᴅ!**\n\n"
                f"👤 `{r['username']}`\n"
                f"🔑 ᴀ ꜰʀᴇᴇ ᴋᴇʏ ʜᴀs ʙᴇᴇɴ ᴄʀᴇᴀᴛᴇᴅ!\n\n"
                f"ᴜsᴇ /start ᴛᴏ ᴏᴘᴇɴ ᴍᴇɴᴜ.")
        else:
            err = d.get("detail") or d.get("error") or "ʀᴇɢɪsᴛʀᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ"
            await m.edit_text(f"**❌ ꜰᴀɪʟᴇᴅ**\n\n`{err}`\n\n/start ᴛᴏ ʀᴇᴛʀʏ")

# ── ᴍᴀɪɴ ᴍᴇɴᴜ ────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("main_menu"))
async def main_menu_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption(main_caption(cb.from_user, sess["username"]), reply_markup=main_kb())

# ── 🔑 ᴍʏ ᴋᴇʏs ───────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("my_keys"))
async def my_keys_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption("**⏳ ʟᴏᴀᴅɪɴɢ...**")
    d, status = await api_get("/api/dashboard", cookie=sess["cookie"])
    keys = d.get("keys", [])
    if not keys:
        await cb.message.edit_caption(
            "**🔑 ɴᴏ ᴋᴇʏs ʏᴇᴛ**\n\nᴜsᴇ ➕ ɴᴇᴡ ᴋᴇʏ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ!",
            reply_markup=InlineKeyboardMarkup([[
                btn("➕ ɴᴇᴡ ᴋᴇʏ", callback_data="gen_key"),
                btn("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
            ]])); return
    text = "**🔑 ʏᴏᴜʀ ᴀᴘɪ ᴋᴇʏs**\n\n"
    for k in keys:
        status_icon = "✅" if k.get("active") else "🔴"
        text += (
            f"{status_icon} `{k['key']}`\n"
            f"   **ᴘʟᴀɴ:** {k.get('plan_name','Free')} | "
            f"**ᴛᴏᴅᴀʏ:** {k.get('today_uses',0)} | "
            f"**ʟɪᴍɪᴛ:** {'∞' if k.get('plan_limit',-1)==-1 else k.get('plan_limit',100)}\n\n"
        )
    await cb.message.edit_caption(text, reply_markup=back_kb())

# ── 📈 ᴜsᴀɢᴇ ──────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("my_usage"))
async def my_usage_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption("**⏳ ꜰᴇᴛᴄʜɪɴɢ...**")
    d, _ = await api_get("/api/dashboard", cookie=sess["cookie"])
    keys = d.get("keys", [])
    if not keys:
        await cb.message.edit_caption("**❌ ɴᴏ ᴋᴇʏs ꜰᴏᴜɴᴅ!**", reply_markup=back_kb()); return
    today_total  = sum(k.get("today_uses",0) for k in keys)
    today_audio  = sum(k.get("today_audio",0) for k in keys)
    today_video  = sum(k.get("today_video",0) for k in keys)
    all_total    = sum((k.get("alltime") or {}).get("total",0) for k in keys)
    all_audio    = sum((k.get("alltime") or {}).get("audio",0) for k in keys)
    all_video    = sum((k.get("alltime") or {}).get("video",0) for k in keys)
    await cb.message.edit_caption(
        f"**📈 ʏᴏᴜʀ ᴜsᴀɢᴇ sᴛᴀᴛs**\n\n"
        f"╔══════════════════╗\n"
        f"║      ᴛᴏᴅᴀʏ       ║\n"
        f"╠══════════════════╣\n"
        f"║ 📊 ʀᴇQᴜᴇsᴛs : `{today_total}`\n"
        f"║ 🎵 ᴀᴜᴅɪᴏ   : `{today_audio}`\n"
        f"║ 🎬 ᴠɪᴅᴇᴏ   : `{today_video}`\n"
        f"╠══════════════════╣\n"
        f"║    ᴀʟʟ-ᴛɪᴍᴇ      ║\n"
        f"╠══════════════════╣\n"
        f"║ 📊 ᴛᴏᴛᴀʟ   : `{all_total}`\n"
        f"║ 🎵 ᴀᴜᴅɪᴏ   : `{all_audio}`\n"
        f"║ 🎬 ᴠɪᴅᴇᴏ   : `{all_video}`\n"
        f"╚══════════════════╝",
        reply_markup=InlineKeyboardMarkup([[
            btn("🔄 ʀᴇꜰʀᴇsʜ", callback_data="my_usage"),
            btn("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
        ]]))

# ── ➕ ɢᴇɴᴇʀᴀᴛᴇ ᴋᴇʏ ──────────────────────────────────────────────
@bot.on_callback_query(filters.regex("gen_key"))
async def gen_key_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption("**⏳ ɢᴇɴᴇʀᴀᴛɪɴɢ...**")
    d, status, _ = await api_post("/api/keys/generate", {"plan_id": 1}, cookie=sess["cookie"])
    if d.get("success"):
        await cb.message.edit_caption(
            f"**✅ ɴᴇᴡ ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ!**\n\n"
            f"🔑 **ᴋᴇʏ:**\n`{d['key']}`\n\n"
            f"📋 ᴘʟᴀɴ: **Free** | ʟɪᴍɪᴛ: **100/day**\n\n"
            f"⚠️ ᴜsᴇ ᴀs `SHRUTI_API_KEY` ɪɴ ʙᴏᴛ",
            reply_markup=InlineKeyboardMarkup([[
                btn("🔑 ᴍʏ ᴋᴇʏs", callback_data="my_keys"),
                btn("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
            ]]))
    else:
        err = d.get("detail") or d.get("error") or "ꜰᴀɪʟᴇᴅ"
        await cb.message.edit_caption(f"**❌ {err}**", reply_markup=back_kb())

# ── 💳 ᴘʟᴀɴs ──────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("^plans$"))
async def plans_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    d, _ = await api_get("/api/payment/plans")
    plans = d.get("plans", [])
    upi   = d.get("upi_id", "N/A")
    text  = "**💳 ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʟᴀɴs**\n\n"
    for p in plans:
        limit = "Unlimited" if p.get("req_limit",-1)==-1 else f"{p['req_limit']}/day"
        price = "Free" if p["price"]==0 else f"₹{p['price']}/mo"
        text += f"**{p['name']}** — {price}\n📊 {limit}\n📝 {p.get('description','')}\n\n"
    text += f"**UPI:** `{upi}`\n\n💡 ᴜsᴇ ᴡᴇʙ ᴅᴀsʜʙᴏᴀʀᴅ ᴛᴏ ᴜᴘɢʀᴀᴅᴇ ᴡɪᴛʜ ᴘᴀʏᴍᴇɴᴛ"
    await cb.message.edit_caption(text,
        reply_markup=InlineKeyboardMarkup([[
            btn("🌐 ᴏᴘᴇɴ ᴅᴀsʜʙᴏᴀʀᴅ", web_app=WebAppInfo(url=f"{API_BASE}")),
        ],[
            btn("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
        ]]))

# ── 📜 ᴘᴀʏᴍᴇɴᴛ ʜɪsᴛᴏʀʏ ─────────────────────────────────────────
@bot.on_callback_query(filters.regex("pay_history"))
async def pay_history_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption("**⏳ ʟᴏᴀᴅɪɴɢ...**")
    d, _ = await api_get("/api/payment/history", cookie=sess["cookie"])
    history = d.get("history", [])
    if not history:
        await cb.message.edit_caption("**📜 ɴᴏ ᴘᴀʏᴍᴇɴᴛs ʏᴇᴛ**", reply_markup=back_kb()); return
    text = "**📜 ᴘᴀʏᴍᴇɴᴛ ʜɪsᴛᴏʀʏ**\n\n"
    for h in history[:5]:
        text += (
            f"✅ **{h.get('plan_name','?')} ᴘʟᴀɴ**\n"
            f"   💰 ₹{h.get('amount',0)} | 🧾 `{h.get('utr','?')}`\n"
            f"   📅 {str(h.get('created_at',''))[:10]}\n\n"
        )
    await cb.message.edit_caption(text, reply_markup=back_kb())

# ── 🏓 ᴘɪɴɢ ──────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("^ping$"))
async def ping_cb(client, cb: CallbackQuery):
    if not await require_joined(client, cb): return
    await cb.answer()
    t = time.time()
    d, _ = await api_get("/ping")
    ms = round((time.time()-t)*1000)
    uptime = d.get("uptime",0)
    h,m = int(uptime)//3600, (int(uptime)%3600)//60
    status = "🟢 ᴇxᴄᴇʟʟᴇɴᴛ" if ms<200 else "🟡 ɢᴏᴏᴅ" if ms<500 else "🔴 sʟᴏᴡ"
    await cb.message.edit_caption(
        f"**🏓 ᴘᴏɴɢ!**\n\n"
        f"╔══════════════════╗\n"
        f"║   ᴀᴘɪ sᴛᴀᴛᴜs    ║\n"
        f"╠══════════════════╣\n"
        f"║ ⚡ ʟᴀᴛᴇɴᴄʏ : `{ms}ms`\n"
        f"║ 🕐 ᴜᴘᴛɪᴍᴇ  : `{h}ʜ {m}ᴍ`\n"
        f"║ 📶 sᴛᴀᴛᴜs  : {status}\n"
        f"╚══════════════════╝",
        reply_markup=InlineKeyboardMarkup([[
            btn("🔄 ʀᴇꜰʀᴇsʜ", callback_data="ping"),
            btn("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
        ]]))

# ── 🚪 ʟᴏɢᴏᴜᴛ ─────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("^logout$"))
async def logout_cb(client, cb: CallbackQuery):
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if sess:
        await api_post("/api/logout", cookie=sess["cookie"])
    _del_sess(cb.from_user.id)
    await cb.message.edit_caption(
        "**✅ ʟᴏɢɢᴇᴅ ᴏᴜᴛ!**\n\n/start ᴛᴏ ʟᴏɢɪɴ ᴀɢᴀɪɴ",
        reply_markup=auth_kb())

# ── /sᴛᴀᴛs ───────────────────────────────────────────────────────
@bot.on_message(filters.command("stats") & filters.private)
async def stats_cmd(client, message: Message):
    d, _ = await api_get("/ping")
    await message.reply_photo(IMG_START,
        caption=(
            f"**📊 ʙᴏᴛ sᴛᴀᴛs**\n\n"
            f"👥 **ᴜsᴇʀs:** `{len(known_users)}`\n"
            f"✅ **ᴀᴘɪ:** ᴀᴄᴛɪᴠᴇ\n"
            f"⏱ **ᴜᴘᴛɪᴍᴇ:** `{int(d.get('uptime',0))//3600}h`\n\n"
            f"**ᴅᴇᴠ:** ᴘᴀɴᴅᴀ-ʙᴀʙʏ | @sxypndu"
        ))

# ── ʀᴜɴ ──────────────────────────────────────────────────────────
print("🚀 ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ v2 | ᴅᴇᴠ: ᴘᴀɴᴅᴀ-ʙᴀʙʏ")
bot.run()
