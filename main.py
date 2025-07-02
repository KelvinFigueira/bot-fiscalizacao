from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import datetime
import logging
import os
import sys

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Obter token de variável de ambiente (mais seguro)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7872376410:AAHYX0nl302EmXChhZN5bsp0JwBCugMP35A")

corredores = {
    "Corredor A Térreo": [f"Sala {i:02}" for i in range(1, 20)],
    "Corredor B Térreo": [f"Sala {i}" for i in range(41, 52)],
    "Corredor C Térreo": [f"Sala {i}" for i in range(80, 89)],
    "Corredor A 1º Piso": [f"Sala {i}" for i in range(20, 41)],
    "Corredor B 1º Piso": [f"Sala {i}" for i in range(53, 69)],
    "Corredor C 1º Piso": [f"Sala {i}" for i in range(89, 100)],
}

# Dicionário para armazenar registros
registros = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [[InlineKeyboardButton(text=c, callback_data=f"corredor|{c}")]
                    for c in corredores.keys()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Selecione o corredor:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Erro no comando /start: {e}")
        await update.message.reply_text("❌ Ocorreu um erro. Tente novamente mais tarde.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
            
    except Exception as e:
        logger.error(f"Erro no button_handler: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ocorreu um erro ao processar sua solicitação."
        )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.message.from_user
        corredor = context.user_data.get("corredor")
        sala = context.user_data.get("sala")
        tipo = context.user_data.get("tipo")
        
        if not all([corredor, sala, tipo]):
            await update.message.reply_text("⚠️ Por favor, selecione uma sala primeiro usando o menu.")
            return

        data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        legenda = f"{tipo} registrada por {user.first_name}\n📍 {corredor} - {sala}\n🕒 {data_hora}"
        
        # Armazenar registro corretamente
        if corredor not in registros:
            registros[corredor] = {}
        if sala not in registros[corredor]:
            registros[corredor][sala] = []
            
        registros[corredor][sala].append(legenda)

        photo = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo,
            caption=legenda
        )
        
        # Limpar dados temporários
        context.user_data.pop("corredor", None)
        context.user_data.pop("sala", None)
        context.user_data.pop("tipo", None)
        
    except Exception as e:
        logger.error(f"Erro no photo_handler: {e}")
        await update.message.reply_text("❌ Falha ao processar a foto. Tente novamente.")

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not registros:
            await update.message.reply_text("📭 Nenhum registro encontrado.")
            return
            
        msg = "📋 *Registros de Fotos:*\n\n"
        for corredor, salas in registros.items():
            msg += f"🏢 *{corredor}*\n"
            for sala, fotos in salas.items():
                msg += f"  📌 {sala}: {len(fotos)} foto(s)\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Erro no comando /ver: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao recuperar os registros.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Erro não tratado: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ Ocorreu um erro inesperado. Os desenvolvedores foram notificados.")

def main():
    logger.info("Iniciando aplicação...")
    
    try:
        # Construir aplicação
        app = Application.builder().token(TOKEN).build()
        
        # Adicionar handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("ver", ver))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        
        # Handler de erros
        app.add_error_handler(error_handler)
        
        logger.info("Bot iniciado. Pressione Ctrl+C para encerrar.")
        app.run_polling(
            close_loop=False,
            stop_signals=[],
            timeout=30,
            read_timeout=30,
            connect_timeout=30,
            pool_timeout=30
        )
        
    except Exception as e:
        logger.critical(f"Erro fatal: {e}")
        sys.exit(1)
    finally:
        logger.info("Aplicação encerrada.")

if __name__ == "__main__":
    main()
