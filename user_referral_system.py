import json
import logging

logger = logging.getLogger(__name__)

def load_data(filename="users_data_converted.json"):
    """Loads user data from a JSON file."""
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        logger.warning(f"File {filename} not found. Creating a new one.")
        return {"users": {}, "total_users": 0}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {filename}. Creating a new one.")
        return {"users": {}, "total_users": 0}
    except Exception as e:
        logger.exception(f"Error loading data: {e}")
        return None

def save_data(data, filename="users_data_converted.json"):
    """Saves user data to a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.exception(f"Error saving data: {e}")

def manage_user(user_id, username, referred_by=None):
    """Manages user data and referral counts. Returns True if this is a new user."""
    data = load_data()
    if data is None:
        return False

    users = data.get("users", {})
    total_users = data.get("total_users", 0)

    user_id_str = str(user_id)
    is_new_user = user_id_str not in users

    if is_new_user:
        users[user_id_str] = {
            "username": username,
            "referral_count": 0,
            "referred_by": None
        }
        total_users += 1
        data["total_users"] = total_users

    if referred_by and is_new_user:  # Only process referral if it's a new user
        referred_by_str = str(referred_by)
        if referred_by_str in users:
            users[referred_by_str]["referral_count"] += 1
            users[user_id_str]["referred_by"] = int(referred_by)
        else:
            logger.warning(f"Referrer {referred_by} not found.")

    data["users"] = users
    save_data(data)
    return is_new_user

def get_referral_count(user_id):
    """Gets the referral count for a user."""
    data = load_data()
    if data is None:
        return 0

    users = data.get("users", {})
    user = users.get(str(user_id))

    if user:
        return user.get("referral_count", 0)
    else:
        return 0

def get_total_user_count():
    """Gets the total number of registered users."""
    data = load_data()
    if data is None:
        return 0

    return data.get("total_users", 0)