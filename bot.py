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

class LLMClient:
    def __init__(self):
        self.host = os.getenv('OLLAMA_HOST')
        self.model = os.getenv('MODEL')
        self.client = Client(host=self.host)

    def get_response(self, prompt: str) -> Dict[str, Any]:
        """Get structured response from LLM using JSON mode."""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt + "\nRespond ONLY with valid JSON.",
                system="You are a financial assistant that ONLY responds in valid JSON format.",
                format="json",  # Changed from {'type': 'json'} to "json"
                stream=False,
                options={
                    'temperature': 0.7,
                    'num_predict': 100,
                }
            )
            
            # Response will be a valid JSON string
            try:
                return json.loads(response['response'])
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in response: {e}")
                logger.debug(f"Raw response: {response['response']}")
                return None
            
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return None

    def get_structured_response(self, message: str) -> Dict[str, Any]:
        """Get a structured response with specific format."""
        prompt = f"""Interpreta este mensaje financiero en español y devuelve un objeto JSON: '{message}'

Expected formats:

For a SINGLE expense/income:
{{
    "type": "expense"|"income",  # Use "expense" for: "gasté", "pagué", "compré"
                                # Use "income" for: "cobré", "ingresé", "recibí"
    "amount": float,            # Convert numbers like "mil", "1k" to float
    "description": string,      # Keep original description
    "money_type": "bank"|"cash",
    "category": string          # Map to closest category
}}

For MULTIPLE transactions, return an array:
[{{
    "type": "expense"|"income",
    "amount": float,
    "description": string,
    "money_type": "bank"|"cash",
    "category": string
}}]

For exchanges:
{{
    "type": "exchange",
    "amount": float,           # Original amount
    "target_amount": float,    # Final amount
    "source_currency": string, # Original currency (USD, EUR, etc)
    "target_currency": string, # Target currency (usually ARS)
    "money_type": "bank"|"cash",
    "exchange_rate": float     # target_amount / amount
}}

For queries:
{{
    "type": "query",
    "query_type": "summary"|"balance",  # "summary" for: "resumen", "total", "mostrame todo"
                                       # "balance" for: "cuánto tengo", "saldo"
    "money_type": "cash"|"bank"|"all"   # "cash" for: "efectivo", "plata"
                                       # "bank" for: "banco", "cuenta"
                                       # "all" for general queries
}}

Categories:
- "comida": restaurantes, delivery, cafetería, fiambrería, almuerzo, cena, comida, restaurant
- "transporte": taxi, uber, colectivo, subte, nafta, bondi, tren, didi, remis
- "servicios": luz, gas, agua, internet, teléfono, servicios, factura, seguro, impuestos
- "supermercado": super, mercado, almacén, verdulería, carnicería, pescadería, panadería, pastelería, heladería
- "entretenimiento": cine, teatro, juegos, salidas, streaming, spotify, netflix, bar
- "salud": farmacia, médico, medicamentos, consulta, análisis
- "otros": default when unclear

Rules:
1. ALWAYS return valid JSON
2. For expenses with "tarjeta"|"transferencia"|"débito"|"crédito" → Use "bank"
3. For expenses with "efectivo"|"cash"|"plata" → Use "cash"
4. DEFAULT to "cash" if no payment method mentioned
5. Use ONLY the specified category values
6. Convert ALL amounts to float
7. For exchanges, calculate exchange_rate as target_amount/amount
8. Return array ONLY for multiple transactions
9. Process Spanish text and common Argentine terms

DO NOT include any text outside the JSON structure.
"""
        return self.get_response(prompt)

class BotHandler:
    def __init__(self):
        self.transaction_service = TransactionService()
        self.llm = LLMClient()
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

