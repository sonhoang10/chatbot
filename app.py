from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response
import os
import openai
import vectorDB  # import file vectorDB
import json
import chatHistoryPrettifier  # makes chat history look nice
from dotenv import load_dotenv
#from tts import text_to_speech
from vnTTS import VNTTS
import asyncio
from queue import Queue
from threading import Thread

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
sessionID = 'abc123' #default sessionID
modelDir = os.path.join(basedir, "model")
outputDir = os.path.join(basedir, "sessions", sessionID, "AudioFolder")
ttsModel = VNTTS(model_dir=modelDir, output_dir=outputDir)
try:
    for message in ttsModel.load_model(modelDir):
        print(message)
except:
    ttsModel.setup(modelDir)
    for message in ttsModel.load_model(modelDir):
        print(message)

#setting up drops
def setup_session_dir(sessionID = 'abc123'):
    basedir = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'sessions\\')) #gets the current directory
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    #update the basedir to basedir/sessions/session_id/uploads folder
    sessions = sessionID
    basedir = os.path.normpath(os.path.join(basedir, sessions)) #gets directory of the session
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
    return basedir

#set up chatbot model
basedir = setup_session_dir("abc123")
store = {} #session storage for history
background = False

sessionDir = vectorDB.setup_session_dir(sessionID)
try:
    db = vectorDB.Chroma(persist_directory=sessionDir, embedding_function=vectorDB.OpenAIEmbeddings())
except:
    db = vectorDB.Chroma.from_texts([], persist_directory=sessionDir, embedding_function=vectorDB.OpenAIEmbeddings())

chain = vectorDB.createChain(db)
ragChain = vectorDB.chatResponseChain(chain)
store[sessionID] = ragChain



@app.route('/', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        data = request.get_json()
        question = data.get('question')
        sessionID = data.get('sessionID', 'abc123')

        def async_to_sync(generator_func):
            def sync_generator(*args, **kwargs):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                gen = generator_func(*args, **kwargs)
                q = Queue()

                def enqueue_data():
                    not_done = True
                    while not_done:
                        try:
                            item = loop.run_until_complete(gen.__anext__())
                            q.put(item)
                        except StopAsyncIteration:
                            not_done = False
                    q.put(StopIteration)

                thread = Thread(target=enqueue_data)
                thread.start()

                while True:
                    item = q.get()
                    if item == StopIteration:
                        break
                    if isinstance(item, list):
                        metadata = item[0]
                    else:
                        yield item

                loop.call_soon_threadsafe(loop.stop)
                thread.join()

            return sync_generator


        def get_chain_for_session(sessionID):
            sessionDir = vectorDB.setup_session_dir(sessionID)
            if sessionID in store:
                return store[sessionID]

            try:
                db = vectorDB.Chroma(persist_directory=sessionDir, embedding_function=vectorDB.OpenAIEmbeddings())
            except:
                db = vectorDB.Chroma.from_texts([], persist_directory=sessionDir, embedding_function=vectorDB.OpenAIEmbeddings())

            chain = vectorDB.createChain(db)
            ragChain = vectorDB.chatResponseChain(chain)
            store[sessionID] = ragChain
            return ragChain

        # Get or create the chain for the session
        ragChain = get_chain_for_session(sessionID)

        @async_to_sync
        async def generate(question, sessionID, ragChain):
            async for chunk in vectorDB.chat(question, sessionID, ragChain):
                if isinstance(chunk, list):
                    metadata = chunk[0]
                    continue
                json_data = json.dumps({'sender': 'bot', 'content': chunk})
                #check if the json content has the word null
                if 'null' not in json_data:
                    yield f"data: {json_data}\n\n"

        return Response(generate(question, sessionID, ragChain), mimetype='text/event-stream', content_type='text/event-stream')

    return render_template('chatbot.html', background = background)

@app.route('/tts', methods=['POST'])
def audioReturn():
    data = request.get_json()
    answer = data.get('answer')
    directory = os.path.normpath((basedir + '\\AudioFolder\\'))
    if not os.path.exists(directory):
        os.makedirs(directory)
    id = ttsModel.text_to_speech(answer) #returns audioId of the audio file
    return jsonify({'message': 'Audio file created!', 'audioId': id})

@app.route('/mp3/<id>', methods=['GET'])
def mp3(id):
        audioFileName = id + ".wav"
        # directory = "AudioFolder/"+ audioFileName
        # directory = os.path.normpath(directory)
        directory = os.path.normpath(basedir + '\\AudioFolder\\' + audioFileName)
        directory = os.path.normpath(basedir+"/AudioFolder/" + audioFileName)
        return send_file(directory, as_attachment=True)


@app.route('/audio', methods=['GET', 'POST'])
def audio():
    data = request.get_json()
    response_text = data.get('text_tran_tospeech')
             # Convert response to speech
    if response_text:         
        response_audio = ttsModel.text_to_speech(response_text)
        return jsonify({'response_audio': response_audio})
    
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
    return render_template('newFiles.html', background = background)

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

    file_path = os.path.normpath(os.path.join(app.config['UPLOADED_PATH'], filename))
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    os.remove(file_path)
    return jsonify({"message": "File deleted successfully"}), 200

@app.route('/files/chatLoader', methods=['POST'])
def chatLoader():
    filepath = os.path.normpath((basedir + '\\uploads'))

    try:
        vectorDB.embedAllInDirectiory(filepath, sessionID)
    except:
        pass
    vectorDB.embedAllImages(filepath, sessionID)
    return jsonify({'message': 'Files uploaded to VectorDB!'})

@app.route('/files/resetChat', methods=['POST'])
def chatReset():
    try:
        vectorDB.deleteSession(sessionID)
    except:
        pass
    
    return jsonify({'message': 'ChatReset'})

@app.route('/files/historyDownload', methods=['POST'])
def historyDownload():
    pdfPath = os.path.normpath(basedir + '\\chat_history.pdf') #creates chat history
    filepath = os.path.normpath(vectorDB.chat_history_as_txt(sessionID))
    chatHistoryPrettifier.convert_chat_to_pdf(filepath, pdfPath) #return filepath for pdf
    return send_from_directory(directory=basedir, path='chat_history.pdf', as_attachment=True)

@app.route('/background', methods=['POST'])
def retbackground():
    global background
    background = not background
    text = str(background)
    return jsonify({'bool': text}), 200

if __name__ == '__main__':
    app.run(debug=False) #when set to true it runs twice for some reason