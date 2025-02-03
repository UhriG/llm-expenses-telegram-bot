import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create file handler
file_handler = RotatingFileHandler(
    f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log',
    maxBytes=1024*1024,  # 1MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Filter out httpx polling logs
logging.getLogger('httpx').setLevel(logging.WARNING)
# Filter out telegram polling logs
logging.getLogger('telegram.ext._application').setLevel(logging.WARNING)
logging.getLogger('telegram.ext._updater').setLevel(logging.WARNING) 