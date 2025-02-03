# Telegram Expense Tracker Bot

A Telegram bot that helps you track expenses, incomes, and currency exchanges using natural language. Just write how you would normally talk about money - the bot will understand and categorize everything automatically.

## Features

### Natural Language Understanding
Simply write your transactions as you would tell them to a friend:
```
"Gasté $500 en el supermercado con tarjeta"
"Me quedé sin plata, pagué $7000 el taxi"
"Ingresé $50000 del sueldo en efectivo"
"Cambié 100 USD a 90000 pesos"
"Cuánto tengo en efectivo?"
"Dame un resumen de mis gastos"
```

### Automatic Categorization
The bot automatically detects categories:
- 🍽️ Food & Restaurants
- 🚗 Transportation
- 📱 Services & Utilities
- 🛒 Supermarket
- 🎮 Entertainment
- 🏥 Health
- 💱 Currency Exchange
- 📦 Others

### Smart Payment Detection
Automatically detects payment method:
- 💳 Bank/Card when you mention: "tarjeta", "débito", "crédito", "transferencia"
- 💵 Cash when you mention: "efectivo", "cash", "plata"
- Defaults to cash when not specified

### Quick Queries
Just ask naturally:
- "Cuánto tengo?" - Get total balance
- "Efectivo?" - Check cash balance
- "Banco?" - Check bank balance
- "Resumen" - Get detailed summary
- "Gastos del mes" - See monthly expenses

## Administrative Commands

For safety, some operations require specific commands:

### `/clear`
Initiates the process to clear all transactions. Requires confirmation with `/confirmar`.

### `/confirmar`
Confirms the clearing of all transactions after using `/clear`.

⚠️ Warning: Clearing transactions cannot be undone!

## Setup

### 1. Prerequisites
- Python 3.8 or higher
- Ollama installed and running (https://ollama.ai)
- A Telegram Bot Token (from @BotFather)

### 2. Clone and Install
```bash
# Clone the repository
git clone https://github.com/your-repo/expense-tracker-bot.git
cd expense-tracker-bot

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the project root:
```env
BOT_TOKEN=your_telegram_bot_token_here
OLLAMA_HOST=http://127.0.0.1:11434
MODEL=qwen2.5:7b
```

### 4. Install and Start Ollama
```bash
# Pull the model
ollama pull qwen2.5:7b

# Start Ollama server (in a separate terminal)
ollama serve
```

### 5. Run the Bot
```bash
python bot.py
```

## Examples

### Recording Expenses
```
"Almorcé por $15000"
→ Categoría: comida, Método: efectivo

"Pagué la luz con tarjeta, $76000"
→ Categoría: servicios, Método: banco

"Uber $5600 con débito"
→ Categoría: transporte, Método: banco
```

### Multiple Transactions
```
"Hoy gasté en efectivo: leche 2000, pan 1500, café 3000"
→ 3 transacciones en supermercado

"Con tarjeta compré remedios por 12000 y después cena 8000"
→ 2 transacciones: salud y comida
```

### Currency Exchange
```
"Cambié 430 USD a 510200 pesos"
"Compré 100 euros por 95000 pesos con tarjeta"
```

## Database Structure

Uses SQLite with tables for:
- Transactions (expenses, incomes)
- Categories (automatic classification)
- Money Types (cash/bank)
- Exchange Transactions

## Project Structure
```
expense-tracker-bot/
├── bot.py                 # Main bot logic
├── database.py           # Database operations
├── models/              # Data models
├── services/           # Business logic
├── utils/              # Utilities
├── tests/             # Test files
├── logs/              # Log files
└── README.md          # Documentation
```

## Development

### Running Tests
```bash
python -m unittest discover tests
```

### Logs
Check `logs/bot_YYYYMMDD.log` for detailed operation logs.

## License
MIT