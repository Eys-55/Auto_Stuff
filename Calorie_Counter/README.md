# Telegram Food Logger Bot

This bot uses Telegram to receive food descriptions (text, photo, or audio), analyzes them with Google's Gemini 1.5 Flash to estimate nutritional information, and logs the data to a Google Sheet.

## Features

-   Log food via text message (e.g., "a bowl of oatmeal with berries").
-   Log food by sending a photo of your meal.
-   Log food by sending a voice message describing your meal.
-   Data is automatically appended to a specified Google Sheet.

## Project Structure

```
.
├── main.py               # Main application entry point
├── telegram_bot.py       # Handles Telegram bot interactions
├── gemini_client.py      # Handles communication with Gemini API
├── gsheets_client.py     # Handles communication with Google Sheets API
├── config.py             # Handles configuration and environment variables
├── requirements.txt      # Python dependencies
├── .env.example          # Example for environment variables
└── README.md             # This file
```

## Setup Instructions

### 1. Prerequisites

-   Python 3.8+
-   A Telegram Bot Token
-   A Google Cloud Project with Gemini API enabled
-   A Google Cloud Service Account with Google Sheets & Drive APIs enabled

### 2. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 3. Install Dependencies

It's recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 4. Configure Environment Variables

1.  Create a `.env` file in the root directory by copying the example:
    ```bash
    cp .env.example .env
    ```
2.  Edit the `.env` file with your credentials:
    -   `TELEGRAM_BOT_TOKEN`: Get this from the [BotFather](https://t.me/BotFather) on Telegram.
    -   `GEMINI_API_KEY`: Get this from [Google AI Studio](https://aistudio.google.com/app/apikey).
    -   `GOOGLE_SHEET_ID`: This is the long string in the URL of your Google Sheet. For `https://docs.google.com/spreadsheets/d/12345ABCDE/edit`, the ID is `12345ABCDE`.
    -   `GOOGLE_CREDENTIALS_FILE`: The path to your service account JSON key file. Defaults to `credentials.json`.

### 5. Set up Google Sheets API

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project (or use an existing one).
3.  Enable the **Google Sheets API** and **Google Drive API** for your project.
4.  Go to "Credentials", click "Create Credentials", and select "Service Account".
5.  Give it a name, grant it the "Editor" role for this project (or a more restricted role if you prefer).
6.  Once created, click on the service account, go to the "Keys" tab, click "Add Key", "Create new key", and choose **JSON**. A `credentials.json` file will be downloaded.
7.  Place this `credentials.json` file in the root of the project directory.
8.  Open your Google Sheet and share it with the service account's email address (found in the `client_email` field of your `credentials.json` file). Give it "Editor" permissions.

### 6. Run the Bot

```bash
python main.py
```

Your bot should now be running and responding to messages on Telegram.