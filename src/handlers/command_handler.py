from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import logger

class CommandHandler:
    def __init__(self, transaction_service):
        self.transaction_service = transaction_service

    async def handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clear command"""
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

    async def handle_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle confirm command"""
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

    async def handle_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle list command"""
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
            date = timestamp.split()[0]
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

    async def handle_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete command"""
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

    async def handle_rename(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle rename command"""
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