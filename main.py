import os
import logging
from datetime import datetime
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Configuração essencial
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = f"https://bot-fiscalizacao.onrender.com/{TOKEN}"
app = Flask(__name__)

# Dados dos corredores (sua estrutura original)
CORREDORES = {
    "Corredor A Térreo": [f"Sala {i:02d}" for i in range(1, 20)],
    "Corredor B Térreo": [f"Sala {i}" for i in range(41, 52)],
    "Corredor C Térreo": [f"Sala {i}" for i in range(80, 89)],
    "Corredor A 1º Piso": [f"Sala {i}" for i in range(20, 41)],
    "Corredor B 1º Piso": [f"Sala {i}" for i in range(53, 69)],
    "Corredor C 1º Piso": [f"Sala {i}" for i in range(89, 100)],
}

# ---- COMANDOS ESTÁVEIS ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando básico para testar conexão"""
    try:
        await update.message.reply_text("✅ Bot está operacional!")
        logger.info("Comando /start processado com sucesso")
    except Exception as e:
        logger.error(f"Erro no /start: {e}")

async def mostrar_corredores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe os corredores como antes (funcionou!)"""
    try:
        keyboard = []
        for corredor in CORREDORES:
            keyboard.append([InlineKeyboardButton(corredor, callback_data=f"corredor_{corredor}")])
        
        await update.message.reply_text(
            "📍 Selecione o Corredor:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info("Menu de corredores exibido")
    except Exception as e:
        logger.error(f"Erro ao mostrar corredores: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa seleções de corredor (funcionou!)"""
    query = update.callback_query
    try:
        corredor = query.data.replace("corredor_", "")
        await query.answer()
        await query.edit_message_text(f"Você selecionou: {corredor}")
        logger.info(f"Corredor selecionado: {corredor}")
    except Exception as e:
        logger.error(f"Erro no callback: {e}")

# ---- CONFIGURAÇÃO ROBUSTA ----
def create_app():
    application = Application.builder().token(TOKEN).build()
    
    # Handlers mínimos e testados
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("corredores", mostrar_corredores))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    return application

# ---- WEBHOOK CONFIÁVEL ----
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    try:
        json_data = await request.get_json()
        update = Update.de_json(json_data, bot_app.bot)
        await bot_app.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return "ERROR", 500

@app.route("/")
def home():
    return "Bot Fiscalizador Online", 200

@app.route("/keepalive")
def keep_alive():
    return "OK", 200

if __name__ == "__main__":
    # Configuração simplificada
    bot_app = create_app()
    
    # Inicialização síncrona para evitar problemas
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.bot.set_webhook(WEBHOOK_URL))
    loop.run_until_complete(bot_app.start())
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
