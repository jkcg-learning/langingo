# Langingo

Langingo is an AI assistant integrated with WhatsApp designed to help you improve your French language skills. You can ask queries in English, and the Large Language Model (LLM) will respond to you in French, with an English translation of the response. An audio version of the response will also be provided.

## Features

- Responds to queries in French with an English translation.
- Provides audio responses in French.
- Fetches the latest news from France.
- Provides weather updates for specified cities.
- Gives the current time in specified cities.

## Getting Started

### Prerequisites

- Python 3.8+
- Google Cloud SDK
- Twilio account
- OpenAI API key
- NewsAPI key
- OpenWeatherMap API key

### Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/jkcg-learning/langingo.git
   cd langingo

2. **Clone the repository:**

   ```sh
   python -m venv venv
   source venv/bin/activate 
   pip install -r requirements.txt

3. **Set up environment variables:**

Create a .env file in the project root and add your API keys:

    OPENAI_API_KEY=your_openai_api_key
    NEWSAPI_KEY=your_newsapi_key
    WEATHERAPI_KEY=your_weatherapi_key

4. **Set up Google Cloud credentials:**

Ensure you have a credentials.json file with your Google Cloud service account credentials and store it in the project root.

5. **Run the application:**

    ```sh
    uvicorn server:app --host 0.0.0.0 --port 8000

6. **Expose the local server to public IP using ngrok:**

    ```sh
    ngrok http 8000   

7. **Setting Up Twilio:**

Create a Twilio account and get a WhatsApp sandbox:

- Sign up for a Twilio account if you don't already have one.

- Go to the Twilio Console and navigate to the WhatsApp sandbox.

- Configure the WhatsApp sandbox:

- Set the "WHEN A MESSAGE COMES IN" URL to http://localhost:8000/whatsapp for your local testing or use your deployed server URL from ngrok


8. **Test the application:**

Send a WhatsApp message to your Twilio sandbox number.

The application should respond in French with an English translation and provide an audio file of the response.

Example Requests

To test the application locally, you can use tools like curl or Postman to send POST requests to the /whatsapp endpoint. Example using curl:

curl -X POST http://localhost:8000/whatsapp -d "Body=What is the weather in Paris?"




