import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Union
import user_referral_system as urs
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import CommandHandler, CallbackContext, Application, MessageHandler, filters, CallbackQueryHandler
from telegram.error import RetryAfter, Forbidden, TelegramError

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class BroadcastConfig:
    ADMIN_USER_ID: int = 5250831809  # Replace with your admin ID
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 2.0
    RATE_LIMIT_DELAY: float = 0.05
    PROGRESS_UPDATE_INTERVAL: int = 50

class BroadcastState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.start_time: Optional[float] = None
        self.total_users: int = 0
        self.messages_sent: int = 0
        self.users_blocked: int = 0
        self.is_running: bool = False
        self.current_batch: int = 0

class BroadcastManager:
    def __init__(self, config: BroadcastConfig):
        self.config = config
        self.state = BroadcastState()
        self.pending_broadcasts: Dict[int, Message] = {}
        self.button_details: Dict[int, List[str]] = {}
        self.in_button_setup: Dict[int, bool] = {}

    def is_admin(self, user_id: int) -> bool:
        return user_id == self.config.ADMIN_USER_ID

    async def send_admin_message(self, context: CallbackContext, text: str) -> None:
        try:
            await context.bot.send_message(
                chat_id=self.config.ADMIN_USER_ID,
                text=text,
                parse_mode='HTML'
            )
        except TelegramError as e:
            logger.error(f"Failed to send admin message: {e}")

    async def send_with_retry(
        self,
        context: CallbackContext,
        user_id: int,
        message: Message,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        for attempt in range(self.config.MAX_RETRIES):
            try:
                await message.copy(
                    chat_id=user_id,
                    reply_markup=reply_markup
                )
                await asyncio.sleep(self.config.RATE_LIMIT_DELAY)
                return True
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after)
            except Forbidden:
                return False
            except TelegramError as e:
                if attempt == self.config.MAX_RETRIES - 1:
                    logger.error(f"Failed to send message to {user_id}: {e}")
                    return False
                await asyncio.sleep(self.config.RETRY_DELAY)
        return False

    def create_button_markup(self, button_details: List[str]) -> InlineKeyboardMarkup:
        keyboard = []
        for i in range(0, len(button_details), 2):
            if i + 1 < len(button_details):
                keyboard.append([
                    InlineKeyboardButton(button_details[i], url=button_details[i + 1])
                ])
        return InlineKeyboardMarkup(keyboard)

    async def broadcast_messages(
        self,
        context: CallbackContext,
        message: Message,
        button_details: Optional[List[str]]
    ) -> None:
        try:
            self.state.reset()
            self.state.is_running = True
            self.state.start_time = time.time()

            data = urs.load_data()
            if not data:
                await self.send_admin_message(context, "❌ Error loading user data")
                return

            users = data.get("users", {})
            self.state.total_users = len(users)
            users_to_remove = []
            reply_markup = self.create_button_markup(button_details) if button_details else None

            for batch_index, user_id in enumerate(users.keys()):
                self.state.current_batch = batch_index + 1

                success = await self.send_with_retry(
                    context,
                    int(user_id),
                    message,
                    reply_markup
                )

                if success:
                    self.state.messages_sent += 1
                else:
                    self.state.users_blocked += 1
                    users_to_remove.append(user_id)

                if self.state.current_batch % self.config.PROGRESS_UPDATE_INTERVAL == 0:
                    await self.send_progress_update(context)

            for user_id in users_to_remove:
                del users[user_id]

            data["users"] = users
            data["total_users"] = len(users)
            urs.save_data(data)

            await self.send_broadcast_summary(context)
        except Exception as e:
            logger.exception("Broadcast error")
            await self.send_admin_message(context, f"❌ Broadcast error: {str(e)}")
        finally:
            self.state.is_running = False

    async def send_progress_update(self, context: CallbackContext) -> None:
        if not self.state.is_running:
            return

        progress = (self.state.current_batch / self.state.total_users) * 100 if self.state.total_users > 0 else 0
        elapsed = time.time() - self.state.start_time
        rate = self.state.messages_sent / elapsed if elapsed > 0 else 0

        await self.send_admin_message(
            context,
            f"📊 Broadcast Progress:\n"
            f"Progress: {progress:.1f}%\n"
            f"Sent: {self.state.messages_sent}\n"
            f"Blocked: {self.state.users_blocked}\n"
            f"Rate: {rate:.1f} messages/sec"
        )

    async def send_broadcast_summary(self, context: CallbackContext) -> None:
        elapsed = time.time() - self.state.start_time
        rate = self.state.messages_sent / elapsed if elapsed > 0 else 0
        await self.send_admin_message(
            context,
            f"✅ Broadcast Complete\n\n"
            f"📊 Statistics:\n"
            f"Total Users: {self.state.total_users}\n"
            f"Messages Sent: {self.state.messages_sent}\n"
            f"Users Blocked: {self.state.users_blocked}\n"
            f"Time Taken: {elapsed:.1f}s\n"
            f"Average Rate: {rate:.1f} messages/sec"
        )

