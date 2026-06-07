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

# ButtonStyle safe import — works with kurigram, graceful fallback otherwise
try:
    from pyrogram.enums import ButtonStyle
    _BS = ButtonStyle
except ImportError:
    class _FakeBS:
        PRIMARY = SUCCESS = DANGER = None
    _BS = _FakeBS()

# ── ᴄᴏɴꜰɪɢ ───────────────────────────────────────────────────────
API_ID     = int(os.environ.get("API_ID",     "20898349"))
API_HASH   = os.environ.get("API_HASH",       "9fdb830d1e435b785f536247f49e7d87")
BOT_TOKEN  = os.environ.get("BOT_TOKEN",      "8914464180:AAEv2dZH1b34CsDowDF0wrFU5HP4YqjFtiQ")
CHANNEL_ID = os.environ.get("CHANNEL_ID",     "@sxypndu")
MASTER_KEY = os.environ.get("MASTER_KEY",     "YukiMasterAdmin2026")
API_BASE   = os.environ.get("API_BASE",       "https://pandaapiv2.up.railway.app")
LOG_GROUP  = os.environ.get("LOG_GROUP",      "-1002564592666")
IMG_START  = os.environ.get("IMG_START",      "https://files.catbox.moe/bd3cqo.jpg")

bot = Client("L", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── sᴇssɪᴏɴ + ᴄᴀᴄʜᴇ ──────────────────────────────────────────────
_sessions: dict = {}
SESSION_TTL = 3600

def _get_sess(uid):
    s = _sessions.get(uid)
    return s if s and time.time()-s["ts"] < SESSION_TTL else None

def _set_sess(uid, cookie, username):
    _sessions[uid] = {"cookie": cookie, "username": username, "ts": time.time()}

def _del_sess(uid):
    _sessions.pop(uid, None)

_pending: dict = {}
_reg_data: dict = {}

# ── ᴠᴇʀɪꜰɪᴇᴅ ᴜsᴇʀs ── channel join confirmed users ──────────────
_verified: set = set()

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
    except:
        return False  # doubt = not joined

async def log_user(client, user):
    global known_users
    if user.id not in known_users:
        known_users.add(user.id); save_users(known_users)
        un = f"@{user.username}" if user.username else "ɴ/ᴀ"
        if LOG_GROUP:
            try:
                await client.send_message(LOG_GROUP,
                    f"**ɴᴇᴡ ᴜsᴇʀ** 🚀\n\n"
                    f"**ɴᴀᴍᴇ:** [{user.first_name}](tg://user?id={user.id})\n"
                    f"**ɪᴅ:** `{user.id}`\n**ᴜsᴇʀɴᴀᴍᴇ:** {un}\n"
                    f"**ᴛᴏᴛᴀʟ:** `{len(known_users)}`",
                    disable_web_page_preview=True)
            except: pass

# ── ᴋᴇʏʙᴏᴀʀᴅs ────────────────────────────────────────────────────
def _btn(text, **kwargs):
    """InlineKeyboardButton wrapper — style ignored if not supported"""
    style = kwargs.pop("style", None)
    if style is not None:
        try:
            return InlineKeyboardButton(text, style=style, **kwargs)
        except TypeError:
            pass
    return InlineKeyboardButton(text, **kwargs)

def join_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📢 ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
        InlineKeyboardButton("✅ ᴠᴇʀɪꜰʏ", callback_data="check_join")
    ]])

def auth_kb():
    return InlineKeyboardMarkup([[
        _btn("🔐 ʟᴏɢɪɴ",    callback_data="do_login",    style=_BS.PRIMARY),
        _btn("📝 ʀᴇɢɪsᴛᴇʀ", callback_data="do_register", style=_BS.SUCCESS),
    ]])

