import os
import logging

logger = logging.getLogger(__name__)

def get_bot_token():
    """Retrieves the bot token from either environment variables or a text file."""
    token = os.getenv("BOT_TOKEN")
    if token:
        return token

    try:
        with open("api.txt", "r") as file:
            token = file.read().strip()
            return token
    except FileNotFoundError:
        logger.error("The file api.txt was not found.")
        raise
    except Exception as e:
        logger.exception(f"Error reading the token from file: {e}")
        raise