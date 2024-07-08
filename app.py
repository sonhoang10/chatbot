from flask import Flask, render_template, request,redirect, jsonify, send_file
from dotenv import load_dotenv
<<<<<<< HEAD
from tts import openai_chat_send, text_to_speech
=======
from tts import openai_chat_send, text_to_speech, record_response
import speech_recognition as sr #needs PyAudio, SpeechRecognition, setuptools, and pocketsphinx
>>>>>>> d975d2fa4e3dc4473c2605de08b6b10344668b85

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        data = request.get_json()
        # print("Received data:", data)  # Debug print
        question = data.get('question')
        
        # Generate a response using OpenAI
        response_text = openai_chat_send(question) #import hàm openai_chat_send từ file tts
        print("OpenAI response:", response_text)
        # Convert response to speech
        # text_to_speech(response) #tạm hide để làm xong tải câu trl trc đã
        response_audio = text_to_speech(response_text)
        
        return jsonify({'response_text': response_text, 'response_audio': response_audio})
    return render_template('chatbot.html')

<<<<<<< HEAD
@app.route('/mp3/<id>', methods=['GET'])
def mp3(id):
        audioFileName = id + ".mp3"
        directory = "AudioFolder/"+ audioFileName
        return send_file(directory, as_attachment=True)
=======

@app.route('/mp3', methods=['GET', 'POST'])
def mp3():
    if request.method == 'GET':
        return send_file("test.mp3", as_attachment=True)
    
>>>>>>> d975d2fa4e3dc4473c2605de08b6b10344668b85

if __name__ == '__main__':
    app.run(debug=True)