import os
import logging

logger = logging.getLogger(__name__)

def get_bot_token():
    """Retrieves the bot token from environment variables or defaults."""
    token = os.getenv("BOT_TOKEN", "7856502542:AAFOlqazGOG0JpwpQjfmm_ARNd4huACWVpM")
    if not token:
        logger.error("BOT_TOKEN environment variable is not set.")
        raise ValueError("BOT_TOKEN environment variable is not set.")
    return token

def get_admin_user_id():
    """Retrieves the admin user ID from environment variables or defaults."""
    admin_id = os.getenv("ADMIN_USER_ID", "5250831809")
    if not admin_id:
        logger.error("ADMIN_USER_ID environment variable is not set.")
        raise ValueError("ADMIN_USER_ID environment variable is not set.")
    return int(admin_id)

def get_group_link():
    """Retrieves the group link from environment variables or defaults."""
    group_link = os.getenv("GROUP_LINK", "https://t.me/PAWSOG_bot/PAWS?startapp=x4I1Iegd")
    if not group_link:
        logger.error("GROUP_LINK environment variable is not set.")
        raise ValueError("GROUP_LINK environment variable is not set.")
    return group_link