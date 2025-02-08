import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
import user_referral_system as urs
from datetime import timedelta



logger = logging.getLogger(__name__)

ADMIN_USER_ID = 5250831809

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command logic."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name or str(user_id)
        bot_link = f"https://t.me/{context.bot.username}"
        ref_link = f"{bot_link}?start={user_id}"

        data = urs.load_data()
        if data is None:
            await update.message.reply_text("An error occurred while loading user data. Please try again later.")
            return

        args = context.args
        referral_code = str(args[0]) if args else None

        # Manage user FIRST
        is_new_user = urs.manage_user(user_id, username, referred_by=referral_code)

        if referral_code:
            referrer_id = int(referral_code)
            if is_new_user: # Only send message if is a new user
                await inform_referrer_on_new_referral(context, referrer_id)

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

        # Only send admin message if this is a new user
        if is_new_user:
            total_users = urs.get_total_user_count()
            admin_message = f"🆕 New User!\nTotal: {total_users}\nName: {username}"
            try:
                await context.bot.send_message(chat_id=ADMIN_USER_ID, text=admin_message)
            except Exception as e:
                logger.exception(f"Error sending admin notification: {e}")

        # Schedule the referral check job if job queue is available
        if context.job_queue:
            chat_id = update.effective_chat.id
            context.job_queue.run_once(
                check_referral_timeout,
                when=timedelta(hours=2),
                data={'user_id': user_id, 'chat_id': chat_id}
            )

    except Exception as e:
        logger.exception(f"Error in start: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")

async def inform_referrer_on_new_referral(context: ContextTypes.DEFAULT_TYPE, referrer_id: int):
    """Informs the referrer when someone joins using their link."""
    try:
        referral_count = urs.get_referral_count(referrer_id)
        if referral_count < 3:
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"You invite {referral_count} users. You need at least 3 to get the group link.",
                disable_web_page_preview=True
            )
        elif referral_count == 3:  # Send congratulatory message only when they reach 3
            group_link = "https://t.me/PAWSOG_bot/PAWS?startapp=MaN4GLCm"  # Replace with your group link
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
        referral_count = urs.get_referral_count(user_id)
        if referral_count >= 3:
            group_link = "https://t.me/PAWSOG_bot/PAWS?startapp=MaN4GLCm"  # Replace with your group link
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

        referral_count = urs.get_referral_count(user_id)
        if referral_count < 3:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Reminder: You haven't yet grabbed Language Group link.\n"
                    f"you are missing a lot of content"
                ),
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.exception(f"Error sending referral timeout message: {e}")


