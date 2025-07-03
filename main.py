import os
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# --- Configuração ---
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = f"https://bot-fiscalizacao.onrender.com/{TOKEN}"
app = Flask(__name__)

# --- Dados de corredores e salas ---
CORREDORES = {
    "Corredor A Térreo": [f"Sala {i:02d}" for i in range(1, 20)],
    "Corredor B Térreo": [f"Sala {i}" for i in range(41, 52)],
    "Corredor C Térreo": [f"Sala {i}" for i in range(80, 89)],
    "Corredor A 1º Piso": [f"Sala {i}" for i in range(20, 41)],
    "Corredor B 1º Piso": [f"Sala {i}" for i in range(53, 69)],
    "Corredor C 1º Piso": [f"Sala {i}" for i in range(89, 100)],
}

# --- Estados da conversa ---
SELECIONAR_CORREDOR, SELECIONAR_SALA, SELECIONAR_TIPO, RECEBER_FOTO = range(4)
registros = {}  # Armazenamento temporário

# --- Comandos ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Bot de Fiscalização\n\n"
        "Comandos disponíveis:\n"
        "/registrar - Iniciar novo registro\n"
        "/ver \"Corredor\" Sala Data\n\n"
        "Ex: /ver \"Corredor A Térreo\" 01 2025-07-02"
    )

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(c, callback_data=f"corredor_{c}")] for c in CORREDORES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📍 Selecione o Corredor:", reply_markup=reply_markup)
    return SELECIONAR_CORREDOR

async def ver_registro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        _, corredor, sala, data = update.message.text.split(maxsplit=3)
        chave = f"{corredor} {sala} {data}"
        if chave not in registros:
            await update.message.reply_text("❌ Nenhum registro encontrado.")
            return

        resposta = f"📅 Registros para {chave}:\n\n"
        for tipo, dados in registros[chave].items():
            resposta += (
                f"🖼️ {tipo}:\n"
                f"👤 {dados['usuario']}\n"
                f"📆 {dados['data']}\n"
                f"📎 [Foto](https://api.telegram.org/file/bot{TOKEN}/{dados['foto_id']})\n\n"
            )
        await update.message.reply_text(resposta, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(
            "⚠️ Formato incorreto.\nEx: /ver \"Corredor A Térreo\" 01 2025-07-02"
        )

# --- Callbacks de interação ---
async def button_corredor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    corredor = query.data.replace("corredor_", "")
    context.user_data['corredor'] = corredor
    keyboard = [[InlineKeyboardButton(s, callback_data=f"sala_{s}")] for s in CORREDORES[corredor]]
    await query.edit_message_text(f"📍 {corredor}\n🔢 Selecione a Sala:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECIONAR_SALA

async def button_sala(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    sala = query.data.replace("sala_", "")
    context.user_data['sala'] = sala
    keyboard = [[
        InlineKeyboardButton("Chegada", callback_data="tipo_Chegada"),
        InlineKeyboardButton("Saída", callback_data="tipo_Saída")
    ]]
    await query.edit_message_text(
        f"📍 {context.user_data['corredor']}\n🔢 Sala: {sala}\n🕒 Selecione o Tipo:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECIONAR_TIPO

async def button_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tipo = query.data.replace("tipo_", "")
    context.user_data['tipo'] = tipo
    await query.edit_message_text(
        f"📸 Agora envie a foto para:\n"
        f"📍 {context.user_data['corredor']}\n"
        f"🔢 Sala: {context.user_data['sala']}\n"
        f"🕒 Tipo: {tipo}"
    )
    return RECEBER_FOTO

async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Envie uma foto, por favor.")
        return RECEBER_FOTO

    foto_id = update.message.photo[-1].file_id
    registro = {
        "foto_id": foto_id,
        "corredor": context.user_data['corredor'],
        "sala": context.user_data['sala'],
        "tipo": context.user_data['tipo'],
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "usuario": update.effective_user.full_name
    }

    chave = f"{registro['corredor']} {registro['sala']} {registro['data'][:10]}"
    registros.setdefault(chave, {})[registro['tipo']] = registro

    await update.message.reply_text(
        f"✅ Registro salvo!\n📍 {registro['corredor']}\n"
        f"🔢 Sala {registro['sala']}\n🕒 {registro['tipo']}\n"
        f"👤 {registro['usuario']}\n📆 {registro['data']}",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_photo(photo=registro['foto_id'], caption=f"{registro['tipo']} - {registro['data']}")
    return ConversationHandler.END

# --- Inicialização do app e webhook ---
application = Application.builder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("registrar", registrar)],
    states={
        SELECIONAR_CORREDOR: [CallbackQueryHandler(button_corredor, pattern="^corredor_")],
        SELECIONAR_SALA: [CallbackQueryHandler(button_sala, pattern="^sala_")],
        SELECIONAR_TIPO: [CallbackQueryHandler(button_tipo, pattern="^tipo_")],
        RECEBER_FOTO: [MessageHandler(filters.PHOTO, receber_foto)],
    },
    fallbacks=[]
)

application.add_handler(conv_handler)
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ver", ver_registro))

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.update_queue.put(update)
    return "OK", 200

async def set_webhook():
    await application.bot.set_webhook(WEBHOOK_URL)

import asyncio
asyncio.run(set_webhook())

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
