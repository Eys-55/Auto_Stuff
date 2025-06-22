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
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, SCOPES)
        client = gspread.authorize(creds)
        return client
    except FileNotFoundError:
        logger.error(f"Google credentials file not found at: {GOOGLE_CREDENTIALS_FILE}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Failed to authorize Google Sheets client: {e}", exc_info=True)
        return None

def append_food_entry(client, food_data):
    """Appends a food entry to the Google Sheet."""
    if not client:
        logger.error("gspread client is not initialized. Cannot append entry.")
        return False
        
    try:
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        
        expected_header = ["Date", "Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]
        
        all_values = sheet.get_all_values()

        # Ensure header row exists and is correct
        if not all_values:
            sheet.append_row(expected_header)
            logger.info("Created header row in Google Sheet.")
        elif all_values[0] != expected_header:
            logger.error(
                f"Google Sheet header is incorrect. "
                f"Expected: {expected_header}, but found: {all_values[0]}. "
                "Please fix the header in your Google Sheet. Not logging entry."
            )
            return False

        # Prepare row data
        row_to_insert = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            food_data.get('food_item', 'N/A'),
            food_data.get('calories', 'N/A'),
            food_data.get('macros', {}).get('protein', 'N/A'),
            food_data.get('macros', {}).get('carbohydrates', 'N/A'),
            food_data.get('macros', {}).get('fat', 'N/A')
        ]
        
        sheet.append_row(row_to_insert)
        logger.info(f"Successfully appended entry for '{food_data.get('food_item')}' to Google Sheet.")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet with ID '{GOOGLE_SHEET_ID}' not found or access denied.", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Failed to append row to Google Sheet: {e}", exc_info=True)
        return False

def get_entries_by_date_range(client, start_date_str: str, end_date_str: str):
    """Fetches and filters food entries from the Google Sheet based on a date range."""
    logger.info(f"Fetching GSheet entries from {start_date_str} to {end_date_str}")
    if not client:
        logger.error("gspread client is not initialized. Cannot fetch entries.")
        return None

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        all_values = sheet.get_all_values()

        if not all_values:
            logger.info("The Google Sheet is empty. No entries to process.")
            return []

        header = all_values[0]
        expected_header = ["Date", "Food Item", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)"]
        if header != expected_header:
            logger.error(f"Google Sheet header is incorrect! Expected: {expected_header}, but found: {header}. Cannot process entries. Please fix the header in your Google Sheet.")
            return None # Return None to indicate an error state

        records = [dict(zip(header, row)) for row in all_values[1:]]

        filtered_entries = []
        for record in records:
            try:
                entry_date_str = record.get("Date")
                if not entry_date_str:
                    logger.warning(f"Skipping row because 'Date' column is missing or empty. Record: {record}")
                    continue
                
                entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d %H:%M:%S").date()

                if start_date <= entry_date <= end_date:
                    filtered_entries.append(record)
            
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse date for record, skipping. Record: {record}, Error: {e}")
                continue
        
        logger.info(f"Found {len(filtered_entries)} entries within the specified date range.")
        return filtered_entries

    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet with ID '{GOOGLE_SHEET_ID}' not found or access denied.", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Failed to get entries from Google Sheet: {e}", exc_info=True)
        return None