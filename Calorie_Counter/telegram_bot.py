import logging
import io
import tempfile
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
import gemini_client
import gsheets_client

# Get logger
logger = logging.getLogger(__name__)

def get_user_info(update: Update) -> str:
    """Helper to get a consistent user identifier string for logging."""
    user = update.effective_user
    return f"user (ID: {user.id}, Name: {user.full_name}, Username: @{user.username})"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user_info = get_user_info(update)
    logger.info(f"Received /start command from {user_info}.")
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! "
        "Send me a description of food, a photo of a meal, or a voice message describing it. "
        "I will analyze it and log its nutritional info to a Google Sheet."
    )
    logger.debug(f"Sent welcome message to {user_info}.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages to analyze food descriptions."""
    user_info = get_user_info(update)
    text = update.message.text
    logger.info(f"Received text message from {user_info}: '{text}'")
    await process_request(update, {'type': 'text', 'data': text})

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles photo messages to analyze food images."""
    user_info = get_user_info(update)
    logger.info(f"Received photo message from {user_info}.")
    
    logger.debug("Getting photo file object from message...")
    photo_file = await update.message.photo[-1].get_file()
    logger.debug(f"Photo file object obtained. File ID: {photo_file.file_id}")
    
    # Download photo into a byte buffer
    byte_buffer = io.BytesIO()
    logger.debug("Downloading photo to in-memory buffer...")
    await photo_file.download_to_memory(byte_buffer)
    byte_buffer.seek(0)
    logger.info("Photo downloaded successfully to memory.")
    
    await process_request(update, {'type': 'image', 'data': byte_buffer.getvalue()})

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles voice/audio messages to analyze food audio."""
    user_info = get_user_info(update)
    logger.info(f"Received audio/voice message from {user_info}.")
    
    audio_source = update.message.voice or update.message.audio
    if not audio_source:
        logger.warning(f"Could not find audio source in message from {user_info}.")
        await update.message.reply_text("Could not process the audio file.")
        return

    logger.debug("Getting audio file object from message...")
    audio_file = await audio_source.get_file()
    logger.debug(f"Audio file object obtained. File ID: {audio_file.file_id}")

    # Create a temporary file to save the audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
        temp_file_path = temp_audio_file.name
        logger.debug(f"Created temporary file for audio: {temp_file_path}")
        await audio_file.download_to_drive(custom_path=temp_file_path)
        logger.info(f"Audio file downloaded successfully to {temp_file_path}")

    try:
        await process_request(update, {'type': 'audio', 'data': temp_file_path})
    finally:
        # Clean up the temporary file
        logger.debug(f"Cleaning up temporary audio file: {temp_file_path}")
        os.remove(temp_file_path)
        logger.debug("Temporary file removed.")

async def process_request(update: Update, content: dict):
    """Generic processor for all content types."""
    user_info = get_user_info(update)
    logger.info(f"Starting to process request for {user_info}. Content type: {content['type']}")
    
    await update.message.reply_text("Analyzing, please wait...")
    logger.debug(f"Sent 'Analyzing...' message to {user_info}.")

    try:
        # 1. Analyze with Gemini
        logger.info(f"Step 1: Sending content to Gemini for analysis for {user_info}.")
        food_data = gemini_client.analyze_content(content)

        if not food_data or not food_data.get('food_item'):
            logger.warning(f"Gemini analysis failed or returned no food item for {user_info}.")
            await update.message.reply_text("Sorry, I couldn't identify the food item. Please try again with a clearer description or image.")
            return
        
        logger.info(f"Gemini analysis successful for {user_info}. Food identified: {food_data.get('food_item')}")

        # 2. Append to Google Sheets
        logger.info(f"Step 2: Connecting to Google Sheets for {user_info}.")
        gs_client = gsheets_client.get_gsheets_client()
        if not gs_client:
            logger.error(f"Failed to get Google Sheets client for {user_info}. Check server logs.")
            await update.message.reply_text("Error: Could not connect to Google Sheets. Please check server logs.")
            return
        
        logger.info(f"Appending data to Google Sheets for {user_info}: {food_data}")
        success = gsheets_client.append_food_entry(gs_client, food_data)

        # 3. Reply to user
        logger.info(f"Step 3: Replying to {user_info}.")
        if success:
            logger.info(f"Google Sheets append was successful for {user_info}.")
            macros = food_data.get('macros', {})
            response_message = (
                f"Successfully logged!\n\n"
                f"• *Food:* {food_data.get('food_item', 'N/A')}\n"
                f"• *Calories:* {food_data.get('calories', 'N/A')} kcal\n"
                f"• *Protein:* {macros.get('protein', 'N/A')}g\n"
                f"• *Carbs:* {macros.get('carbohydrates', 'N/A')}g\n"
                f"• *Fat:* {macros.get('fat', 'N/A')}g"
            )
            await update.message.reply_text(response_message, parse_mode='Markdown')
            logger.debug(f"Sent success confirmation to {user_info}.")
        else:
            logger.error(f"Google Sheets append failed for {user_info}.")
            await update.message.reply_text("I analyzed the food, but I failed to log it to Google Sheets. Please check server logs.")

    except Exception as e:
        logger.error(f"An unexpected error occurred while processing request for {user_info}: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred. Please try again later.")


def run():
    """Starts the Telegram bot."""
    logger.info("Setting up Telegram bot application...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    logger.debug("Adding /start command handler.")
    application.add_handler(CommandHandler("start", start))

    # Message handlers
    logger.debug("Adding text message handler.")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.debug("Adding photo message handler.")
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.debug("Adding audio/voice message handler.")
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))

    logger.info("Starting bot polling...")
    application.run_polling()
    logger.info("Bot has stopped polling.")