import logging
import io
import tempfile
import os
import re
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
        "I will analyze it and log its nutritional info to a Google Sheet. You can also ask me questions like 'what did I eat today?'"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages to analyze food descriptions."""
    user_info = get_user_info(update)
    text = update.message.text
    logger.info(f"Received text for FOOD LOGGING from {user_info}: '{text}'")
    await process_request(update, {'type': 'text', 'data': text})

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles photo messages to analyze food images."""
    user_info = get_user_info(update)
    logger.info(f"Received photo for logging from {user_info}.")
    photo_file = await update.message.photo[-1].get_file()
    
    byte_buffer = io.BytesIO()
    await photo_file.download_to_memory(byte_buffer)
    byte_buffer.seek(0)
    
    await process_request(update, {'type': 'image', 'data': byte_buffer.getvalue()})

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles voice/audio messages to analyze food audio."""
    user_info = get_user_info(update)
    logger.info(f"Received audio for logging from {user_info}.")
    
    audio_source = update.message.voice or update.message.audio
    if not audio_source:
        await update.message.reply_text("Could not process the audio file.")
        return

    audio_file = await audio_source.get_file()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio_file:
        temp_file_path = temp_audio_file.name
        await audio_file.download_to_drive(custom_path=temp_file_path)

    try:
        await process_request(update, {'type': 'audio', 'data': temp_file_path})
    finally:
        os.remove(temp_file_path)

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles natural language queries about the food log."""
    user_info = get_user_info(update)
    query_text = update.message.text
    logger.info(f"Received QUERY from {user_info}: '{query_text}'")

    await update.message.reply_text("Thinking about your request, please wait...")

    try:
        # 1. Parse the query to get a date range
        date_range = gemini_client.parse_query(query_text)

        if not date_range or not date_range.get('start_date') or not date_range.get('end_date'):
            await update.message.reply_text("Sorry, I couldn't understand the date range in your request. Please try asking again (e.g., 'what did I eat today?' or 'show me my log from July 1 to July 5').")
            return
        
        start_date = date_range['start_date']
        end_date = date_range['end_date']
        logger.info(f"Gemini parsed date range for {user_info}: {start_date} to {end_date}")

        # 2. Get entries from Google Sheets
        gs_client = gsheets_client.get_gsheets_client()
        if not gs_client:
            await update.message.reply_text("Error: Could not connect to Google Sheets. Please check server logs.")
            return

        entries = gsheets_client.get_entries_by_date_range(gs_client, start_date, end_date)

        if entries is None:
            await update.message.reply_text("Sorry, I encountered an error while trying to read your food log.")
            return
        
        if not entries:
            await update.message.reply_text(f"I couldn't find any food logged between {start_date} and {end_date}.")
            return

        # 3. Process entries and create a summary
        logger.info(f"Processing {len(entries)} entries for {user_info} to create summary.")
        total_calories, total_protein, total_carbs, total_fat = 0, 0, 0, 0
        food_items = []

        for entry in entries:
            try:
                total_calories += int(entry.get('Calories', 0))
                total_protein += int(entry.get('Protein (g)', 0))
                total_carbs += int(entry.get('Carbs (g)', 0))
                total_fat += int(entry.get('Fat (g)', 0))
                food_items.append(entry.get('Food Item', 'Unknown Item'))
            except (ValueError, TypeError):
                logger.warning(f"Skipping entry with non-numeric macro values: {entry}")

        # 4. Format and send the response
        date_header = f"from *{start_date}* to *{end_date}*" if start_date != end_date else f"for *{start_date}*"
        food_list_str = '\n'.join([f"- {item}" for item in food_items])
        response_message = (
            f"Here is your food log summary {date_header}:\n\n"
            f"📊 *Total Macros*\n"
            f"  • *Calories:* {total_calories} kcal\n"
            f"  • *Protein:* {total_protein}g\n"
            f"  • *Carbs:* {total_carbs}g\n"
            f"  • *Fat:* {total_fat}g\n\n"
            f"🍎 *Logged Items*\n"
            f"{food_list_str}"
        )

        await update.message.reply_text(response_message, parse_mode='Markdown')
        logger.info(f"Sent food log summary to {user_info}.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during query processing for {user_info}: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

async def process_request(update: Update, content: dict):
    """Generic processor for all content types."""
    user_info = get_user_info(update)
    
    await update.message.reply_text("Analyzing, please wait...")

    try:
        # 1. Analyze with Gemini
        food_data = gemini_client.analyze_content(content)

        if not food_data or not food_data.get('food_item'):
            await update.message.reply_text("Sorry, I couldn't identify the food item. Please try again with a clearer description or image.")
            return
        
        logger.info(f"Gemini identified '{food_data.get('food_item')}' for {user_info}.")

        # 2. Append to Google Sheets
        gs_client = gsheets_client.get_gsheets_client()
        if not gs_client:
            await update.message.reply_text("Error: Could not connect to Google Sheets. Please check server logs.")
            return
        
        success = gsheets_client.append_food_entry(gs_client, food_data)

        # 3. Reply to user
        if success:
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
        else:
            await update.message.reply_text("I analyzed the food, but I failed to log it to Google Sheets. Please check server logs.")

    except Exception as e:
        logger.error(f"An unexpected error occurred while processing request for {user_info}: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred. Please try again later.")

def run():
    """Starts the Telegram bot."""
    logger.info("Setting up Telegram bot application...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))

    # Message handlers
    query_keywords = r'^(how|what|show|give|list|breakdown|summary)'
    query_filter = filters.TEXT & ~filters.COMMAND & filters.Regex(re.compile(query_keywords, re.IGNORECASE))
    application.add_handler(MessageHandler(query_filter, handle_query))

    log_filter = filters.TEXT & ~filters.COMMAND & ~query_filter
    application.add_handler(MessageHandler(log_filter, handle_text))
    
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))

    logger.info("Starting bot polling...")
    application.run_polling()
    logger.info("Bot has stopped polling.")