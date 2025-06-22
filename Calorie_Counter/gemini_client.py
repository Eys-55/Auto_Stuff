import google.generativeai as genai
import logging
import json
from PIL import Image
import io

from config import GEMINI_API_KEY

# Get logger
logger = logging.getLogger(__name__)

# Configure the Gemini API client
logger.debug("Configuring Gemini API client...")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
logger.debug("Gemini API client configured for model 'gemini-1.5-flash'.")

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

def analyze_content(content):
    """
    Analyzes content (text, image, or audio) using Gemini and returns nutritional information.

    Args:
        content: A dictionary containing the type and data.
                 e.g., {'type': 'text', 'data': 'a cup of rice'}
                 e.g., {'type': 'image', 'data': <image_bytes>}
                 e.g., {'type': 'audio', 'data': <path_to_audio_file>}

    Returns:
        A dictionary with the parsed nutritional information or None on failure.
    """
    logger.info(f"Starting Gemini analysis for content type: {content['type']}")
    try:
        api_content = [PROMPT]
        if content['type'] == 'text':
            logger.debug(f"Preparing text content for Gemini: {content['data']}")
            api_content.append(content['data'])
        elif content['type'] == 'image':
            logger.debug(f"Preparing image content for Gemini. Image size: {len(content['data'])} bytes.")
            img = Image.open(io.BytesIO(content['data']))
            api_content.append(img)
        elif content['type'] == 'audio':
            logger.debug(f"Preparing audio content for Gemini. Uploading file: {content['data']}")
            audio_file = genai.upload_file(
                path=content['data'],
                display_name="user_audio"
            )
            api_content.append(audio_file)
            logger.debug(f"Audio file uploaded successfully: {audio_file.name}")
        else:
            logger.error(f"Unsupported content type for Gemini analysis: {content['type']}")
            return None

        logger.info("Sending request to Gemini API...")
        response = model.generate_content(api_content)
        logger.info("Received response from Gemini API.")
        
        # Clean up response text to extract JSON
        response_text = response.text.strip()
        logger.debug(f"Gemini raw response text: '{response_text}'")
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        logger.info(f"Cleaned Gemini response for JSON parsing: {response_text}")
        
        data = json.loads(response_text)
        logger.info(f"Successfully parsed JSON from Gemini response: {data}")
        return data

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from Gemini response. Response was: {response.text}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred with the Gemini API: {e}", exc_info=True)
        return None