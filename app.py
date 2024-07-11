from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import os
import openai
import vectorDB #import file vectorDB
import chatHistoryPrettifier #makes chat history look nice
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
        #response_text = openai_chat_send(question) #import hàm openai_chat_send từ file tts
        #get respose text from vectorDB
        response_text = vectorDB.chat(question, sessionID)
        print("OpenAI response:", response_text)
        # Convert response to speech
        response_audio = text_to_speech(response_text)
        
        return jsonify({'response_text': response_text, 'response_audio': response_audio})
    return render_template('chatbot.html')

@app.route('/mp3/<id>', methods=['GET'])
def mp3(id):
        audioFileName = id + ".mp3"
        directory = "AudioFolder/"+ audioFileName
        directory = os.path.normpath(directory)
        return send_file(directory, as_attachment=True)

#setting up drops
basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.normpath(basedir)
if not os.path.exists(os.path.join(basedir, 'sessions\\')):
    os.makedirs(os.path.join(basedir, 'sessions\\'))
#update the basedir to basedir/sessions/session_id/uploads folder
sessionID = 'abc123'#replace this with the session id
sessions = 'sessions\\' + sessionID
basedir = os.path.join(basedir, sessions)
basedir = os.path.normpath(basedir)
#check if directories exist, if not create them
if not os.path.exists(basedir):
    os.makedirs(basedir)
if not os.path.exists(os.path.join(basedir, '\\uploads')):
    os.makedirs(os.path.join(basedir, '\\uploads'))


app.config.update(
    UPLOADED_PATH=os.path.join(basedir, 'uploads'),
    # Flask-Dropzone config:
    DROPZONE_ALLOWED_FILE_TYPE='text',
    DROPZONE_MAX_FILE_SIZE=3,
    DROPZONE_MAX_FILES=30,
)

@app.route('/files', methods=['GET', 'POST'])
def upload():
    #check if directories exist, if not create them
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    if request.method == 'POST':
        f = request.files.get('file')
        if f:
            f.save(os.path.join(app.config['UPLOADED_PATH'], f.filename))
            return "File uploaded successfully", 200
        else:
            return "Could not read file", 400
    return render_template('newFiles.html')

@app.route('/files/list', methods=['GET'])
def list_files():
    #check if app confight uploade path exists, if not create it
    if not os.path.exists(app.config['UPLOADED_PATH']):
        os.makedirs(app.config['UPLOADED_PATH'])
    files = []
    for filename in os.listdir(app.config['UPLOADED_PATH']):
        file_path = os.path.join(app.config['UPLOADED_PATH'], filename)
        if os.path.isfile(file_path):
            files.append({
                'name': filename,
                'size': os.path.getsize(file_path)
            })
    return jsonify(files)

@app.route('/files/delete', methods=['DELETE'])
def delete_file():
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Filename not provided"}), 400

    file_path = os.path.join(app.config['UPLOADED_PATH'], filename)
    file_path = os.path.normpath(file_path)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    os.remove(file_path)
    return jsonify({"message": "File deleted successfully"}), 200

@app.route('/files/chatLoader', methods=['POST'])
def chatLoader():
    filepath = basedir + '\\uploads'
    filepath = os.path.normpath(filepath)

    vectorDB.embedAllInDirectiory(filepath, sessionID)
    return jsonify({'message': 'Files uploaded to VectorDB!'})

@app.route('/files/resetChat', methods=['POST'])
def chatReset():
    filepath = basedir + '\\uploads'
    filepath = os.path.normpath(filepath)
    try:
        vectorDB.deleteSession(sessionID)
    except:
        pass
    
    return jsonify({'message': 'ChatReset'})

@app.route('/files/historyDownload', methods=['POST'])
def historyDownload():
    #creates chat history
    pdfPath = os.path.normpath(basedir + '\\chat_history.pdf')
    filepath = vectorDB.chat_history_as_txt(sessionID)
    filepath = os.path.normpath(filepath)
    #makes chat history look nice
    chatHistoryPrettifier.convert_chat_to_pdf(filepath, pdfPath)
    #return filepath
    return send_from_directory(directory=basedir, path='chat_history.pdf', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)