def main_kb():
    return InlineKeyboardMarkup([
        [
            _btn("🔑 ᴍʏ ᴋᴇʏs", callback_data="my_keys",    style=_BS.PRIMARY),
            _btn("📈 ᴜsᴀɢᴇ",   callback_data="my_usage",   style=_BS.PRIMARY),
        ],
        [
            _btn("➕ ɴᴇᴡ ᴋᴇʏ", callback_data="gen_key",    style=_BS.SUCCESS),
            _btn("🏓 ᴘɪɴɢ",    callback_data="ping",       style=_BS.PRIMARY),
        ],
        [
            _btn("💳 ᴜᴘɢʀᴀᴅᴇ", callback_data="plans",      style=_BS.SUCCESS),
            _btn("📜 ʜɪsᴛᴏʀʏ", callback_data="pay_history", style=_BS.PRIMARY),
        ],
        [
            InlineKeyboardButton("🌐 ᴡᴇʙ ᴅᴀsʜʙᴏᴀʀᴅ", web_app=WebAppInfo(url=f"{API_BASE}")),
        ],
        [
            _btn("🚪 ʟᴏɢᴏᴜᴛ", callback_data="logout", style=_BS.DANGER),
        ]
    ])

def back_kb(cb="main_menu"):
    return InlineKeyboardMarkup([[_btn("🏠 ʙᴀᴄᴋ", callback_data=cb, style=_BS.PRIMARY)]])

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

# ══════════════════════════════════════════════════════════════════
#  ✅ GATE — har callback ke top pe call karo
# ══════════════════════════════════════════════════════════════════
async def gate(client, cb: CallbackQuery) -> bool:
    uid = cb.from_user.id
    # Step 1: _verified mein hai?
    if uid not in _verified:
        await cb.answer(
            "⚠️ ᴘʜᴇʟᴇ ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴ ᴋᴀʀᴏ!\n📢 Join karke ✅ Verify dabao.",
            show_alert=True
        )
        try:
            await cb.message.edit_caption(
                f"**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n"
                f"❌ **ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴ ʀᴇQᴜɪʀᴇᴅ!**\n\n"
                f"📢 ʜᴀᴍᴀʀᴀ ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴ ᴋᴀʀᴏ ᴀᴜʀ ✅ ᴠᴇʀɪꜰʏ ᴋʀᴏ.",
                reply_markup=join_kb()
            )
        except: pass
        return False
    # Step 2: verified tha lekin actually chhod diya?
    if not await check_joined(client, uid):
        _verified.discard(uid)
        await cb.answer(
            "⚠️ ᴀᴘɴᴇ ᴄʜᴀɴɴᴇʟ ᴄʜʜᴏᴅ ᴅɪʏᴀ!\n📢 Wapas join karke verify karo.",
            show_alert=True
        )
        try:
            await cb.message.edit_caption(
                f"**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n"
                f"❌ **ᴄʜᴀɴɴᴇʟ ʟᴇꜰᴛ ᴅᴇᴛᴇᴄᴛᴇᴅ!**\n\n"
                f"📢 Wapas join karo aur ✅ Verify karo.",
                reply_markup=join_kb()
            )
        except: pass
        return False
    return True

