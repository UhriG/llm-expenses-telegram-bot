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
    def __init__(self, transaction_service):
        self.host = os.getenv('OLLAMA_HOST')
        self.model = os.getenv('MODEL')
        self.client = Client(host=self.host)
        self.transaction_service = transaction_service

    def get_response(self, prompt: str) -> Dict[str, Any]:
        """Get structured response from LLM using JSON mode."""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt + "\nRespond ONLY with valid JSON.",
                system="You are a financial assistant that ONLY responds in valid JSON format.",
                format="json",
                stream=False,
                options={
                    'temperature': 0.7,
                    'num_predict': 100,
                }
            )
            
            # Log the raw response
            logger.info(f"Raw model response: {response['response']}")
            
            # Response will be a valid JSON string
            try:
                return json.loads(response['response'])
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in response: {e}")
                logger.error(f"Problematic response: {response['response']}")
                return None
            
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            logger.error(f"Full error details: {str(e)}")
            return None

    def get_structured_response(self, message: str) -> Dict[str, Any]:
        """Get a structured response with specific format."""
        # Get existing categories from database
        existing_categories = self.transaction_service.db.get_all_categories()
        categories_str = ", ".join(f'"{cat}"' for cat in existing_categories)
        
        # Clean up the message - replace multiple newlines with a single one
        message = ' '.join(message.split())
        
        prompt = f"""Analiza el siguiente mensaje financiero y devuelve la respuesta en JSON: '{message}'

Categorías existentes: [{categories_str}]

Para CONSULTAS (resumen, balance, etc) usar este formato:
{{
    "type": "query",
    "query_type": "summary"|"balance",  # "summary" para "resumen", "mostrame todo" | "balance" para "cuánto tengo"
    "money_type": "cash"|"bank"|"all"   # "cash" para efectivo, "bank" para banco, "all" para todo
}}

Para TRANSACCIONES usar este formato (siempre en array):
[
    {{
        "type": "expense"|"income",
        "amount": float,
        "description": string,
        "money_type": "bank"|"cash",
        "category": string,
        "should_create_category": boolean,
        "category_reason": string
    }}
]

Para CAMBIO DE DIVISAS usar este formato:
{{
    "type": "exchange",
    "amount": float,
    "target_amount": float,
    "source_currency": string,
    "target_currency": string,
    "money_type": "bank"|"cash",
    "exchange_rate": float  # Calculado como target_amount/amount
}}

REGLAS:
1. Si el mensaje es una consulta como "resumen", "balance", "cuánto tengo", "mostrame" → Usar formato de CONSULTAS
2. Si el mensaje es sobre gastos/ingresos → Usar formato de TRANSACCIONES
3. Si el mensaje es sobre cambio de divisas → Usar formato de CAMBIO
4. Para pagos de tarjeta de crédito o servicios financieros → category: "financiero"
5. Para transferencias o tarjeta → money_type: "bank"
6. Para efectivo → money_type: "cash"
7. Convertir TODOS los montos a números (sin el símbolo $)
8. NO incluir texto fuera de la estructura JSON
9. NO usar caracteres especiales en las descripciones

Ejemplos:
1. "Dame un resumen" →
{{
    "type": "query",
    "query_type": "summary",
    "money_type": "all"
}}

2. "Gasté $100 en comida" →
[{{
    "type": "expense",
    "amount": 100.0,
    "description": "Comida",
    "money_type": "cash",
    "category": "comida",
    "should_create_category": false,
    "category_reason": ""
}}]

3. "Cambié 100 USD a 90000 pesos" →
{{
    "type": "exchange",
    "amount": 100.0,
    "target_amount": 90000.0,
    "source_currency": "USD",
    "target_currency": "ARS",
    "money_type": "cash",
    "exchange_rate": 900.0
}}

Palabras clave:
- Consultas: "resumen", "balance", "cuánto tengo", "mostrar", "dame"
- Gastos: "gasté", "pagué", "compré", "tarjeta"
- Ingresos: "cobré", "recibí", "ingresé", "deposité"
- Cambios: "cambié", "convertí", "pasé de"
"""

        try:
            response = self.get_response(prompt)
            if not response:
                return None
            
            # If response is a transaction dict, wrap it in a list
            if isinstance(response, dict):
                if response.get('type') in ['expense', 'income']:
                    response = [response]
            
            return response
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return None

