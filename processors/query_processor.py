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
            # Get balances by currency
            ars_balances = self._get_balances_by_currency(group_id, 'ARS')
            usd_balance = self.transaction_service.db.get_balance_by_money_type_and_currency(group_id, None, 'USD')

            if query_data.get('query_type') == 'summary':
                # Create summary text that lists balances by currency
                summary = (
                    "📊 Resumen de tus finanzas:\n\n"
                    "💵 Efectivo ARS: ${:.2f}\n"
                    "🏦 Banco ARS: ${:.2f}\n"
                    "💰 Total ARS: ${:.2f}\n\n"
                    "💰 Total USD: ${:.2f}\n"
                ).format(
                    ars_balances['cash'],
                    ars_balances['bank'],
                    ars_balances['total'],
                    usd_balance
                )
                await update.message.reply_text(summary)
            else:
                # Show simple balance
                await update.message.reply_text(
                    f"Tus saldos:\n"
                    f"💵 Efectivo ARS: ${ars_balances['cash']:.2f}\n"
                    f"🏦 Banco ARS: ${ars_balances['bank']:.2f}\n"
                    f"💰 Total ARS: ${ars_balances['total']:.2f}\n\n"
                    f"💰 Total USD: ${usd_balance:.2f}"
                )
        except Exception as e:
            logger.error(f"Error handling query: {e}")
            await update.message.reply_text(
                "Perdón, hubo un error procesando tu consulta. ¿Podés intentarlo de nuevo?"
            )

    def _get_balances_by_currency(self, group_id: int, currency: str) -> dict:
        """Get balances for ARS currency."""
        cash_balance = self.transaction_service.db.get_balance_by_money_type_and_currency(
            group_id, self.get_money_type_id("cash"), currency
        )
        bank_balance = self.transaction_service.db.get_balance_by_money_type_and_currency(
            group_id, self.get_money_type_id("bank"), currency
        )
        return {
            'cash': cash_balance,
            'bank': bank_balance,
            'total': cash_balance + bank_balance
        } 