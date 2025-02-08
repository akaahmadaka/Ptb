import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    PicklePersistence,
    MessageHandler,
    filters,
    ConversationHandler,
)

from config import get_bot_token
from handlers import start, check_referrals
from broadcast import setup_broadcast_handler
from data_utils import convert_user_data_if_needed
from forwarder import forward_to_admin, reply_callback, send_reply_to_user, REPLYING, cancel
from top import top  # Import the top function from top.py

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        convert_user_data_if_needed()
        token = get_bot_token()
        ADMIN_USER_ID = 5250831809  # Replace with your actual admin user ID

        persistence = PicklePersistence(filepath="referral_data.pickle")
        application = (
            ApplicationBuilder()
            .token(token)
            .persistence(persistence)
            .concurrent_updates(True)
            .build()
        )

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(check_referrals, pattern="^check_referrals$"))
        application.add_handler(CommandHandler("top", top))  # Add the /top handler

        # Conversation handler for admin replies
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(reply_callback, pattern="^reply_")],
            states={
                REPLYING: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_reply_to_user)]
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        application.add_handler(conv_handler)

        # Add message forwarding handler (for user messages to admin)
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, lambda update, context: forward_to_admin(update, context, ADMIN_USER_ID)))

        setup_broadcast_handler(application)

        # Start the bot
        application.run_polling()

    except Exception as e:
        logger.exception(f"A top-level error occurred: {e}")

if __name__ == "__main__":
    main()