class BotHandler:
    def __init__(self):
        self.transaction_service = TransactionService()
        self.llm = LLMClient(self.transaction_service)
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

    async def clear_database(self, update: Update, context):
        """Initiate database clearing process."""
        group_id = update.message.chat.id
        
        # Get current transaction count
        transactions = self.transaction_service.db.get_latest_transactions(group_id, limit=None)
        count = len(transactions)
        
        logger.info(f"User requested to clear {count} transactions for group {group_id}")
        
        await update.message.reply_text(
            f"⚠️ ¿Estás seguro de que querés borrar TODAS las transacciones ({count} en total)?\n"
            "Esta acción:\n"
            "- Borrará todas las transacciones\n"
            "- Reiniciará los IDs desde 1\n"
            "- Mantendrá las categorías existentes\n"
            "- No se puede deshacer\n\n"
            "Escribí /confirmar para proceder."
        )
        context.user_data['clear_pending'] = True

    async def confirm_clear(self, update: Update, context):
        """Confirm and execute database clearing."""
        if context.user_data.get('clear_pending', False):
            group_id = update.message.chat.id
            self.transaction_service.db.clear_transactions(group_id)
            logger.info(f"Cleared transactions for group {group_id}")
            await update.message.reply_text(
                "✅ Se borraron todas las transacciones.\n"
                "Los próximos registros comenzarán desde el ID 1."
            )
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
        
        # Clean up description
        description = data.get('description', '').strip()
        if description:
            description = description[0].upper() + description[1:].lower()
        
        # Handle category creation if needed
        if data.get('should_create_category', False):
            category_name = data['category']
            category_reason = data.get('category_reason', 'New category needed')
            logger.info(f"Creating new category '{category_name}'. Reason: {category_reason}")
        
        category_id = self._get_category_id(data.get('category'))
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

    async def list_transactions(self, update: Update, context):
        """List recent transactions for deletion."""
        group_id = update.message.chat.id
        show_all = False
        category = None
        
        # Parse arguments
        if context.args:
            if context.args[0].lower() == "all":
                show_all = True
            else:
                # Check if it's a valid category
                category = context.args[0].lower()
                if category not in self.transaction_service.db.get_all_categories():
                    categories = ", ".join(self.transaction_service.db.get_all_categories())
                    await update.message.reply_text(
                        f"❌ Categoría no válida. Las categorías disponibles son:\n{categories}"
                    )
                    return
        
        transactions = self.transaction_service.db.get_latest_transactions(
            group_id, 
            limit=None if show_all else 10,
            category=category
        )
        
        if not transactions:
            msg = "No hay transacciones"
            if category:
                msg += f" en la categoría '{category}'"
            msg += " para mostrar."
            await update.message.reply_text(msg)
            return
        
        # Format the transaction list
        message = "🗑 Para borrar una transacción, usá /borrar seguido del ID\n\n"
        if category:
            message = f"📊 Mostrando transacciones de la categoría '{category}'\n\n"
        
        message += "ID | Fecha | Tipo | Monto | Categoría | Descripción\n"
        message += "-" * 50 + "\n"
        
        for tx in transactions:
            tx_id, tx_type, amount, description, tx_category, timestamp = tx
            # Format timestamp to local date
            date = timestamp.split()[0]  # Get just the date part
            # Format amount with sign
            amount_str = f"${abs(amount):.2f}"
            if tx_type == "expense":
                amount_str = f"-{amount_str}"
            elif tx_type == "income":
                amount_str = f"+{amount_str}"
            
            message += f"{tx_id} | {date} | {tx_type} | {amount_str} | {tx_category} | {description}\n"
        
        message += "\nEjemplos:\n"
        message += "/borrar 123 - Borra una transacción\n"
        message += "/listar all - Muestra todas las transacciones\n"
        message += "/listar comida - Muestra solo transacciones de comida"
        
        await update.message.reply_text(message)

    async def delete_transaction(self, update: Update, context):
        """Delete a specific transaction by ID."""
        if not context.args:
            await update.message.reply_text(
                "❌ Tenés que especificar el ID de la transacción a borrar.\n"
                "Usá /listar para ver los IDs disponibles."
            )
            return
        
        try:
            transaction_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ El ID debe ser un número.\n"
                "Usá /listar para ver los IDs disponibles."
            )
            return
        
        group_id = update.message.chat.id
        if self.transaction_service.db.delete_transaction(transaction_id, group_id):
            await update.message.reply_text(f"✅ Transacción {transaction_id} borrada correctamente.")
            logger.info(f"Deleted transaction {transaction_id} for group {group_id}")
        else:
            await update.message.reply_text(
                "❌ No se encontró la transacción o no tenés permiso para borrarla."
            )

    async def rename_category(self, update: Update, context):
        """Rename a category."""
        if len(context.args) < 2:
            # Show current categories and usage
            categories = self.transaction_service.db.get_all_categories()
            categories_list = "\n".join(f"- {cat}" for cat in categories)
            
            await update.message.reply_text(
                "❌ Tenés que especificar la categoría original y el nuevo nombre.\n\n"
                "Uso: /renombrar categoria_original nuevo_nombre\n\n"
                "Categorías actuales:\n"
                f"{categories_list}\n\n"
                "Ejemplo: /renombrar comida alimentos"
            )
            return
        
        old_name = context.args[0].lower()
        new_name = context.args[1].lower()
        
        success, message = self.transaction_service.db.rename_category(old_name, new_name)
        if success:
            logger.info(f"Category renamed from '{old_name}' to '{new_name}'")
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")

def main():
    bot_token = os.getenv('BOT_TOKEN')
    application = Application.builder().token(bot_token).build()
    
    bot_handler = BotHandler()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("clear", bot_handler.clear_database))
    application.add_handler(CommandHandler("confirmar", bot_handler.confirm_clear))
    application.add_handler(CommandHandler("listar", bot_handler.list_transactions))
    application.add_handler(CommandHandler("borrar", bot_handler.delete_transaction))
    application.add_handler(CommandHandler("renombrar", bot_handler.rename_category))
    
    # Handle all other messages through natural language
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_handler.handle_message))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main() 