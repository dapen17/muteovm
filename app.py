from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, timedelta, timezone
import re

tracked_users = {}

ADMIN_GROUP_ID = -1002309805544  # Grup admin
MAIN_GROUP_ID = -1002314388836   # Grup utama

def parse_duration(text: str):
    """Parse durasi dari string, misal '1d' -> 1 hari, '60' -> 60 menit"""
    pattern = r"^(\d+)([mhd])?$"
    match = re.match(pattern, text.lower())
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2) or "m"
    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    return None

async def ovm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_GROUP_ID:
        return

    if len(context.args) != 2:
        await update.message.reply_text("Gunakan: /ovm <durasi> @username\nContoh: /ovm 1d @user")
        return

    duration_str = context.args[0]
    username = context.args[1].lstrip('@').lower()

    duration = parse_duration(duration_str)
    if not duration:
        await update.message.reply_text("Format durasi salah. Gunakan contoh: 1d (1 hari), 1h (1 jam), 30 (30 menit)")
        return

    until = datetime.now(timezone.utc) + duration
    tracked_users[username] = {
        "until": until,
        "muted": False
    }

    await update.message.reply_text(
        f"✅ Tracking @{username} selama {duration_str}.\n"
        "⚠️ User akan dimute jika tidak memakai 'dont@' di nama selama 1 hari kedepan."
    )

async def check_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    username = user.username.lower() if user.username else None

    if not username or username not in tracked_users:
        await query.answer()
        await query.edit_message_text("🚫 Kamu tidak sedang dalam pengawasan OVM.")
        return

    track = tracked_users[username]
    now = datetime.now(timezone.utc)

    if now > track["until"]:
        try:
            await context.bot.restrict_chat_member(
                MAIN_GROUP_ID,
                user.id,
                permissions=ChatPermissions(can_send_messages=True)
            )
        except:
            pass
        del tracked_users[username]
        await query.answer()
        await query.edit_message_text("✅ Waktu OVM sudah habis. Kamu bebas sekarang.")
        return

    fullname = f"{user.first_name or ''} {user.last_name or ''}"
    if "dont@" not in fullname.lower():
        await query.answer()
        await query.edit_message_text("❗ Nama kamu belum mengandung 'dont@'. Ganti nama dulu.")
        return

    if track["muted"]:
        try:
            await context.bot.restrict_chat_member(
                MAIN_GROUP_ID,
                user.id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            tracked_users[username]["muted"] = False
            await query.answer()
            await query.edit_message_text("✅ Kamu sudah di-unmute karena pakai 'dont@'.")
        except Exception as e:
            await query.edit_message_text(f"❌ Gagal unmute: {e}")
    else:
        await query.edit_message_text("✅ Kamu tidak sedang mute.")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    username = user.username.lower() if user.username else None

    if not username or username not in tracked_users:
        return

    track = tracked_users[username]
    now = datetime.now(timezone.utc)

    if now > track["until"]:
        if track["muted"]:
            try:
                await context.bot.restrict_chat_member(
                    MAIN_GROUP_ID,
                    user.id,
                    permissions=ChatPermissions(can_send_messages=True)
                )
            except:
                pass
        del tracked_users[username]
        return

    fullname = f"{user.first_name or ''} {user.last_name or ''}"

    if "dont@" not in fullname.lower():
        # Hapus pesan karena pelanggaran
        try:
            await asyncio.sleep(3)
            await message.delete()

        except:
            pass

        # Mute 10 menit dengan until_date berupa timestamp UTC integer
        try:
            mute_until = datetime.now(timezone.utc) + timedelta(minutes=10)
            await context.bot.restrict_chat_member(
                MAIN_GROUP_ID,
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=int(mute_until.timestamp())
            )
            tracked_users[username]["muted"] = True
        except Exception as e:
            print(f"Gagal mute: {e}")

        keyboard = InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("Check Unmute", callback_data=f"check_{username}")
        )

        await context.bot.send_message(
        chat_id=MAIN_GROUP_ID,
        text=f"⚠️ @{username}, kamu harus pakai 'dont@' karena kamu overmention.\nSelama 24 Jam kamu harus pasang nama dont@ di nama akun kamu.",
        reply_markup=keyboard,
        reply_to_message_id=message.message_id  # Ini akan buat bot reply ke pesan user
    )

    else:
        if track["muted"]:
            try:
                await context.bot.restrict_chat_member(
                    MAIN_GROUP_ID,
                    user.id,
                    permissions=ChatPermissions(can_send_messages=True)
                )
                tracked_users[username]["muted"] = False
            except Exception as e:
                print(f"Gagal unmute: {e}")

async def main():
    app = ApplicationBuilder().token("7868589635:AAEGyBIEGbca7ZN2yb_MALNXxo6I2Dg_fHs").build()

    app.add_handler(CommandHandler("ovm", ovm))
    app.add_handler(CallbackQueryHandler(check_unmute, pattern=r"check_.*"))
    app.add_handler(MessageHandler(filters.ALL & filters.Chat(MAIN_GROUP_ID), on_message))

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    import asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
