import os
from datetime import datetime
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Configurações
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = f"https://bot-fiscalizacao.onrender.com/{TOKEN}"
app = Flask(__name__)

# Dados dos corredores (como fornecido)
CORREDORES = {
    "Corredor A Térreo": [f"Sala {i:02d}" for i in range(1, 20)],
    "Corredor B Térreo": [f"Sala {i}" for i in range(41, 52)],
    "Corredor C Térreo": [f"Sala {i}" for i in range(80, 89)],
    "Corredor A 1º Piso": [f"Sala {i}" for i in range(20, 41)],
    "Corredor B 1º Piso": [f"Sala {i}" for i in range(53, 69)],
    "Corredor C 1º Piso": [f"Sala {i}" for i in range(89, 100)],
}

# Estados da conversa
SELECIONAR_CORREDOR, SELECIONAR_SALA, SELECIONAR_TIPO, RECEBER_FOTO = range(4)
registros = {}  # Armazena os dados (substitua por banco de dados em produção)

# ---- Comandos Principais ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 **Bot de Fiscalização**\n\n"
        "Comandos disponíveis:\n"
        "/registrar - Iniciar novo registro\n"
        "/ver - Consultar registros\n\n"
        "Exemplo: /ver \"Corredor A Térreo\" 01 2025-07-02"
    )

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Cria botões inline para corredores
    keyboard = [
        [InlineKeyboardButton(corredor, callback_data=f"corredor_{corredor}")]
        for corredor in CORREDORES.keys()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📍 Selecione o Corredor:",
        reply_markup=reply_markup
    )
    return SELECIONAR_CORREDOR

async def ver_registro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        _, corredor, sala, data = update.message.text.split(maxsplit=3)
        chave = f"{corredor} {sala} {data}"
        
        if chave not in registros:
            await update.message.reply_text("❌ Nenhum registro encontrado!")
            return
        
        resposta = f"📅 **Registros para {chave}**\n\n"
        for tipo, dados in registros[chave].items():
            resposta += (
                f"🖼️ {tipo}:\n"
                f"👤 {dados['usuario']}\n"
                f"📆 {dados['data']}\n"
                f"📎 [Foto](https://api.telegram.org/file/bot{TOKEN}/{dados['foto_id']})\n\n"
            )
        
        await update.message.reply_text(resposta, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(
            "⚠️ Formato incorreto! Use:\n"
            "/ver \"Corredor\" Sala Data\n\n"
            "Exemplo:\n"
            "/ver \"Corredor A Térreo\" 01 2025-07-02"
        )

# ---- Handlers de Callback ----
async def button_corredor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    corredor = query.data.replace("corredor_", "")
    context.user_data['corredor'] = corredor
    
    # Cria botões para salas
    keyboard = [
        [InlineKeyboardButton(sala, callback_data=f"sala_{sala}")]
        for sala in CORREDORES[corredor]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📍 Corredor: {corredor}\n\n🔢 Selecione a Sala:",
        reply_markup=reply_markup
    )
    return SELECIONAR_SALA

async def button_sala(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    sala = query.data.replace("sala_", "")
    context.user_data['sala'] = sala
    
    # Cria botões para tipo
    keyboard = [
        [
            InlineKeyboardButton("Chegada", callback_data="tipo_Chegada"),
            InlineKeyboardButton("Saída", callback_data="tipo_Saída")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📍 {context.user_data['corredor']}\n"
        f"🔢 Sala: {sala}\n\n"
        "🕒 Selecione o Tipo:",
        reply_markup=reply_markup
    )
    return SELECIONAR_TIPO

async def button_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    tipo = query.data.replace("tipo_", "")
    context.user_data['tipo'] = tipo
    
    await query.edit_message_text(
        f"📸 Agora envie a foto para:\n\n"
        f"📍 {context.user_data['corredor']}\n"
        f"🔢 Sala: {context.user_data['sala']}\n"
        f"🕒 Tipo: {tipo}"
    )
    return RECEBER_FOTO

async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Por favor, envie uma foto!")
        return RECEBER_FOTO
    
    # Armazena os dados
    registro = {
        'foto_id': update.message.photo[-1].file_id,
        'corredor': context.user_data['corredor'],
        'sala': context.user_data['sala'],
        'tipo': context.user_data['tipo'],
        'data': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'usuario': update.effective_user.full_name
    }
    
    # Organiza por corredor/sala/data
    chave = f"{registro['corredor']} {registro['sala']} {registro['data'][:10]}"
    registros.setdefault(chave, {})[registro['tipo']] = registro
    
    # Confirmação
    await update.message.reply_text(
        f"✅ **Registro concluído!**\n\n"
        f"📍 {registro['corredor']}\n"
        f"🔢 Sala {registro['sala']}\n"
        f"🕒 {registro['tipo']}\n"
        f"👤 {registro['usuario']}\n"
        f"📆 {registro['data']}",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Envia a foto de volta como confirmação
    await update.message.reply_photo(
        photo=registro['foto_id'],
        caption=f"{registro['tipo']} - {registro['data']}"
    )
    
    return ConversationHandler.END

# ---- Configuração do Bot ----
def main():
    application = Application.builder().token(TOKEN).build()
    
    # Handler de conversação
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("registrar", registrar)],
        states={
            SELECIONAR_CORREDOR: [CallbackQueryHandler(button_corredor, pattern="^corredor_")],
            SELECIONAR_SALA: [CallbackQueryHandler(button_sala, pattern="^sala_")],
            SELECIONAR_TIPO: [CallbackQueryHandler(button_tipo, pattern="^tipo_")],
            RECEBER_FOTO: [MessageHandler(filters.PHOTO, receber_foto)]
        },
        fallbacks=[CommandHandler("cancelar", lambda u,c: ConversationHandler.END)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ver", ver_registro))
    
    # Configura webhook
    @app.route(f"/{TOKEN}", methods=["POST"])
    async def webhook():
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.update_queue.put(update)
        return "OK", 200
    
    async def set_webhook():
        await application.bot.set_webhook(WEBHOOK_URL)
    
   if __name__ == "__main__":
        import asyncio
        asyncio.run(set_webhook())
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)

main()
