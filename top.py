from telegram import Update
from telegram.ext import ContextTypes
import json

ADMIN_USER_ID = 5250831809  # Replace with your actual admin user ID

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
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