async def broadcast_start(update: Update, context: CallbackContext) -> None:
    if 'broadcast_manager' not in context.bot_data:
        config = BroadcastConfig()
        context.bot_data['broadcast_manager'] = BroadcastManager(config)

    manager = context.bot_data.get('broadcast_manager')

    if not manager:
        logger.error("Failed to initialize broadcast manager")
        await update.message.reply_text("❌ Internal error: Broadcast system not initialized properly")
        return

    if not manager.is_admin(update.effective_user.id):
        return

    if manager.state.is_running:
        await update.message.reply_text("⚠️ A broadcast is already running")
        return

    manager.pending_broadcasts[update.effective_user.id] = None
    manager.button_details[update.effective_user.id] = []
    manager.in_button_setup[update.effective_user.id] = False

    await update.message.reply_text(
        "📝 Please send the message you want to broadcast\n"
        "(text, photo, video, etc.)"
    )
    
async def receive_broadcast_message(update: Update, context: CallbackContext) -> None:
    manager = context.bot_data.get('broadcast_manager')
    
    if not manager:
        return

    user = update.effective_user

    if not manager.is_admin(user.id):
        return

    # Check if we're waiting for a broadcast message
    if user.id not in manager.pending_broadcasts:
        # Ignore messages if we're not in broadcast setup mode
        return

    # Handle button setup if we're in that mode
    if manager.in_button_setup.get(user.id, False):
        await handle_button_details(update, context)
        return

    # Store the message for broadcasting
    manager.pending_broadcasts[user.id] = update.message

    keyboard = [
        [
            InlineKeyboardButton("Add Button", callback_data="add_button"),
            InlineKeyboardButton("Confirm", callback_data="verify_broadcast"),
            InlineKeyboardButton("Cancel", callback_data="cancel_broadcast")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Send preview message
        preview_text = "📢 Broadcast Preview:"
        await context.bot.send_message(
            chat_id=user.id,
            text=preview_text
        )
        await update.message.copy(
            chat_id=user.id,
            reply_markup=reply_markup
        )
    except TelegramError as e:
        logger.error(f"Error creating broadcast preview: {e}")
        await update.message.reply_text("❌ Error creating preview. Please try again.")
        # Clean up the broadcast data
        manager.pending_broadcasts.pop(user.id, None)
        manager.button_details.pop(user.id, None)
        manager.in_button_setup.pop(user.id, None)

async def handle_button_details(update: Update, context: CallbackContext) -> None:
    manager = context.bot_data.get('broadcast_manager')
    
    if not manager:
        return

    user = update.effective_user
    message = update.message

    if not manager.is_admin(user.id):
        return

    button_details_text = message.text
    button_lines = button_details_text.strip().split('\n')

    if len(button_lines) % 2 != 0:
        await message.reply_text(
            "❌ Invalid button format. Please provide title and URL for each button on separate lines:\n\n"
            "Button 1 Title\n"
            "https://button1url.com\n"
            "Button 2 Title\n"
            "https://button2url.com"
        )
        return

    manager.button_details[user.id] = button_lines
    manager.in_button_setup[user.id] = False
    
    # Show preview with buttons
    message_to_broadcast = manager.pending_broadcasts.get(user.id)
    if message_to_broadcast:
        reply_markup = manager.create_button_markup(button_lines)
        try:
            preview_text = "📢 Preview with buttons:"
            await context.bot.send_message(
                chat_id=user.id,
                text=preview_text
            )
            await message_to_broadcast.copy(
                chat_id=user.id,
                reply_markup=reply_markup
            )
            
            # Add confirm/cancel buttons
            confirm_keyboard = [
                [
                    InlineKeyboardButton("✅ Send Broadcast", callback_data="verify_broadcast"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
                ]
            ]
            confirm_markup = InlineKeyboardMarkup(confirm_keyboard)
            
            await context.bot.send_message(
                chat_id=user.id,
                text="Please verify the message above and confirm to send.",
                reply_markup=confirm_markup
            )
        except TelegramError as e:
            logger.error(f"Error creating button preview: {e}")
            await message.reply_text("❌ Error creating preview. Please try again.")

async def handle_callback(update: Update, context: CallbackContext) -> None:
    manager = context.bot_data.get('broadcast_manager')
    
    if not manager:
        return

    query = update.callback_query
    await query.answer()

    if not manager.is_admin(query.from_user.id):
        return

    try:
        if query.data == "add_button":
            manager.in_button_setup[query.from_user.id] = True
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="Please send the button details in the following format:\n\n"
                "Button 1 Title\n"
                "https://button1url.com\n"
                "Button 2 Title\n"
                "https://button2url.com"
            )

        elif query.data == "verify_broadcast":
            message_to_broadcast = manager.pending_broadcasts.get(query.from_user.id)
            if message_to_broadcast:
                await manager.broadcast_messages(
                    context,
                    message_to_broadcast,
                    manager.button_details.get(query.from_user.id)
                )
                # Clean up after broadcast
                manager.pending_broadcasts.pop(query.from_user.id, None)
                manager.button_details.pop(query.from_user.id, None)
                manager.in_button_setup.pop(query.from_user.id, None)
            else:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="❌ No message to broadcast found."
                )

        elif query.data == "cancel_broadcast":
            # Clean up the broadcast data
            manager.pending_broadcasts.pop(query.from_user.id, None)
            manager.button_details.pop(query.from_user.id, None)
            manager.in_button_setup.pop(query.from_user.id, None)
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="✖️ Broadcast cancelled."
            )

    except TelegramError as e:
        logger.error(f"Error in callback handler: {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="❌ An error occurred. Please try again."
        )

async def handle_progress(update: Update, context: CallbackContext) -> None:
    manager = context.bot_data.get('broadcast_manager')
    
    if not manager:
        return

    if not manager.is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ You are not authorized to use this command.")
        return

    if not manager.state.is_running:
        await update.message.reply_text("ℹ️ No broadcast is currently running.")
        return

    await manager.send_progress_update(context)

def setup_broadcast_handler(application: Application) -> None:
    config = BroadcastConfig()
    manager = BroadcastManager(config)
    application.bot_data['broadcast_manager'] = manager

    # Command handler for starting broadcast
    application.add_handler(CommandHandler("broadcast", broadcast_start))
    
    # Message handler for broadcast content
    application.add_handler(MessageHandler(
        # Modified filter to better handle broadcast messages
        filters.ALL & 
        ~filters.COMMAND & 
        filters.ChatType.PRIVATE & 
        filters.User(manager.config.ADMIN_USER_ID),
        receive_broadcast_message,
        # Add this handler with higher priority
    ), group=1)
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Progress command handler
    application.add_handler(CommandHandler("progress", handle_progress))
