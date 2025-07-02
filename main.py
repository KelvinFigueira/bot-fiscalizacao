import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from datetime import datetime

TOKEN = "7872376410:AAHYX0nl302EmXChhZN5bsp0JwBCugMP35A"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Estrutura de corredores e salas
corredores = {
    "Corredor A Térreo": list(range(1, 20)),
    "Corredor B Térreo": list(range(41, 52)),
    "Corredor C Térreo": list(range(80, 89)),
    "Corredor A 1º Piso": list(range(20, 41)),
    "Corredor B 1º Piso": list(range(53, 69)),
    "Corredor C 1º Piso": list(range(89, 100)),
}

user_sessions = {}
photo_storage = {}  # Estrutura: {(corredor, sala, tipo, data): file_id}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(c, callback_data=f"corredor|{c}")] for c in corredores]
    await update.message.reply_text("Selecione o corredor:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    tipo, valor = data[0], data[1]

    user_id = query.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}

    if tipo == "corredor":
        user_sessions[user_id]["corredor"] = valor
        salas = corredores[valor]
        keyboard = [[InlineKeyboardButton(f"Sala {s:02}", callback_data=f"sala|{s}")] for s in salas]
        await query.message.reply_text("Selecione a sala:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif tipo == "sala":
        user_sessions[user_id]["sala"] = valor
        keyboard = [
            [
                InlineKeyboardButton("Chegada", callback_data="tipo|Chegada"),
                InlineKeyboardButton("Saída", callback_data="tipo|Saida")
            ]
        ]
        await query.message.reply_text("Chegada ou Saída?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif tipo == "tipo":
        user_sessions[user_id]["tipo"] = valor
        await query.message.reply_text("Envie agora a foto do data show.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_sessions or "corredor" not in user_sessions[user_id]:
        await update.message.reply_text("Use /start para iniciar o envio da foto.")
        return

    session = user_sessions[user_id]
    corredor = session["corredor"]
    sala = session["sala"]
    tipo = session["tipo"]
    data = datetime.now().strftime("%Y-%m-%d")

    file_id = update.message.photo[-1].file_id
    photo_storage[(corredor, sala, tipo, data)] = file_id

    await update.message.reply_text(
        f"✅ Foto registrada com sucesso!\n\n"
        f"📍 Corredor: {corredor}\n"
        f"🔢 Sala: {sala}\n"
        f"🕒 Tipo: {tipo}\n"
        f"📅 Data: {data}"
    )

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Uso: /ver <Corredor> <Sala> <Data>\nEx: /ver 'Corredor A Térreo' 01 2025-07-02")
        return

    corredor = context.args[0]
    sala = context.args[1]
    data = context.args[2]

    mensagens = []
    for tipo in ["Chegada", "Saida"]:
        key = (corredor, sala, tipo, data)
        if key in photo_storage:
            await update.message.reply_photo(photo_storage[key], caption=f"{tipo} registrada")
        else:
            mensagens.append(f"❌ Sem foto de {tipo}")

    if mensagens:
        await update.message.reply_text("\n".join(mensagens))

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(CommandHandler("ver", ver))

if __name__ == '__main__':
    app.run_polling()
