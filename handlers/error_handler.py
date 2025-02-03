from telegram.ext import CallbackContext
from utils.logger import logger

async def error_handler(update: object, context: CallbackContext) -> None:
    """
    Handles errors that occur while processing updates.
    Logs the error using the global logger and sends a friendly message to the user.
    """
    logger.error("Exception while handling an update:", exc_info=context.error)
    if update is not None and hasattr(update, "message") and update.message:
        await update.message.reply_text(
            "Hubo un error interno. Por favor, intentalo de nuevo más tarde."
        ) 