Comandos administrativos:
/clear - Borrar todas las transacciones ⚠️
"""
        await update.message.reply_text(welcome_text)

    async def clear_database(self, update: Update, context):
        """Initiate database clearing process."""
        group_id = update.message.chat.id
        logger.info(f"User requested to clear transactions for group {group_id}")
        await update.message.reply_text(
            "⚠️ ¿Estás seguro de que querés borrar TODAS las transacciones?\n"
            "Esta acción no se puede deshacer.\n"
            "Escribí /confirmar para proceder."
        )
        context.user_data['clear_pending'] = True

    async def confirm_clear(self, update: Update, context):
        """Confirm and execute database clearing."""
        if context.user_data.get('clear_pending', False):
            group_id = update.message.chat.id
            self.transaction_service.db.clear_transactions(group_id)
            logger.info(f"Cleared transactions for group {group_id}")
            await update.message.reply_text("✅ Se borraron todas las transacciones.")
            context.user_data['clear_pending'] = False
        else:
            await update.message.reply_text("No hay ninguna operación de borrado pendiente.")

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
                        await self._handle_query(update, group_id, data)
                        return
                    # Handle single transaction
                    elif data.get('type') in TransactionType.values():
                        self._process_transaction(user_id, group_id, data)
                        await update.message.reply_text("✅ Transacción registrada correctamente.")
                        return
                
                # Handle multiple transactions
                if isinstance(data, list):
                    for transaction_data in data:
                        self._process_transaction(user_id, group_id, transaction_data)
                    
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

    async def _handle_query(self, update: Update, group_id: int, data: Dict[str, Any]):
        """Handle query responses from LLM."""
        try:
            # Set default money_type to "all" for summaries
            if data['query_type'] == 'summary':
                data['money_type'] = 'all'
            
            # Handle balance queries
            if data['money_type'] == 'cash':
                balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, 
                    self._get_money_type_id(MoneyType.CASH)
                )
                await update.message.reply_text(f"💵 Tu saldo en efectivo es: ${balance:.2f}")
                
            elif data['money_type'] == 'bank':
                balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, 
                    self._get_money_type_id(MoneyType.BANK)
                )
                await update.message.reply_text(f"🏦 Tu saldo en banco es: ${balance:.2f}")
                
            else:  # 'all'
                cash_balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, 
                    self._get_money_type_id(MoneyType.CASH)
                )
                bank_balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, 
                    self._get_money_type_id(MoneyType.BANK)
                )
                total_balance = cash_balance + bank_balance
                
                if data['query_type'] == 'summary':
                    expenses = self.transaction_service.db.get_expenses_summary(group_id)
                    
                    # Generate pie chart
                    plt.figure(figsize=(10, 8))
                    labels = []
                    values = []
                    for category, amount in expenses:
                        if amount < 0:  # Only include expenses (negative amounts)
                            labels.append(category)
                            values.append(abs(amount))
                    
                    if values:  # Only create chart if there are expenses
                        plt.pie(values, labels=labels, autopct='%1.1f%%')
                        plt.title('Distribución de Gastos por Categoría')
                        
                        # Save plot to bytes buffer
                        buf = io.BytesIO()
                        plt.savefig(buf, format='png', bbox_inches='tight')
                        buf.seek(0)
                        plt.close()
                        
                        # Send text summary
                        summary = (
                            f"📊 Resumen de tus finanzas:\n\n"
                            f"💵 Efectivo: ${cash_balance:.2f}\n"
                            f"🏦 Banco: ${bank_balance:.2f}\n"
                            f"💰 Total: ${total_balance:.2f}\n\n"
                            f"📈 Detalle por categoría:\n"
                        )
                        for category, amount in expenses:
                            summary += f"- {category}: ${amount:.2f}\n"
                        
                        await update.message.reply_text(summary)
                        
                        # Send pie chart
                        await update.message.reply_photo(
                            photo=buf,
                            caption="Distribución de tus gastos 📊"
                        )
                    else:
                        await update.message.reply_text("No hay gastos registrados para mostrar en el gráfico.")
                else:
                    await update.message.reply_text(
                        f"Tus saldos:\n"
                        f"💵 Efectivo: ${cash_balance:.2f}\n"
                        f"🏦 Banco: ${bank_balance:.2f}\n"
                        f"💰 Total: ${total_balance:.2f}"
                    )
        except Exception as e:
            logger.error(f"Error handling query: {e}")
            await update.message.reply_text(
                "Perdón, hubo un error procesando tu consulta. ¿Podés intentarlo de nuevo?"
            )

    def _process_transaction(self, user_id: int, group_id: int, transaction_data: Dict[str, Any]) -> None:
        """Process a single transaction."""
        try:
            if transaction_data['type'] == TransactionType.EXCHANGE:
                self._process_exchange_transaction(user_id, group_id, transaction_data)
            else:
                self._process_regular_transaction(user_id, group_id, transaction_data)
        except Exception as e:
            logger.error(f"Error processing transaction: {e}")
            raise

    def _process_exchange_transaction(self, user_id: int, group_id: int, data: Dict[str, Any]) -> None:
        """Process an exchange transaction."""
        # Calculate exchange rate if not provided
        if 'exchange_rate' not in data:
            data['exchange_rate'] = data['target_amount'] / data['amount']
        
        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            group_id=group_id,
            transaction_type=TransactionType.INCOME,
            amount=data['target_amount'],
            description=self._format_exchange_description(data),
            category_id=self._get_category_id(Category.EXCHANGE),
            money_type_id=self._get_money_type_id(data.get('money_type', MoneyType.CASH))
        )
        
        # Add transaction and exchange details
        transaction_id = self.transaction_service.add_transaction(transaction)
        exchange_transaction = ExchangeTransaction(
            transaction_id=transaction_id,
            source_currency=data['source_currency'],
            target_currency=data['target_currency'],
            exchange_rate=data['exchange_rate']
        )
        self.transaction_service.add_exchange_transaction(exchange_transaction)

    def _process_regular_transaction(self, user_id: int, group_id: int, data: Dict[str, Any]) -> None:
        """Process an expense or income transaction."""
        is_expense = data['type'] == TransactionType.EXPENSE
        
        # Clean up description - capitalize first letter and handle Spanish characters
        description = data.get('description', '').strip()
        if description:
            description = description[0].upper() + description[1:].lower()
            # Handle Spanish characters
            description = description.replace('fiambreria', 'fiambrería')
        
        category_id = self._get_category_id(data.get('category', Category.COMIDA))
        money_type_id = self._get_money_type_id(data.get('money_type', MoneyType.CASH))
        
        transaction = Transaction(
            user_id=user_id,
            group_id=group_id,
            transaction_type=data['type'],
            amount=data['amount'] * (-1 if is_expense else 1),
            description=description,
            category_id=category_id,
            money_type_id=money_type_id
        )
        
        self.transaction_service.add_transaction(transaction)
        
        # Log the mappings for verification
        category_name = self.transaction_service.db.get_category_name(category_id)
        money_type_name = self.transaction_service.db.get_money_type_name(money_type_id)
        logger.info(f"Transaction saved with category: {category_id} ({category_name}), "
                    f"money_type: {money_type_id} ({money_type_name})")

    def _format_exchange_description(self, data: Dict[str, Any]) -> str:
        """Format the description for an exchange transaction."""
        return (
            f"Exchange: {data['amount']} {data['source_currency']} → "
            f"{data['target_amount']} {data['target_currency']}"
        )

    def _get_category_id(self, category_name: Optional[str]) -> Optional[int]:
        """Get or create category ID."""
        if not category_name:
            return self._get_category_id(Category.OTROS)
        return self.transaction_service.db.get_or_create_category(category_name)

    def _get_money_type_id(self, money_type: Optional[str]) -> Optional[int]:
        """Get or create money type ID."""
        if not money_type:
            return self._get_money_type_id(MoneyType.CASH)
        return self.transaction_service.db.get_or_create_money_type(money_type)

def main():
    bot_token = os.getenv('BOT_TOKEN')
    application = Application.builder().token(bot_token).build()
    
    bot_handler = BotHandler()
    
    # Add command handlers for sensitive operations
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("clear", bot_handler.clear_database))
    application.add_handler(CommandHandler("confirmar", bot_handler.confirm_clear))
    
    # Handle all other messages through natural language
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_message))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main() 