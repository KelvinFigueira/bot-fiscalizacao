from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import datetime

TOKEN = "7872376410:AAHYX0nl302EmXChhZN5bsp0JwBCugMP35A"

corredores = {
    "Corredor A Térreo": [f"Sala {i:02}" for i in range(1, 20)],
    "Corredor B Térreo": [f"Sala {i}" for i in range(41, 52)],
    "Corredor C Térreo": [f"Sala {i}" for i in range(80, 89)],
    "Corredor A 1º Piso": [f"Sala {i}" for i in range(20, 41)],
    "Corredor B 1º Piso": [f"Sala {i}" for i in range(53, 69)],
    "Corredor C 1º Piso": [f"Sala {i}" for i in range(89, 100)],
}

registros = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(text=c, callback_data=f"corredor|{c}")]
                for c in corredores.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecione o corredor:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("|")

    if data[0] == "corredor":
        corredor = data[1]
        salas = corredores[corredor]
        keyboard = [[InlineKeyboardButton(text=s, callback_data=f"sala|{corredor}|{s}")]
                    for s in salas]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"Salas do {corredor}:", reply_markup=reply_markup)

    elif data[0] == "sala":
        corredor, sala = data[1], data[2]
        keyboard = [
            [
                InlineKeyboardButton("📷 Chegada", callback_data=f"foto|{corredor}|{sala}|Chegada"),
                InlineKeyboardButton("📷 Saída", callback_data=f"foto|{corredor}|{sala}|Saída")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"{sala} - Selecione o tipo de foto:", reply_markup=reply_markup)

    elif data[0] == "foto":
        corredor, sala, tipo = data[1], data[2], data[3]
        context.user_data["corredor"] = corredor
        context.user_data["sala"] = sala
        context.user_data["tipo"] = tipo
        await query.edit_message_text(f"Envie a foto da **{sala} ({tipo})** agora:")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    corredor = context.user_data.get("corredor")
    sala = context.user_data.get("sala")
    tipo = context.user_data.get("tipo")
    data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    if corredor and sala and tipo:
        legenda = f"{tipo} registrada por {user.first_name}\n📍 {corredor} - {sala}\n🕒 {data_hora}"
        registros.setdefault(corredor, {}).setdefault(sala, []).append(legenda)

        photo = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=legenda)

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📋 *Registros de Fotos:*\n\n"
    for corredor, salas in registros.items():
        msg += f"🏢 *{corredor}*\n"
        for sala, fotos in salas.items():
            msg += f"  📌 {sala}: {len(fotos)} foto(s)\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ver", ver))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    app.run_polling()
