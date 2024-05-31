from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from gtts import gTTS
import openai
import os
import requests
from google.oauth2 import service_account
from google.cloud import storage
import uuid
from datetime import datetime

app = FastAPI()

# Load your API keys from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')
newsapi_key = os.getenv('NEWSAPI_KEY')
weatherapi_key = os.getenv('WEATHERAPI_KEY')

# Set up Google Cloud Storage credentials
credentials = service_account.Credentials.from_service_account_file('credentials.json')
bucket_name = 'langingo'  # Replace with your GCS bucket name

class GCPUploader:
    def __init__(self, credentials, bucket_name):
        self.storage_client = storage.Client(credentials=credentials)
        self.bucket_name = bucket_name

    def upload_to_gcs(self, file_path, file_name):
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(file_name)
        
        with open(file_path, 'rb') as file_obj:
            blob.upload_from_file(file_obj, content_type='audio/mp4')
        
        return f"https://storage.cloud.google.com/{self.bucket_name}/{file_name}"

class Responder:
    def __init__(self, openai_api_key, newsapi_key, weatherapi_key):
        openai.api_key = openai_api_key
        self.newsapi_key = newsapi_key
        self.weatherapi_key = weatherapi_key

    def get_france_news(self):
        url = f'https://newsapi.org/v2/top-headlines?country=fr&apiKey={self.newsapi_key}'
        response = requests.get(url)
        news_data = response.json()
        articles = news_data.get('articles', [])
        
        news_texts = [f"{article['title']}: {article['description']}" for article in articles[:5]]
        return " ".join(news_texts)

    def get_weather(self, city):
        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.weatherapi_key}&units=metric'
        response = requests.get(url)
        weather_data = response.json()
        description = weather_data['weather'][0]['description']
        temperature = weather_data['main']['temp']
        
        weather_summary = f"The current weather in {city} is {description} with a temperature of {temperature}°C."
        return weather_summary

    def get_time(self, city):
        url = f'http://worldtimeapi.org/api/timezone/{city}' 
        response = requests.get(url)
        print(response)
        time_data = response.json()
        print(time_data)
        current_time = time_data['datetime']
        time_summary = f"The current time in {city} is {current_time}."
        return time_summary

    def respond_in_french(self, question, summary=None):
        if summary:
            prompt = (
                f"Respond to the following question in French: {question}\n\n"
                f"Also, here is the information you requested: {summary}\n\n"
                "Also provide the English translation of the response.\n\n"
                "French:\n\nEnglish:"
            )
        else:
            prompt = (
                f"Respond to the following question in French: {question}\n\n"
                "Also provide the English translation of the response.\n\n"
                "French:\n\nEnglish:"
            )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=500
        )
        return response.choices[0].message.content

    def is_news_request(self, message):
        return "news" in message.lower() or "headlines" in message.lower() or "latest news" in message.lower() or "current events" in message.lower()

    def is_weather_request(self, message):
        return "weather" in message.lower()

    def is_time_request(self, message):
        return "time" in message.lower()

    def extract_city(self, message):
        words = message.split()
        for i, word in enumerate(words):
            if word.lower() in ["in", "at"]:
                if i + 1 < len(words):
                    return words[i + 1]
        return "Paris"  # default city

@app.post("/whatsapp")
async def whatsapp_reply(request: Request):
    msg = await request.form()
    message_body = msg.get('Body', '')

    responder = Responder(openai.api_key, newsapi_key, weatherapi_key)
    # gcp_uploader = GCPUploader(credentials, bucket_name)

    news_summary = weather_summary = time_summary = None

    if responder.is_news_request(message_body):
        news_text = responder.get_france_news()
        news_summary = f"Latest news: {news_text}"
    elif responder.is_weather_request(message_body):
        city = responder.extract_city(message_body)
        weather_summary = responder.get_weather(city)
    elif responder.is_time_request(message_body):
        city = responder.extract_city(message_body)
        time_summary = responder.get_time(city)
    
    if news_summary:
        response_summary = news_summary
    elif weather_summary:
        response_summary = weather_summary
    elif time_summary:
        response_summary = time_summary
    else:
        response_summary = None

    french_response = responder.respond_in_french(message_body, response_summary)

    # Generate a unique token with timestamp
    # token = uuid.uuid4()
    # timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # unique_filename = f"response_{token}_{timestamp}.mp4"
    # local_file_path = f"/tmp/{unique_filename}"  # Adjust the path if necessary

    # # Generate audio response using gTTS
    # tts = gTTS(text=french_response, lang='fr')
    # tts.save(local_file_path)

    # # Upload the audio file to Google Cloud Storage
    # audio_url = gcp_uploader.upload_to_gcs(local_file_path, unique_filename)

    # Create a Twilio MessagingResponse
    resp = MessagingResponse()
    resp.message(french_response)
    # message = resp.message(french_response)
    # message.media(url=audio_url, content_type="audio/mp4")

    # Clean up the audio file from local storage
    # os.remove(local_file_path)

    return Response(content=str(resp), media_type="application/xml")  # This ensures the response is correctly formatted for Twilio

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
