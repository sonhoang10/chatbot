import openai
import pyttsx3
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# File to store recordings
recordings_file = 'recordings.json'

# Load existing recordings
if os.path.exists(recordings_file):
    with open(recordings_file, 'r') as file:
        recordings = json.load(file)
else:
    recordings = []

# # Adjectives and nouns to generate random names for voices
# adjectives = ["beautiful", "sad", "mystical", "serene", "whispering", "gentle", "melancholic"]
# nouns = ["sea", "love", "dreams", "song", "rain", "sunrise", "silence", "echo"]

# Initializing pyttsx3 for text-to-speech output
engine = pyttsx3.init()
engine.setProperty('rate', 185)

def change_voice(engine, language, gender='VoiceGenderFemale'):
    voices = engine.getProperty('voices')
    for voice in voices:
        if language in voice.languages and gender == voice.gender:
            engine.setProperty('voice', voice.id)
            return True
    # print(f"Desired voice with language '{language}' and gender '{gender}' not found. Using default voice.")
    return False

# def list_available_voices(engine):
#     voices = engine.getProperty('voices')
#     for voice in voices:
#         print(f"ID: {voice.id}")
#         print(f"Name: {voice.name}")
#         print(f"Languages: {voice.languages}")
#         print(f"Gender: {voice.gender}")
#         print("-" * 20)

# List available voices for debugging purposes
# print("Available voices:")
# list_available_voices(engine)

# Try to change the voice
change_voice(engine, "en_US", "VoiceGenderFemale")
# def generate_random_name():
#     adjective = random.choice(adjectives)
#     noun = random.choice(nouns)
#     return f"{adjective} {noun}"

# def speech_to_text(audio_path):
#     print("entered transcribe", "./" + audio_path)
#     audio_file = open(audio_path, "rb")
#     print(audio_file)
#     transcript = openai.Audio.transcribe("whisper-1", audio_file)
#     print(transcript)
#     return transcript['text']

def text_to_speech(response):
    engine.say(response)
    engine.runAndWait()

def save_response_to_file(response, folder="responses"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    response_filename = os.path.join(folder, f"response_{len(os.listdir(folder)) + 1}.txt")
    with open(response_filename, 'w') as f:
        f.write(response)
    print(f"Response saved to {response_filename}")

def openai_chat_send(transcript):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": transcript}
    ]
    print("Transcript:", transcript)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    return completion.choices[0].message["content"]

def record_response(question, response):
    timestamp = datetime.now().isoformat()
    recording = {
        'timestamp': timestamp,
        'question': question,
        'response': response
    }
    recordings.append(recording)
    with open(recordings_file, 'w') as file:
        json.dump(recordings, file, indent=4)
    print(f"Recording saved: {recording}")


# question = input("Type your question: ")

# # Send user input to OpenAI ChatGPT
# response = openai_chat_send(question)

# # Print the assistant's response
# print("Assistant:", response)

# # Convert output to voice
# text_to_speech(response)

# # Record the response
# record_response(question, response)
