import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE
from datetime import datetime

# Get logger
logger = logging.getLogger(__name__)

# Scopes for Google Sheets and Drive API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

def get_gsheets_client():
    """Initializes and returns the gspread client."""
    logger.info("Initializing Google Sheets client...")
    try:
        logger.debug(f"Loading credentials from file: {GOOGLE_CREDENTIALS_FILE}")
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, SCOPES)
        logger.debug("Credentials loaded successfully.")
        
        logger.info("Authorizing Google Sheets client...")
        client = gspread.authorize(creds)
        logger.info("Google Sheets client authorized successfully.")
        return client
    except FileNotFoundError:
        logger.error(f"Google credentials file not found at: {GOOGLE_CREDENTIALS_FILE}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Failed to authorize Google Sheets client: {e}", exc_info=True)
        return None

def append_food_entry(client, food_data):
    """Appends a food entry to the Google Sheet."""
    logger.info("Attempting to append food entry to Google Sheet.")
    if not client:
        logger.error("gspread client is not initialized. Cannot append entry.")
        return False
        
    try:
        logger.debug(f"Opening spreadsheet with ID: {GOOGLE_SHEET_ID}")
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        logger.info(f"Successfully opened worksheet: '{sheet.title}'")
        
        # Ensure header row exists
        if not sheet.get_all_values():
            logger.info("Sheet is empty. Creating header row.")
            header = ["Date", "Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]
            sheet.append_row(header)
            logger.info("Created header row in Google Sheet.")

        # Prepare row data
        row_to_insert = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            food_data.get('food_item', 'N/A'),
            food_data.get('calories', 'N/A'),
            food_data.get('macros', {}).get('protein', 'N/A'),
            food_data.get('macros', {}).get('carbohydrates', 'N/A'),
            food_data.get('macros', {}).get('fat', 'N/A')
        ]
        
        logger.debug(f"Row to be inserted: {row_to_insert}")
        sheet.append_row(row_to_insert)
        logger.info(f"Successfully appended entry for '{food_data.get('food_item')}' to Google Sheet.")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet with ID '{GOOGLE_SHEET_ID}' not found or access denied.", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Failed to append row to Google Sheet: {e}", exc_info=True)
        return False