import os
import json
import logging

logger = logging.getLogger(__name__)


def convert_user_data_if_needed(filename="users_data_converted.json"):
    """Creates or initializes a user data file if needed."""
    try:
        # Check if the user data file exists
        if not os.path.exists(filename):
            # Create a new file with empty user data structure
            with open(filename, "w") as f:
                json.dump({"users": {}, "total_users": 0}, f, indent=4)
            logger.info(f"Created new user data file: {filename}")
        else:
            # File exists, assume data is already in the new format
            logger.info(f"Using existing user data file: {filename}")
    except Exception as e:
        logger.exception(f"Error in convert_user_data_if_needed: {e}")