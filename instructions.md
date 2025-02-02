Expense Tracker Telegram Bot with Local LLM Integration (Natural Chat Interface)
==================================================================================

Overview
--------
This project builds a Telegram bot that lets users manage their expenses and incomes through a natural, conversational interface. Instead of relying on explicit commands, the bot uses an LLM (Mistral via the Ollama API) to interpret freeform messages. Whether a user types, “I spent $50 on lunch today” or “What’s my balance?”, the bot understands the intent, records transactions in a local SQLite database, and even provides personalized financial advice.

Key Features:
• Natural Chat Interface – Users interact in freeform language rather than using strict commands.
• Local Data Privacy – All financial data is stored locally on your machine.
• AI-Driven Insights – The Mistral model (accessed via Ollama) processes and interprets natural language input to handle transactions and generate advice.
• Secure Configuration – Sensitive credentials (like the Telegram Bot token) and settings are stored in a .env file.
• Object-Oriented Code – The project is structured using OOP in Python to maintain clear separation of concerns (for example, classes like BotHandler, DatabaseHandler, and LLMClient).

Architecture & Components
-------------------------
1. Ollama API Server:
   - Runs locally (default address: 127.0.0.1:11434).
   - Uses the Mistral model (pull with "ollama pull mistral").
   - Start the server using: "ollama serve".

2. Telegram Bot (Python):
   - Built with the python-telegram-bot library.
   - Listens for natural language messages.
   - Uses the Mistral model via Ollama to interpret the user's intent.
   - Performs actions such as recording transactions, retrieving summaries, and offering financial advice.
   - Designed using Object-Oriented Programming (OOP) for clarity and maintainability.

3. SQLite Database:
   - A lightweight database to store transactions.
   - Each transaction includes: id, user_id (Telegram chat ID), type (income/expense), amount, description, and a timestamp.
   - Database interactions (insertions, queries) are encapsulated in a dedicated module/class.

4. Environment Variables (.env File):
   - Sensitive data and configuration settings are stored in a .env file.
   - Example variables include:
     
     BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE  
     OLLAMA_HOST=http://127.0.0.1:11434  
     MODEL=mistral

   - Ensure that the .env file is excluded from version control (add it to .gitignore).

Setup Instructions
------------------

Prerequisites:
• Python 3.8 or higher  
• Git  
• Docker (if using any Dockerized components such as an optional WebUI)  
• Ollama installed on your local machine

Step-by-Step Guide:
1. Clone the Repository:
   - Run:  
     git clone https://github.com/yourusername/expense-tracker-bot.git  
     cd expense-tracker-bot

2. Create and Configure the .env File:
   - In the project root, create a file named ".env".
   - Add the following lines (replace placeholders with your actual credentials):
     
     BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE  
     OLLAMA_HOST=http://127.0.0.1:11434  
     MODEL=mistral

3. Install Python Dependencies:
   - (Optional) Create and activate a virtual environment.
   - Run:  
     pip install -r requirements.txt
   - Your requirements.txt should include:
     • python-telegram-bot  
     • requests  
     • python-dotenv

4. Set Up the SQLite Database:
   - Use the provided database initialization script (or let the bot handle it on first run):
     python database.py

5. Start the Ollama API Server:
   - Open a terminal window and run:  
     ollama serve
   - Ensure the Mistral model is pulled (if not, run "ollama pull mistral") and that the server is listening on 127.0.0.1:11434.

6. Run the Telegram Bot:
   - In a separate terminal window, run:  
     python bot.py

7. Interact with the Bot on Telegram:
   - Open a chat with your bot.
   - Simply type natural language messages. For example:
     • “I earned $5000 from my salary.”  
       (The bot will record an income transaction.)
     • “I spent $200 on groceries yesterday.”  
       (The bot will record an expense.)
     • “What is my current balance?”  
       (The bot will query the SQLite database and provide a financial summary.)
     • “Can you give me some financial advice?”  
       (The bot will use the Mistral model to generate personalized advice.)

Project Structure
-----------------
expense-tracker-bot/  
  • bot.py           - Main Telegram bot code, designed with OOP to handle natural language processing and interactions.  
  • database.py      - Contains the SQLite database schema and functions for recording and querying transactions.  
  • .env             - Stores sensitive credentials and configuration variables (excluded from Git).  
  • requirements.txt - Lists all Python dependencies.  
  • PROJECT_INSTRUCTIONS.md - This detailed project guide.  
  • README.md        - Additional project information (optional).

Object-Oriented Design Considerations
---------------------------------------
Using OOP in this project is highly recommended. For instance:
• BotHandler Class: Encapsulates logic for receiving messages, interpreting intent via the LLM, and responding appropriately.
• DatabaseHandler Class: Manages all database interactions such as inserting transactions and retrieving summaries.
• LLMClient Class: Interfaces with the Ollama API, sending user prompts and processing the responses.
This modular design improves code clarity, facilitates testing, and makes future feature additions easier.

Deployment
----------
Local Deployment:
   - Follow the setup instructions above to run the bot on your local machine.

Optional Docker Deployment:
   - You may containerize parts of the project (for example, the WebUI or even the bot) using a Dockerfile and docker-compose.yml.
   - Ensure proper port configuration so that the Docker containers do not conflict with the Ollama server or each other.

Contributing
------------
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with detailed explanations of your changes.

License
-------
This project is licensed under the MIT License.

Contact
-------
For questions or suggestions, please open an issue on GitHub or contact the project maintainer directly.