# ── /sᴛᴀʀᴛ ───────────────────────────────────────────────────────
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message: Message):
    user = message.from_user
    await log_user(client, user)

    # _verified check — hamesha join screen pehle
    if user.id not in _verified:
        await message.reply_photo(IMG_START,
            caption=(
                f"**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n"
                f"👋 ʜᴇʟʟᴏ {user.mention}!\n\n"
                f"📢 ʙᴏᴛ ɪsᴛᴇᴍᴀᴀʟ ᴋᴀʀɴᴇ ᴋᴇ ʟɪʏᴇ ᴘᴇʜʟᴇ\n"
                f"ʜᴀᴍᴀʀᴀ ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴ ᴋᴀʀᴏ! 👇"
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

# ── ✅ ᴄʜᴇᴄᴋ ᴊᴏɪɴ ────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("check_join"))
async def check_join_cb(client, cb: CallbackQuery):
    uid = cb.from_user.id
    if not await check_joined(client, uid):
        await cb.answer("❌ ᴀʙʜɪ ᴛᴀᴋ ᴊᴏɪɴ ɴᴀʜɪ ᴋɪʏᴀ! Pehle join karo.", show_alert=True)
        return
    _verified.add(uid)  # ✅ ab allowed
    await cb.answer("✅ ᴠᴇʀɪꜰɪᴇᴅ!")
    sess = _get_sess(uid)
    if sess:
        await cb.message.edit_caption(main_caption(cb.from_user, sess["username"]), reply_markup=main_kb())
    else:
        await cb.message.edit_caption(
            f"**⚡ ᴀʀᴜ ʏᴛ ᴀᴘɪ ʙᴏᴛ**\n\n🔐 ʟᴏɢɪɴ ᴏʀ 📝 ʀᴇɢɪsᴛᴇʀ",
            reply_markup=auth_kb())

# ── 🔐 ʟᴏɢɪɴ ꜰʟᴏᴡ ────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("do_login"))
async def do_login_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
    await cb.answer()
    _pending[cb.from_user.id] = "login_username"
    await cb.message.edit_caption(
        "**🔐 ʟᴏɢɪɴ**\n\n✏️ sᴇɴᴅ ʏᴏᴜʀ **ᴜsᴇʀɴᴀᴍᴇ**:",
        reply_markup=back_kb("cancel_input"))

@bot.on_callback_query(filters.regex("do_register"))
async def do_register_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
    await cb.answer()
    _pending[cb.from_user.id] = "reg_username"
    _reg_data[cb.from_user.id] = {}
    await cb.message.edit_caption(
        "**📝 ʀᴇɢɪsᴛᴇʀ**\n\n✏️ sᴇɴᴅ ʏᴏᴜʀ **ᴜsᴇʀɴᴀᴍᴇ**:",
        reply_markup=back_kb("cancel_input"))

@bot.on_callback_query(filters.regex("cancel_input"))
async def cancel_input(client, cb: CallbackQuery):
    if not await gate(client, cb): return
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

    if uid not in _verified:
        _pending.pop(uid, None); _reg_data.pop(uid, None)
        await message.reply(
            "**❌ ᴄʜᴀɴɴᴇʟ ᴊᴏɪɴ ʀᴇQᴜɪʀᴇᴅ!**\n\n📢 /start → join → verify",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 ᴊᴏɪɴ", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"),
            ]]))
        return

    text = message.text.strip()

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
            await m.edit_text(f"**✅ ʟᴏɢɪɴ sᴜᴄᴄᴇssꜰᴜʟ!**\n\n👤 `{uname}`\n\nᴜsᴇ /start ᴛᴏ ᴏᴘᴇɴ ᴍᴇɴᴜ.")
        else:
            err = d.get("detail") or d.get("error") or "ɪɴᴠᴀʟɪᴅ ᴄʀᴇᴅᴇɴᴛɪᴀʟs"
            await m.edit_text(f"**❌ ʟᴏɢɪɴ ꜰᴀɪʟᴇᴅ**\n\n`{err}`\n\n/start ᴛᴏ ʀᴇᴛʀʏ")

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
                f"**✅ ʀᴇɢɪsᴛᴇʀᴇᴅ!**\n\n👤 `{r['username']}`\n"
                f"🔑 ᴀ ꜰʀᴇᴇ ᴋᴇʏ ʜᴀs ʙᴇᴇɴ ᴄʀᴇᴀᴛᴇᴅ!\n\nᴜsᴇ /start ᴛᴏ ᴏᴘᴇɴ ᴍᴇɴᴜ.")
        else:
            err = d.get("detail") or d.get("error") or "ʀᴇɢɪsᴛʀᴀᴛɪᴏɴ ꜰᴀɪʟᴇᴅ"
            await m.edit_text(f"**❌ ꜰᴀɪʟᴇᴅ**\n\n`{err}`\n\n/start ᴛᴏ ʀᴇᴛʀʏ")

# ── 🏠 ᴍᴀɪɴ ᴍᴇɴᴜ ─────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("main_menu"))
async def main_menu_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption(main_caption(cb.from_user, sess["username"]), reply_markup=main_kb())

