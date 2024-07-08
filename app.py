from flask import Flask, render_template, request, jsonify, send_file
import os
import openai
from dotenv import load_dotenv
from tts import openai_chat_send, text_to_speech

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        response_audio = text_to_speech(response_text)
        
        return jsonify({'response_text': response_text, 'response_audio': response_audio})
    return render_template('chatbot.html')

@app.route('/mp3/<id>', methods=['GET'])
def mp3(id):
        audioFileName = id + ".mp3"
        directory = "AudioFolder/"+ audioFileName
        return send_file(directory, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)