import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

# Conversation state for admin reply
REPLYING = 0

# Dictionary to store pending replies (key: admin message ID, value: user ID)
pending_replies = {}

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, admin_user_id):
    """Forwards user messages to the admin with a reply button."""
    try:
        user = update.effective_user
        user_id = user.id

        # Don't forward admin's own messages
        if user_id == admin_user_id:
            return

        # Prepare user info with proper formatting
        user_info = (
            f"👤 User Information:\n"
            f"ID: {user_id}\n"
            f"Username: @{user.username or 'N/A'}\n"
            f"Name: {user.first_name or 'N/A'}"
        )

        # Get caption if it exists
        caption = update.message.caption if update.message.caption else ""
        
        # If there's a caption, add it to user_info
        if caption:
            user_info = f"{user_info}\n\n💬 Message Caption:\n{caption}"

        # Create reply keyboard
        keyboard = [[InlineKeyboardButton("Reply", callback_data=f"reply_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Forward the message to the admin with user info and reply button
        if update.message.text:
            sent_message = await context.bot.send_message(
                chat_id=admin_user_id,
                text=f"{user_info}\n\n📝 Message:\n{update.message.text}",
                reply_markup=reply_markup
            )
        elif update.message.photo:
            sent_message = await context.bot.send_photo(
                chat_id=admin_user_id,
                photo=update.message.photo[-1].file_id,
                caption=user_info,
                reply_markup=reply_markup
            )
        elif update.message.video:
            sent_message = await context.bot.send_video(
                chat_id=admin_user_id,
                video=update.message.video.file_id,
                caption=user_info,
                reply_markup=reply_markup
            )
        elif update.message.document:
            sent_message = await context.bot.send_document(
                chat_id=admin_user_id,
                document=update.message.document.file_id,
                caption=user_info,
                reply_markup=reply_markup
            )
        elif update.message.sticker:
            # First send user info
            await context.bot.send_message(
                chat_id=admin_user_id,
                text=user_info
            )
            # Then send sticker
            sent_message = await context.bot.send_sticker(
                chat_id=admin_user_id,
                sticker=update.message.sticker.file_id,
                reply_markup=reply_markup
            )
        elif update.message.audio:
            sent_message = await context.bot.send_audio(
                chat_id=admin_user_id,
                audio=update.message.audio.file_id,
                caption=user_info,
                reply_markup=reply_markup,
                title=update.message.audio.title if update.message.audio.title else None,
                performer=update.message.audio.performer if update.message.audio.performer else None
            )
        elif update.message.voice:
            sent_message = await context.bot.send_voice(
                chat_id=admin_user_id,
                voice=update.message.voice.file_id,
                caption=user_info,
                reply_markup=reply_markup
            )
        elif update.message.animation:
            sent_message = await context.bot.send_animation(
                chat_id=admin_user_id,
                animation=update.message.animation.file_id,
                caption=user_info,
                reply_markup=reply_markup
            )
        elif update.message.contact:
            contact = update.message.contact
            contact_info = (
                f"{user_info}\n\n"
                f"📞 Contact Information:\n"
                f"Phone: {contact.phone_number}\n"
                f"Name: {contact.first_name}"
            )
            sent_message = await context.bot.send_message(
                chat_id=admin_user_id,
                text=contact_info,
                reply_markup=reply_markup
            )
        elif update.message.location:
            # First send user info
            await context.bot.send_message(
                chat_id=admin_user_id,
                text=user_info
            )
            # Then send location
            sent_message = await context.bot.send_location(
                chat_id=admin_user_id,
                latitude=update.message.location.latitude,
                longitude=update.message.location.longitude,
                reply_markup=reply_markup
            )
        elif update.message.venue:
            venue = update.message.venue
            venue_info = (
                f"{user_info}\n\n"
                f"📍 Venue Information:\n"
                f"Title: {venue.title}\n"
                f"Address: {venue.address}"
            )
            # First send venue info
            await context.bot.send_message(
                chat_id=admin_user_id,
                text=venue_info
            )
            # Then send location
            sent_message = await context.bot.send_location(
                chat_id=admin_user_id,
                latitude=venue.location.latitude,
                longitude=venue.location.longitude,
                reply_markup=reply_markup
            )
        elif update.message.poll:
            sent_message = await context.bot.send_message(
                chat_id=admin_user_id,
                text=f"{user_info}\n\nUser sent a poll.",
                reply_markup=reply_markup
            )
        else:
            sent_message = await context.bot.send_message(
                chat_id=admin_user_id,
                text=f"{user_info}\n\nUnsupported message type received.",
                reply_markup=reply_markup
            )

        # Store the message ID for reply handling
        pending_replies[sent_message.message_id] = user_id

    except Exception as e:
        logger.exception(f"Error forwarding message to admin: {e}")
        try:
            await context.bot.send_message(
                chat_id=admin_user_id,
                text=f"⚠️ Error forwarding message: {str(e)}"
            )
        except:
            pass

async def reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the admin's reply callback."""
    query = update.callback_query
    await query.answer()

    admin_message_id = query.message.message_id
    user_id = pending_replies.get(admin_message_id)

    if user_id:
        context.user_data["replying_to"] = user_id
        await query.message.reply_text(
            "Please enter your reply message:\n"
            "(Send /cancel to cancel the reply)"
        )
        return REPLYING
    else:
        await query.message.reply_text("This message is no longer available for reply.")
        return ConversationHandler.END

async def send_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the admin's reply to the user."""
    try:
        user_id = context.user_data.pop("replying_to", None)
        if user_id:
            reply_text = update.message.text
            await context.bot.send_message(
                chat_id=user_id,
                text=reply_text
            )
            await update.message.reply_text("✅ Reply sent successfully!")
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ No user to reply to.")
            return ConversationHandler.END
    except Exception as e:
        logger.exception(f"Error sending reply to user: {e}")
        await update.message.reply_text("❌ Failed to send reply. Please try again.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the reply conversation."""
    context.user_data.pop("replying_to", None)
    await update.message.reply_text("Reply cancelled.")
    return ConversationHandler.END
