from flask import Flask, render_template, request,redirect, jsonify, send_file
from dotenv import load_dotenv
from tts import openai_chat_send, text_to_speech, record_response
import speech_recognition as sr #needs PyAudio, SpeechRecognition, setuptools, and pocketsphinx

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        data = request.get_json()
        # print("Received data:", data)  # Debug print
        question = data.get('question')
        print("Question received:", question)  # Debug print
        
        # Generate a response using OpenAI
        response_text = openai_chat_send(question) #import hàm openai_chat_send từ file tts
        print("OpenAI response:", response_text)
        # Convert response to speech
        # text_to_speech(response) #tạm hide để làm xong tải câu trl trc đã
        response_audio = text_to_speech(response_text)
        
        return jsonify({'response_text': response_text, 'response_audio': response_audio})
    return render_template('chatbot.html')


@app.route('/mp3', methods=['GET', 'POST'])
def mp3():
    if request.method == 'GET':
        return send_file("test.mp3", as_attachment=True)
    

if __name__ == '__main__':
    app.run(debug=True)