from flask import Flask, render_template, request, jsonify
import os
import openai
from dotenv import load_dotenv
from tts import openai_chat_send, text_to_speech, record_response

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        data = request.get_json()
        # print("Received data:", data)  # Debug print
        question = data.get('question')
        print("Question received:", question)  # Debug print
        
        # Generate a response using OpenAI
        response = openai_chat_send(question)
        print(response)
        # Convert response to speech
        # text_to_speech(response) #tạm hide để làm xong tải câu trl trc đã
        
        # Record the response
        # record_response(question, response) #tạm hide để làm xong tải câu trl trc đã
        
        return jsonify({'response': response})
    return render_template('chatbot.html')

@app.route('/hello')
def index():
    return '12334'

if __name__ == '__main__':
    app.run(debug=True)