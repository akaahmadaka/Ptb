import logging
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    PicklePersistence,
    MessageHandler,
    filters,
    ConversationHandler,
)
from config import get_bot_token, get_admin_user_id, get_group_link
from broadcast import setup_broadcast_handler
from user_referral_system import (
    load_data,
    manage_user,
    get_referral_count,
    get_total_user_count,
)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation state for admin reply
REPLYING = 0

# Dictionary to store pending replies (key: admin message ID, value: user ID)
pending_replies = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command logic."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or str(user_id)
        bot_link = f"https://t.me/{context.bot.username}"
        ref_link = f"{bot_link}?start={user_id}"

        args = context.args
        referral_code = str(args[0]) if args else None

        is_new_user = await handle_referral(context, user_id, username, referral_code)
        await send_welcome_message(update, context, username, ref_link)
        await notify_admin(context, username, is_new_user)
        await schedule_referral_check(context, user_id, update.effective_chat.id)

    except Exception as e:
        logger.exception(f"Error in start: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def handle_referral(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str, referral_code: str):
    """Handles the referral logic."""
    data = load_data()
    if data is None:
        await context.bot.send_message(chat_id=user_id, text="An error occurred while loading user data. Please try again later.")
        return False

    is_new_user = manage_user(user_id, username, referred_by=referral_code)

    if referral_code:
        referrer_id = int(referral_code)
        if is_new_user:
            await inform_referrer_on_new_referral(context, referrer_id)
    return is_new_user

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, ref_link: str):
    """Sends the welcome message to the user."""
    custom_text = "☝️👆🔞Translation_x0_0x🔞☝️👆"
    share_url = f"https://t.me/share/url?text=\n{custom_text}&url={ref_link}"

    keyboard = [
        [InlineKeyboardButton("Share Your Link", url=share_url)],
        [InlineKeyboardButton("Get Group Link", callback_data="check_referrals")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Hello {username}, In order to get 🔞LANGUAGE🤤 Group link, you need to invite at least 3 users.\n\n{ref_link}\nhold to copy"
        "\n\nOr Click the buttons below:",
        reply_markup=reply_markup
    )

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, username:str, is_new_user: bool):
    """Notifies the admin about a new user."""
    if is_new_user:
        total_users = get_total_user_count()
        admin_message = f"🆕 New User!\nTotal: {total_users}\nName: {username}"
        try:
            await context.bot.send_message(chat_id=get_admin_user_id(), text=admin_message)
        except Exception as e:
            logger.exception(f"Error sending admin notification: {e}")

async def schedule_referral_check(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int):
    """Schedules the referral check job."""
    if context.job_queue:
        context.job_queue.run_once(
            check_referral_timeout,
            when=timedelta(hours=2),
            data={'user_id': user_id, 'chat_id': chat_id}
        )

async def inform_referrer_on_new_referral(context: ContextTypes.DEFAULT_TYPE, referrer_id: int):
    """Informs the referrer when someone joins using their link."""
    try:
        referral_count = get_referral_count(referrer_id)
        if referral_count < 3:
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"You invite {referral_count} users. You need at least 3 to get the group link.",
                disable_web_page_preview=True
            )
        elif referral_count == 3:  # Send congratulatory message only when they reach 3
            group_link = get_group_link()
            group_title = "👉 Language Group 👈"
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"Congratulations! {referral_count} users joined using your link.\nHere is the group link:\n <a href='{group_link}'>{group_title}</a>\nTap on start",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        # No message sent if referral_count > 3

    except Exception as e:
        logger.exception(f"Error informing referrer: {e}")

async def check_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the check_referrals callback query (button press)."""
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        await check_and_send_referral_message(context, user_id) # Use the old function

    except Exception as e:
        logger.exception(f"Error in check_referrals: {e}")
        await query.message.reply_text("An error occurred. Please try again later.")

async def check_and_send_referral_message(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Checks referral count and sends message if the threshold is met (for button press)."""
    try:
        referral_count = get_referral_count(user_id)
        if referral_count >= 3:
            group_link = get_group_link()
            group_title = "👉 Language Group 👈"

            message = (
                f"Congratulations! {referral_count} users joined using your link.\n"
                f"Here is the group link:\n <a href='{group_link}'>{group_title}</a>\nTap on Start"
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"You invite {referral_count} users. invite at least 3 users to get the group link.",
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.exception(f"Error in check_and_send_referral_message: {e}")

async def check_referral_timeout(context: ContextTypes.DEFAULT_TYPE):
    """Checks if a user has met the referral target after the specified time."""
    try:
        job = context.job
        data = job.data
        user_id = data['user_id']
        chat_id = data['chat_id']

        referral_count = get_referral_count(user_id)
        if referral_count < 3:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Reminder: You haven't reached the referral target yet. Invite more users to get the group link!"
                ),
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.exception(f"Error sending referral timeout message: {e}")

async def forward_to_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forwards user messages to the admin with a reply button."""
    admin_user_id = get_admin_user_id()
    await forward_to_admin(update, context, admin_user_id)

async def reply_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the admin's reply callback."""
    return await reply_callback(update, context)

async def send_reply_to_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the admin's reply to the user."""
    return await send_reply_to_user(update, context)

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the reply conversation."""
    return await cancel(update, context)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /top command to display the top 10 users with the most referrals."""
    user_id = update.effective_user.id
    if user_id != get_admin_user_id():
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    # Load data from user_data_converted.json
    try:
        with open('users_data_converted.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("❌ Data file not found. Please check the file path.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("❌ Invalid data file. Please check the file format.")
        return

    users = data.get('users', {})

    # Extract users with referral_count > 0
    users_with_referrals = [
        (user_info.get('username', 'Unknown User'), user_info['referral_count'])
        for user_info in users.values()
        if 'referral_count' in user_info and user_info['referral_count'] > 0
    ]

    # Sort users by referral_count in descending order
    sorted_users = sorted(users_with_referrals, key=lambda x: x[1], reverse=True)

    # Get top 10 users
    top_users = sorted_users[:10]

    # Prepare the message with emojis and formatting
    if not top_users:
        message = "📊 No users have made referrals yet."
    else:
        message = "🏆 *Top 10 Users with the Most Referrals* 🏆\n\n"
        for rank, (username, count) in enumerate(top_users, start=1):
            # Add emojis based on rank
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = "🔹"

            message += f"{medal} *{rank}. {username}* - {count}\n"

        message += "\n🎉 Keep up the great work! 🎉"

    # Send the formatted message
    await update.message.reply_text(message, parse_mode="Markdown")

def main():
    try:
        token = get_bot_token()
        admin_user_id = get_admin_user_id()

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
            entry_points=[CallbackQueryHandler(reply_callback_handler, pattern="^reply_")],
            states={
                REPLYING: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_reply_to_user_handler)]
            },
            fallbacks=[CommandHandler("cancel", cancel_handler)],
        )
        application.add_handler(conv_handler)

        # Add message forwarding handler (for user messages to admin)
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_to_admin_handler))

        setup_broadcast_handler(application)

        # Start the bot
        application.run_polling()

    except Exception as e:
        logger.exception(f"A top-level error occurred: {e}")

if __name__ == "__main__":
    main()