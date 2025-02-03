import unittest
from unittest.mock import Mock, patch, AsyncMock
from bot import BotHandler, TransactionType, Category, MoneyType

class TestBotHandler(unittest.TestCase):
    def setUp(self):
        self.bot_handler = BotHandler()
        self.update = Mock()
        self.context = Mock()
        self.update.message.from_user.id = 123
        self.update.message.chat.id = 456

    @patch('bot.LLMClient')
    async def test_handle_single_expense(self, mock_llm):
        """Test handling a single expense transaction"""
        # Mock LLM response
        mock_llm.return_value.get_structured_response.return_value = {
            "type": "expense",
            "amount": 1000.0,
            "description": "Almuerzo",
            "category": "comida",
            "money_type": "cash"
        }
        
        self.update.message.text = "Gasté 1000 en almuerzo"
        
        # Mock database methods
        self.bot_handler.transaction_service.db.get_category_name.return_value = "comida"
        self.bot_handler.transaction_service.db.get_money_type_name.return_value = "cash"
        
        await self.bot_handler.handle_message(self.update, self.context)
        
        # Verify transaction was processed correctly
        self.bot_handler.transaction_service.add_transaction.assert_called_once()
        args = self.bot_handler.transaction_service.add_transaction.call_args[0][0]
        self.assertEqual(args.transaction_type, TransactionType.EXPENSE)
        self.assertEqual(args.amount, -1000.0)
        self.assertEqual(args.description, "Almuerzo")

    @patch('bot.LLMClient')
    async def test_handle_multiple_expenses(self, mock_llm):
        """Test handling multiple transactions"""
        mock_llm.return_value.get_structured_response.return_value = [
            {
                "type": "expense",
                "amount": 100.0,
                "description": "Pan",
                "category": "supermercado",
                "money_type": "cash"
            },
            {
                "type": "expense",
                "amount": 200.0,
                "description": "Leche",
                "category": "supermercado",
                "money_type": "cash"
            }
        ]
        
        self.update.message.text = "Compré pan 100 y leche 200"
        await self.bot_handler.handle_message(self.update, self.context)
        
        # Verify two transactions were processed
        self.assertEqual(self.bot_handler.transaction_service.add_transaction.call_count, 2)

    @patch('bot.LLMClient')
    @patch('matplotlib.pyplot')
    async def test_handle_summary_query(self, mock_plt, mock_llm):
        """Test handling a summary query with pie chart"""
        mock_llm.return_value.get_structured_response.return_value = {
            "type": "query",
            "query_type": "summary",
            "money_type": "all"
        }
        
        # Mock database responses
        self.bot_handler.transaction_service.db.get_balance_by_money_type.side_effect = [1000.0, 2000.0]
        self.bot_handler.transaction_service.db.get_expenses_summary.return_value = [
            ("comida", -500.0),
            ("transporte", -300.0)
        ]
        
        self.update.message.text = "Dame un resumen"
        await self.bot_handler.handle_message(self.update, self.context)
        
        # Verify pie chart was generated
        mock_plt.pie.assert_called_once()
        mock_plt.savefig.assert_called_once()

    @patch('bot.LLMClient')
    async def test_handle_exchange(self, mock_llm):
        """Test handling a currency exchange"""
        mock_llm.return_value.get_structured_response.return_value = {
            "type": "exchange",
            "amount": 100.0,
            "target_amount": 90000.0,
            "source_currency": "USD",
            "target_currency": "ARS",
            "money_type": "cash",
            "exchange_rate": 900.0
        }
        
        self.update.message.text = "Cambié 100 dólares a 90000 pesos"
        await self.bot_handler.handle_message(self.update, self.context)
        
        # Verify exchange transaction was processed
        self.bot_handler.transaction_service.add_transaction.assert_called_once()
        self.bot_handler.transaction_service.add_exchange_transaction.assert_called_once()

    def test_format_exchange_description(self):
        """Test exchange description formatting"""
        data = {
            "amount": 100,
            "source_currency": "USD",
            "target_amount": 90000,
            "target_currency": "ARS"
        }
        description = self.bot_handler._format_exchange_description(data)
        self.assertEqual(description, "Exchange: 100 USD → 90000 ARS")

if __name__ == '__main__':
    unittest.main() 