# ── 🔑 ᴍʏ ᴋᴇʏs ───────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("my_keys"))
async def my_keys_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption("**⏳ ʟᴏᴀᴅɪɴɢ...**")
    d, status = await api_get("/api/keys", cookie=sess["cookie"])
    keys = d.get("keys", [])
    if not keys:
        await cb.message.edit_caption(
            "**🔑 ɴᴏ ᴋᴇʏs ʏᴇᴛ**\n\nᴜsᴇ ➕ ɴᴇᴡ ᴋᴇʏ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ ɴᴇᴡ ᴋᴇʏ", callback_data="gen_key"),
                InlineKeyboardButton("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
            ]])); return
    text = "**🔑 ʏᴏᴜʀ ᴀᴘɪ ᴋᴇʏs**\n\n"
    for k in keys:
        si = "✅" if k.get("active") else "🔴"
        text += (
            f"{si} `{k['key']}`\n"
            f"   **ᴘʟᴀɴ:** {k.get('plan_name','Free')} | "
            f"**ᴛᴏᴅᴀʏ:** {k.get('today_uses',0)} | "
            f"**ʟɪᴍɪᴛ:** {'∞' if k.get('plan_limit',-1)==-1 else k.get('plan_limit',100)}\n\n"
        )
    await cb.message.edit_caption(text, reply_markup=back_kb())

# ── 📈 ᴜsᴀɢᴇ ──────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("my_usage"))
async def my_usage_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption("**⏳ ꜰᴇᴛᴄʜɪɴɢ...**")
    d, _ = await api_get("/api/dashboard", cookie=sess["cookie"])
    keys = d.get("keys", [])
    if not keys:
        await cb.message.edit_caption("**❌ ɴᴏ ᴋᴇʏs ꜰᴏᴜɴᴅ!**", reply_markup=back_kb()); return
    today_total = sum(k.get("today_uses",0) for k in keys)
    today_audio = sum(k.get("today_audio",0) for k in keys)
    today_video = sum(k.get("today_video",0) for k in keys)
    all_total   = sum((k.get("alltime") or {}).get("total",0) for k in keys)
    all_audio   = sum((k.get("alltime") or {}).get("audio",0) for k in keys)
    all_video   = sum((k.get("alltime") or {}).get("video",0) for k in keys)
    await cb.message.edit_caption(
        f"**📈 ʏᴏᴜʀ ᴜsᴀɢᴇ sᴛᴀᴛs**\n\n"
        f"╔══════════════════╗\n║      ᴛᴏᴅᴀʏ       ║\n╠══════════════════╣\n"
        f"║ 📊 ʀᴇQᴜᴇsᴛs : `{today_total}`\n║ 🎵 ᴀᴜᴅɪᴏ   : `{today_audio}`\n║ 🎬 ᴠɪᴅᴇᴏ   : `{today_video}`\n"
        f"╠══════════════════╣\n║    ᴀʟʟ-ᴛɪᴍᴇ      ║\n╠══════════════════╣\n"
        f"║ 📊 ᴛᴏᴛᴀʟ   : `{all_total}`\n║ 🎵 ᴀᴜᴅɪᴏ   : `{all_audio}`\n║ 🎬 ᴠɪᴅᴇᴏ   : `{all_video}`\n╚══════════════════╝",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 ʀᴇꜰʀᴇsʜ", callback_data="my_usage"),
            InlineKeyboardButton("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
        ]]))

