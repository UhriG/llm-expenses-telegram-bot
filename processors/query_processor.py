import io
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional
from utils.logger import logger

class QueryProcessor:
    def __init__(self, transaction_service):
        self.transaction_service = transaction_service

    def get_money_type_id(self, money_type: Optional[str]) -> int:
        """
        Helper method to get (or create) the money type ID.
        Defaults to "cash" if no money_type is provided.
        """
        if not money_type:
            return self.transaction_service.db.get_or_create_money_type("cash")
        return self.transaction_service.db.get_or_create_money_type(money_type)

    async def process_query(self, update, group_id: int, query_data: Dict[str, Any]) -> None:
        """
        Process query responses.
        Handles balance queries and summary queries (with a pie chart) based on the 
        'query_type' and 'money_type' fields in query_data.
        """
        try:
            # For summary queries, force money_type to be all so we can combine balances.
            if query_data.get('query_type') == 'summary':
                query_data['money_type'] = 'all'

            if query_data.get('money_type') == 'cash':
                balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, self.get_money_type_id("cash")
                )
                await update.message.reply_text(f"💵 Tu saldo en efectivo es: ${balance:.2f}")
            elif query_data.get('money_type') == 'bank':
                balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, self.get_money_type_id("bank")
                )
                await update.message.reply_text(f"🏦 Tu saldo en banco es: ${balance:.2f}")
            else:  # money_type "all"
                cash_balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, self.get_money_type_id("cash")
                )
                bank_balance = self.transaction_service.db.get_balance_by_money_type(
                    group_id, self.get_money_type_id("bank")
                )
                total_balance = cash_balance + bank_balance

                if query_data.get('query_type') == 'summary':
                    expenses = self.transaction_service.db.get_expenses_summary(group_id)

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

                        # Create summary text that lists balances and expense details
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