from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from gtts import gTTS
import openai
import os
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.cloud import storage
import uuid
from datetime import datetime
from tqdm import tqdm

app = FastAPI()

# Load your API keys from environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')
newsapi_key = os.getenv('NEWSAPI_KEY')
weatherapi_key = os.getenv('WEATHERAPI_KEY')

# Set up Google Drive API credentials
credentials = service_account.Credentials.from_service_account_file('credentials.json')
storage_client = storage.Client(credentials=credentials)
bucket_name = 'langingo'  # Replace with your GCS bucket name

def get_france_news():
    url = f'https://newsapi.org/v2/top-headlines?country=fr&apiKey={newsapi_key}'
    response = requests.get(url)
    news_data = response.json()
    articles = news_data.get('articles', [])
    
    news_texts = [f"{article['title']}: {article['description']}" for article in articles[:5]]
    print(news_texts)
    
    return " ".join(news_texts)

def get_weather(city):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weatherapi_key}&units=metric'
    response = requests.get(url)
    weather_data = response.json()
    description = weather_data['weather'][0]['description']
    temperature = weather_data['main']['temp']
    
    weather_summary = f"The current weather in {city} is {description} with a temperature of {temperature}°C."
    return weather_summary

def get_time(city):
    url = f'http://worldtimeapi.org/api/timezone/{city}'
    response = requests.get(url)
    time_data = response.json()
    datetime = time_data['datetime']
    time_summary = f"The current time in {city} is {datetime}."
    return time_summary

def respond_in_french(question, summary=None):
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

def is_news_request(message):
    return "news" in message.lower() or "headlines" in message.lower() or "latest news" in message.lower() or "current events" in message.lower()

def is_weather_request(message):
    return "weather" in message.lower()
 
def is_time_request(message):
    return "time" in message.lower()

def extract_city(message):
    words = message.split()
    for i, word in enumerate(words):
        if word.lower() in ["in", "at"]:
            if i + 1 < len(words):
                return words[i + 1]
    return "Paris"  # default city

def upload_to_gcs(file_path, file_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    
    with open(file_path, 'rb') as file_obj:
        blob.upload_from_file(file_obj, content_type='audio/mp4')
    
    return f"https://storage.cloud.google.com/{bucket_name}/{file_name}"


@app.post("/whatsapp")
async def whatsapp_reply(request: Request):

    msg = await request.form()
    message_body = msg.get('Body', '')

    news_summary = weather_summary = time_summary = None

    if is_news_request(message_body):
        news_text = get_france_news()
        news_summary = f"Latest news: {news_text}"
    elif is_weather_request(message_body):
        city = extract_city(message_body)
        weather_summary = get_weather(city)
    elif is_time_request(message_body):
        city = extract_city(message_body)
        time_summary = get_time(city)
    
    if news_summary:
        response_summary = news_summary
    elif weather_summary:
        response_summary = weather_summary
    elif time_summary:
        response_summary = time_summary
    else:
        response_summary = None

    french_response = respond_in_french(message_body, response_summary)

    # resp = MessagingResponse()
    # resp.message(french_response)

    # return Response(content=str(resp), media_type="application/xml")

    # Generate a unique token with timestamp
    token = uuid.uuid4()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"response_{token}_{timestamp}.mp4"
    local_file_path = f"/tmp/{unique_filename}"  # Adjust the path if necessary

    # Generate audio response using gTTS
    tts = gTTS(text=french_response, lang='fr')
    tts.save(local_file_path)

    # Upload the audio file to Google Cloud Storage
    audio_url = upload_to_gcs(local_file_path, unique_filename)

    # Create a Twilio MessagingResponse
    resp = MessagingResponse()
    message = resp.message(french_response)
    # message.media(url=audio_url, content_type="audio/mp4")

    # # Construct the TwiML response
    # twiml_response = f"""
    # <?xml version="1.0" encoding="UTF-8"?>
    # <Response>
    #     <Message>
    #         {french_response}
    #         <Media url="{audio_url}" content-type="audio/mpeg"/>
    #     </Message>
    # </Response>
    # """

    # Clean up the audio file from local storage
    os.remove(local_file_path)

    return Response(content=str(resp), media_type="application/xml")  # This ensures the response is correctly formatted for Twilio



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