# ── ➕ ɢᴇɴᴇʀᴀᴛᴇ ᴋᴇʏ ──────────────────────────────────────────────
@bot.on_callback_query(filters.regex("gen_key"))
async def gen_key_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
    await cb.answer()
    sess = _get_sess(cb.from_user.id)
    if not sess:
        await cb.message.edit_caption("**🔐 ʟᴏɢɪɴ ʀᴇQᴜɪʀᴇᴅ**", reply_markup=auth_kb()); return
    await cb.message.edit_caption("**⏳ ɢᴇɴᴇʀᴀᴛɪɴɢ...**")
    d, status, _ = await api_post("/api/keys/generate", {"plan_id": 1}, cookie=sess["cookie"])
    if d.get("success"):
        await cb.message.edit_caption(
            f"**✅ ɴᴇᴡ ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ!**\n\n🔑 **ᴋᴇʏ:**\n`{d['key']}`\n\n"
            f"📋 ᴘʟᴀɴ: **Free** | ʟɪᴍɪᴛ: **100/day**\n\n⚠️ ᴜsᴇ ᴀs `SHRUTI_API_KEY` ɪɴ ʙᴏᴛ",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔑 ᴍʏ ᴋᴇʏs", callback_data="my_keys"),
                InlineKeyboardButton("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
            ]]))
    else:
        err = d.get("detail") or d.get("error") or "ꜰᴀɪʟᴇᴅ"
        await cb.message.edit_caption(f"**❌ {err}**", reply_markup=back_kb())

# ── 💳 ᴘʟᴀɴs ──────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("^plans$"))
async def plans_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
    await cb.answer()
    d, _ = await api_get("/api/payment/plans")
    plans = d.get("plans", [])
    upi   = d.get("upi_id", "N/A")
    text  = "**💳 ᴀᴠᴀɪʟᴀʙʟᴇ ᴘʟᴀɴs**\n\n"
    for p in plans:
        limit = "Unlimited" if p.get("req_limit",-1)==-1 else f"{p['req_limit']}/day"
        price = "Free" if p["price"]==0 else f"₹{p['price']}/mo"
        text += f"**{p['name']}** — {price}\n📊 {limit}\n📝 {p.get('description','')}\n\n"
    text += f"**UPI:** `{upi}`\n\n💡 ᴜsᴇ ᴡᴇʙ ᴅᴀsʜʙᴏᴀʀᴅ ᴛᴏ ᴜᴘɢʀᴀᴅᴇ"
    await cb.message.edit_caption(text, reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("🌐 ᴏᴘᴇɴ ᴅᴀsʜʙᴏᴀʀᴅ", web_app=WebAppInfo(url=f"{API_BASE}")),
    ],[
        InlineKeyboardButton("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
    ]]))

# ── 📜 ᴘᴀʏᴍᴇɴᴛ ʜɪsᴛᴏʀʏ ─────────────────────────────────────────
@bot.on_callback_query(filters.regex("pay_history"))
async def pay_history_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
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
    if not await gate(client, cb): return
    await cb.answer()
    t = time.time()
    d, _ = await api_get("/ping")
    ms = round((time.time()-t)*1000)
    uptime = d.get("uptime",0)
    h,m = int(uptime)//3600, (int(uptime)%3600)//60
    status = "🟢 ᴇxᴄᴇʟʟᴇɴᴛ" if ms<200 else "🟡 ɢᴏᴏᴅ" if ms<500 else "🔴 sʟᴏᴡ"
    await cb.message.edit_caption(
        f"**🏓 ᴘᴏɴɢ!**\n\n╔══════════════════╗\n║   ᴀᴘɪ sᴛᴀᴛᴜs    ║\n╠══════════════════╣\n"
        f"║ ⚡ ʟᴀᴛᴇɴᴄʏ : `{ms}ms`\n║ 🕐 ᴜᴘᴛɪᴍᴇ  : `{h}ʜ {m}ᴍ`\n║ 📶 sᴛᴀᴛᴜs  : {status}\n╚══════════════════╝",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 ʀᴇꜰʀᴇsʜ", callback_data="ping"),
            InlineKeyboardButton("🏠 ʙᴀᴄᴋ", callback_data="main_menu"),
        ]]))

# ── 🚪 ʟᴏɢᴏᴜᴛ ─────────────────────────────────────────────────────
@bot.on_callback_query(filters.regex("^logout$"))
async def logout_cb(client, cb: CallbackQuery):
    if not await gate(client, cb): return
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
