import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from database import DatabaseHandler
from dotenv import load_dotenv

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
        response = requests.post(url, json=data)
        return response.json()['response']

class BotHandler:
    def __init__(self):
        self.db = DatabaseHandler()
        self.llm = LLMClient()

    async def start(self, update: Update, context):
        await update.message.reply_text("Welcome to your personal expense tracker! Just tell me about your expenses or income in natural language.")

    async def handle_message(self, update: Update, context):
        user_id = update.message.from_user.id
        message = update.message.text
        
        # Get LLM interpretation
        prompt = f"Interpret this financial message: '{message}'. Is it an income, expense, or query? Respond with JSON format: {{'type': 'income'|'expense'|'query', 'amount': float, 'description': str}}"
        response = self.llm.get_response(prompt)
        
        try:
            data = eval(response)
            if data['type'] in ['income', 'expense']:
                self.db.add_transaction(user_id, data['type'], data['amount'], data['description'])
                await update.message.reply_text(f"Recorded {data['type']} of ${data['amount']} for {data['description']}")
            elif data['type'] == 'query':
                balance = self.db.get_balance(user_id)
                await update.message.reply_text(f"Your current balance is ${balance:.2f}")
        except Exception as e:
            await update.message.reply_text("Sorry, I didn't understand that. Could you please rephrase?")

def main():
    bot_token = os.getenv('BOT_TOKEN')
    application = Application.builder().token(bot_token).build()
    
    bot_handler = BotHandler()
    
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_message))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main() 