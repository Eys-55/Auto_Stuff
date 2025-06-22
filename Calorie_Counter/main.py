import logging
import os
from telegram_bot import run
from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE
import gsheets_client

# Get logger
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("=======================================")
    logger.info("===== Food Logger Bot Initializing =====")
    logger.info("=======================================")

    # Pre-flight checks for environment variables
    logger.info("Performing pre-flight checks...")
    if not all([TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, GOOGLE_SHEET_ID]):
        logger.critical("CRITICAL: One or more core environment variables are missing.")
        logger.critical("Please check your .env file for TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, GOOGLE_SHEET_ID.")
        exit(1)
    
    logger.debug(f"TELEGRAM_BOT_TOKEN is set: {'Yes' if TELEGRAM_BOT_TOKEN else 'No'}")
    logger.debug(f"GEMINI_API_KEY is set: {'Yes' if GEMINI_API_KEY else 'No'}")
    logger.debug(f"GOOGLE_SHEET_ID: {GOOGLE_SHEET_ID}")
    logger.debug(f"GOOGLE_CREDENTIALS_FILE: {GOOGLE_CREDENTIALS_FILE}")

    # Check for credentials file
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        logger.critical(f"CRITICAL: Google credentials file '{GOOGLE_CREDENTIALS_FILE}' not found. Exiting.")
        exit(1)
    
    logger.info("Environment variables and credentials file seem to be in place.")

    # Test GSheets connection once at startup
    logger.info("Attempting to connect to Google Sheets to verify credentials...")
    gs_client = gsheets_client.get_gsheets_client()
    if not gs_client:
        logger.critical("CRITICAL: Could not establish connection with Google Sheets. Check credentials and API access. Exiting.")
        exit(1)
    
    logger.info("Successfully connected to Google Sheets.")
    logger.info("Configuration and connections seem OK. Starting bot.")
    
    run()