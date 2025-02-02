import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from database import DatabaseHandler
from dotenv import load_dotenv
import json

load_dotenv()

class LLMClient:
    def __init__(self):
        self.ollama_host = os.getenv('OLLAMA_HOST')
        self.model = os.getenv('MODEL')

    def get_response(self, prompt):
        url = f"{self.ollama_host}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()  # Raise an error for bad status codes
            return response.json().get('response', '')
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            return ''

class BotHandler:
    def __init__(self):
        self.db = DatabaseHandler()
        self.llm = LLMClient()

    async def start(self, update: Update, context):
        await update.message.reply_text("¡Bienvenido a tu gestor de gastos personal! Contame sobre tus gastos o ingresos en lenguaje natural y te ayudo a registrarlos.")

    async def handle_message(self, update: Update, context):
        user_id = update.message.from_user.id
        group_id = update.message.chat.id
        message = update.message.text
        
        # Get LLM interpretation
        prompt = f"Interpretá este mensaje financiero: '{message}'. Identificá múltiples transacciones si las hay. Para cada transacción, respondé en formato JSON: [{{'type': 'expense'|'income'|'exchange', 'amount': float, 'description': str, 'money_type': 'cash'|'bank', 'category': str, 'source_currency': str, 'target_currency': str, 'exchange_rate': float}}]. Usá español rioplatense (argentino)."
        response = self.llm.get_response(prompt)
        
        if not response:
            await update.message.reply_text("Perdón, estoy teniendo problemas para procesar tu mensaje. ¿Podés intentarlo de nuevo más tarde?")
            return
        
        try:
            data = json.loads(response)
            if isinstance(data, list):  # Check if multiple transactions
                for transaction in data:
                    self.db.add_transaction(
                        user_id, 
                        group_id, 
                        transaction['type'], 
                        transaction['amount'], 
                        transaction.get('description'), 
                        transaction.get('category'), 
                        transaction.get('money_type'), 
                        transaction.get('source'),
                        transaction.get('source_currency'),
                        transaction.get('target_currency'),
                        transaction.get('exchange_rate')
                    )
                await update.message.reply_text(f"Registré {len(data)} transacciones correctamente.")
            else:  # Single transaction
                self.db.add_transaction(
                    user_id, 
                    group_id, 
                    data['type'], 
                    data['amount'], 
                    data.get('description'), 
                    data.get('category'), 
                    data.get('money_type'), 
                    data.get('source'),
                    data.get('source_currency'),
                    data.get('target_currency'),
                    data.get('exchange_rate')
                )
                await update.message.reply_text(f"Registré un {data['type']} de ${data['amount']} para {data.get('description', 'sin descripción')}.")
        except json.JSONDecodeError as e:
            print(f"Error decodificando la respuesta del LLM: {e}")
            await update.message.reply_text("Perdón, no pude procesar tu mensaje. ¿Podés intentarlo de nuevo?")
        except Exception as e:
            print(f"Error procesando la respuesta del LLM: {e}")
            await update.message.reply_text("Perdón, no entendí eso. ¿Podés reformularlo?")

    async def clear_database(self, update: Update, context):
        group_id = update.message.chat.id
        # Ask for confirmation
        await update.message.reply_text("¿Estás seguro de que querés borrar todos los registros del grupo? Escribí /confirmar para confirmar.")
        context.user_data['clear_pending'] = True

    async def confirm_clear(self, update: Update, context):
        group_id = update.message.chat.id
        if context.user_data.get('clear_pending', False):
            self.db.clear_transactions(group_id)
            await update.message.reply_text("¡Listo! Borré todos los registros del grupo.")
            context.user_data['clear_pending'] = False
        else:
            await update.message.reply_text("No hay ninguna operación pendiente de confirmación.")

def main():
    bot_token = os.getenv('BOT_TOKEN')
    application = Application.builder().token(bot_token).build()
    
    bot_handler = BotHandler()
    
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("clear", bot_handler.clear_database))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_message))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main() 