import google.generativeai as genai
import logging
import json
from PIL import Image
import io
from datetime import date

from config import GEMINI_API_KEY

# Get logger
logger = logging.getLogger(__name__)

# Configure the Gemini API client
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

PROMPT = """
Analyze the food item from the provided text, image, or audio.
Your response MUST be a single, minified JSON object with no other text before or after it.
The JSON object should have the following structure:
{
  "food_item": "Name of the food",
  "calories": <total_calories_as_integer>,
  "macros": {
    "protein": <protein_in_grams_as_integer>,
    "carbohydrates": <carbs_in_grams_as_integer>,
    "fat": <fat_in_grams_as_integer>
  }
}
If you cannot determine the food item or its nutritional information from the input,
return a JSON object with null values for all fields.
Example for "an apple":
{"food_item":"Apple","calories":95,"macros":{"protein":0,"carbohydrates":25,"fat":0}}
"""

QUERY_PROMPT_TEMPLATE = """
You are an intelligent assistant that parses user queries about their food log.
Analyze the user's text and determine the date range they are asking about.
Your response MUST be a single, minified JSON object with "start_date" and "end_date" in "YYYY-MM-DD" format.

- "today": set both start_date and end_date to today's date.
- "yesterday": set both start_date and end_date to the date for yesterday.
- "this week": set start_date to the most recent Monday and end_date to today.
- "this month": set start_date to the 1st of the current month and end_date to today.
- If only one date is mentioned, set both start_date and end_date to that date.
- Today's date is {current_date}.

Example for a query about today:
User query: "how many calories did I eat today"
Response: {{"start_date":"{current_date}","end_date":"{current_date}"}}

Example for a specific date range:
User query: "show me everything from jan 12 to jan 16"
Response: {{"start_date":"2024-01-12","end_date":"2024-01-16"}}

Example for a single past date:
User query: "what did I eat on march 5th 2023"
Response: {{"start_date":"2023-03-05","end_date":"2023-03-05"}}

If you cannot determine a date range from the query, return null for both fields.
User query: "what is the meaning of life"
Response: {{"start_date":null,"end_date":null}}
"""

def analyze_content(content):
    """
    Analyzes content (text, image, or audio) using Gemini and returns nutritional information.
    """
    logger.info(f"Starting Gemini analysis for content type: {content['type']}")
    try:
        api_content = [PROMPT]
        if content['type'] == 'text':
            api_content.append(content['data'])
        elif content['type'] == 'image':
            img = Image.open(io.BytesIO(content['data']))
            api_content.append(img)
        elif content['type'] == 'audio':
            audio_file = genai.upload_file(
                path=content['data'],
                display_name="user_audio"
            )
            api_content.append(audio_file)
        else:
            logger.error(f"Unsupported content type for Gemini analysis: {content['type']}")
            return None

        response = model.generate_content(api_content)
        
        # Clean up response text to extract JSON
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        data = json.loads(response_text)
        logger.info(f"Successfully parsed Gemini response: {data}")
        return data

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from Gemini response. Response was: {response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred with the Gemini API: {e}", exc_info=True)
        return None

def parse_query(user_query: str):
    """
    Parses a natural language query to extract a date range using Gemini.
    """
    logger.info(f"Starting query parsing for: '{user_query}'")
    try:
        current_date_str = date.today().strftime("%Y-%m-%d")
        prompt = QUERY_PROMPT_TEMPLATE.format(current_date=current_date_str)
        api_content = [prompt, user_query]
        
        response = model.generate_content(api_content)
        
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        data = json.loads(response_text)
        logger.info(f"Successfully parsed query response: {data}")
        return data

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from Gemini query response. Response was: {response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during query parsing: {e}", exc_info=True)
        return None