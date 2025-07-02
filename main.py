import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://bot-fiscalizacao.onrender.com{WEBHOOK_PATH}"

app = Flask(__name__)

# Inicializa o bot
application = Application.builder().token(TOKEN).build()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot rodando com webhook!")

# Adiciona handler
application.add_handler(CommandHandler("start", start))

# Rota para receber atualizações do Telegram
@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.update_queue.put(update)
    return "OK", 200

# Configura o webhook quando o aplicativo iniciar
def setup_webhook():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.bot.set_webhook(WEBHOOK_URL))

# Configura o webhook quando o app iniciar
setup_webhook()

# Inicia o servidor Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
