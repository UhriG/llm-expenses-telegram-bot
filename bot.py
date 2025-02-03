import os
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from services.transaction_service import TransactionService
from models.transaction import Transaction, ExchangeTransaction
from dotenv import load_dotenv
from utils.logger import logger
from contextlib import asynccontextmanager
from ollama import Client
from typing import Dict, Any, Optional
import matplotlib.pyplot as plt
import io
from telegram import InputFile
from processors.transaction_processor import TransactionProcessor
from processors.query_processor import QueryProcessor
from services.llm_client import LLMClient

load_dotenv()

class TransactionType:
    EXPENSE = "expense"
    INCOME = "income"
    EXCHANGE = "exchange"

    @classmethod
    def values(cls):
        return [cls.EXPENSE, cls.INCOME, cls.EXCHANGE]

class MoneyType:
    CASH = "cash"
    BANK = "bank"

class Category:
    COMIDA = "comida"
    TRANSPORTE = "transporte"
    SERVICIOS = "servicios"
    SUPERMERCADO = "supermercado"
    ENTRETENIMIENTO = "entretenimiento"
    SALUD = "salud"
    OTROS = "otros"
    EXCHANGE = "exchange"

class BotHandler:
    def __init__(self, transaction_service):
        self.transaction_service = transaction_service
        self.transaction_processor = TransactionProcessor(transaction_service)
        self.query_processor = QueryProcessor(transaction_service)
        self.llm = LLMClient(transaction_service)
        logger.info("BotHandler initialized")

    @asynccontextmanager
    async def typing_action(self, chat_id, context):
        """Show typing action while processing."""
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            yield
        finally:
            pass

    async def start(self, update: Update, context):
        """Send welcome message."""
        welcome_text = """
¡Bienvenido a tu gestor de gastos personal! 📊

Simplemente contame sobre tus gastos o ingresos en lenguaje natural:
- "Gasté $500 en comida"
- "Ingresé $1000 de sueldo"
- "Cambié 100 USD a 90000 pesos"
- "Cuánto tengo en efectivo?"
- "Dame un resumen"

Comandos disponibles:
/listar - Ver últimas 10 transacciones 📋
/listar all - Ver todas las transacciones 📋
/listar categoria - Ver transacciones de una categoría 📋
/borrar ID - Borrar una transacción específica 🗑
/clear - Borrar todas las transacciones ⚠️
/renombrar vieja nueva - Renombrar una categoría 📝
"""
        await update.message.reply_text(welcome_text)

    async def handle_message(self, update: Update, context):
        """Process all messages through LLM."""
        user_id = update.message.from_user.id
        group_id = update.message.chat.id
        message = update.message.text
        logger.info(f"Received message from user {user_id} in group {group_id}: {message}")
        
        async with self.typing_action(group_id, context):
            data = self.llm.get_structured_response(message)
            
            if not data:
                await update.message.reply_text(
                    "Perdón, no pude procesar tu mensaje. ¿Podrías reformularlo?"
                )
                return
            
            try:
                # Handle query responses
                if isinstance(data, dict):
                    if data.get('type') == 'query':
                        await self.query_processor.process_query(update, group_id, data)
                        return
                    # Handle single transaction
                    elif data.get('type') in TransactionType.values():
                        self.transaction_processor.process_transaction(user_id, group_id, data)
                        await update.message.reply_text("✅ Transacción registrada correctamente.")
                        return
                
                # Handle multiple transactions
                if isinstance(data, list):
                    for transaction_data in data:
                        self.transaction_processor.process_transaction(user_id, group_id, transaction_data)
                    
                    await update.message.reply_text(
                        f"✅ Registré {len(data)} {'transacción' if len(data) == 1 else 'transacciones'} correctamente."
                    )
                    return
                
                logger.error(f"Unexpected response format: {data}")
                await update.message.reply_text(
                    "Perdón, no entendí bien ese mensaje. ¿Podrías decirlo de otra forma?"
                )
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await update.message.reply_text(
                    "Hubo un error procesando tu mensaje. ¿Podrías intentarlo de nuevo?"
                )

def main():
    bot_token = os.getenv('BOT_TOKEN')
    application = Application.builder().token(bot_token).build()
    
    transaction_service = TransactionService()
    bot_handler = BotHandler(transaction_service)
    from handlers.command_handler import BotCommandHandler
    command_handler = BotCommandHandler(transaction_service)
    
    # Register command handlers from BotCommandHandler
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("clear", command_handler.clear_database))
    application.add_handler(CommandHandler("confirmar", command_handler.confirm_clear))
    application.add_handler(CommandHandler("listar", command_handler.list_transactions))
    application.add_handler(CommandHandler("borrar", command_handler.delete_transaction))
    application.add_handler(CommandHandler("renombrar", command_handler.rename_category))
    
    # Handle all other messages through natural language
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_message))

    # --- Register global error handler from error_handler.py ---
    from handlers.error_handler import error_handler
    application.add_error_handler(error_handler)
    # -------------------------------------------------------------

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main() 