import os
import textParser
import openai
from dotenv import load_dotenv
import json
import imageHandler
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
import shutil
import time
from PIL import Image
from langchain_core.documents import Document
import asyncio

os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key

def setup_session_dir(session_id):
    # Get the current working directory
    base_dir = os.getcwd()
    # Create the session directory path within the current working directory
    session_dir = os.path.normpath(os.path.join(base_dir, 'sessions', session_id, 'chromaDB'))
    # Create the directory if it does not exist
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def readFile(file_path): #reads file
    doccuments = textParser.extract_text(file_path)
    return doccuments

def createChunks(text): #appends files to vectorDB
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    chunks = text_splitter.split_documents(text)
    return chunks

def vectorStorage(chunks, sessionID):
    sessionDir = setup_session_dir(sessionID)
    embeddings_function = OpenAIEmbeddings(
                api_key=os.getenv("OPENAI_API_KEY")
            )
    db = Chroma.from_documents(documents=chunks, embedding=embeddings_function, persist_directory=sessionDir, client_settings={"anonymized_telemetry": False})
    #retriever = db.as_retriever()
    return db


    
def createChain(db):
    retriever = db.as_retriever()
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    ### Contextualize question ###
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )


    ### Answer question ###
    system_prompt = (
        "You are an assistant for question-answering tasks. When asking about a document, assume the document is embedded"
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Keep the answer concise."
        "\n\n"
        "{context}"
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    return rag_chain

def save_chat_history(chat_history,session_id='abc123'):
    session_dir = setup_session_dir(session_id)
    history_path = os.path.join(session_dir, "chat_history.json")
    with open(history_path, 'w') as file:
        json.dump([message.dict() for message in chat_history.messages], file)

def load_chat_history(session_id='abc123'):
    session_dir = setup_session_dir(session_id)
    history_path = os.path.join(session_dir, "chat_history.json")
    chat_history = ChatMessageHistory()

    if os.path.exists(history_path):
        with open(history_path, 'r') as file:
            messages = json.load(file)
            for msg in messages:
                if msg["type"] == "human":
                    chat_history.add_user_message((msg["content"]))
                elif msg["type"] == "ai":
                    chat_history.add_ai_message(msg["content"])
    
    return chat_history

def chat_history_as_txt(session_id='abc123'):
    session_dir = setup_session_dir(session_id)
    history_path = os.path.join(session_dir, "chat_history.json")
    #create an output doccument
    output_path = os.path.join(session_dir, "chat_history.txt")

    if os.path.exists(history_path):
        with open(history_path, 'r') as file:
            messages = json.load(file)
            for msg in messages:
                if msg["type"] == "human":
                    with open(output_path, 'a') as output_file:
                        output_file.write(f"User: {msg['content']}\n")
                elif msg["type"] == "ai":
                    with open(output_path, 'a') as output_file:
                        output_file.write(f"AI: {msg['content']}\n")
    return output_path

def get_session_history(session_id: str) -> BaseChatMessageHistory:
        return load_chat_history(session_id)
    
def chatResponseChain(chain):

    conversational_rag_chain = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    return conversational_rag_chain

async def chatResponse(chain, question, sessionID):
    response = ""
    imgMetaData = None
    try:
        async for s in chain.astream(
            {"input": question},
            config={
                "configurable": {"session_id": sessionID}
            },  # constructs a key "abc123" in `store`.
        ):
            try:
                try:
                    if s['context'][0].metadata:
                        imgMetaData = s['context']
                        # print (imgMetaData)
                except:
                    pass
                chunk = s['answer']
                response += chunk
                yield chunk  # Yield each chunk instead of accumulating the entire response
            except KeyError:
                pass
    except:
        #if there is an error, delete the session and retry
        #deleteSession(sessionID)
        async for s in chain.astream(
            {"input": question},
            config={
                "configurable": {"session_id": sessionID}
            },  # constructs a key "abc123" in `store`.
        ):
            try:
                try:
                    if s['context'][0].metadata:
                        imgMetaData = s['context']
                        # print (imgMetaData)
                except:
                    pass
                chunk = s['answer']
                response += chunk
                yield chunk  # Yield each chunk instead of accumulating the entire response
            except KeyError:
                pass

            

    chat_history = get_session_history(sessionID)
    chat_history.add_user_message(question)
    chat_history.add_ai_message(response)
    
    save_chat_history(chat_history, sessionID)
    if (imgMetaData):
        yield imgMetaData
    

def deleteSession(sessionID = "abc123"):
    basedir = setup_session_dir(sessionID)
    #delete database folder
    try:
        shutil.rmtree(basedir)
    except:
        #reset the database
        db = Chroma.from_texts([], persist_directory=basedir, embedding_function=OpenAIEmbeddings())
        db.reset_collection()

    setup_session_dir(sessionID)
        

def embed(file_path, sessionID = "abc123"):
    text = readFile(file_path)
    chunks = createChunks(text)
    db = vectorStorage(chunks, sessionID)
    chain = createChain(db)
    ragChain = chatResponseChain(chain)
    store[sessionID] = ragChain
    #add to context that the file has been embedded


def embedAllInDirectiory(directory, sessionID):
    base_dir = os.getcwd()
    directory = os.path.normpath(os.path.join(base_dir, directory))
    list_extensions = [".pdf", ".txt", ".ppt", "pptx", "doc", "docx"]
    list_globs = [f"**/*{ext}" for ext in list_extensions]
    loader = DirectoryLoader(path = directory, glob = list_globs)
    docs = loader.load()
    chunks = createChunks(docs)
    db = vectorStorage(chunks, sessionID)

def embedImage(imageuri, sessionID="abc123"):
    base_dir = os.getcwd()
    image_path = os.path.normpath(os.path.join(base_dir, imageuri))
    
    # Using imageHandler.py to get the caption and objects detected
    caption, objects = imageHandler.image_handler(image_path)
    
    # Extract additional metadata
    file_path = image_path
    file_name = os.path.basename(image_path)
    file_type = os.path.splitext(file_name)[1].lower()
    
    # Create document content
    md = {
        "source": "Local", "file_path": file_path,"file_type": file_type,"title": file_name
    }
    docs = f"{caption}\n{objects}"
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    document = text_splitter.create_documents(texts = [docs], metadatas = [md])
    db = Chroma.from_documents(documents=document, persist_directory=setup_session_dir(sessionID), embedding=OpenAIEmbeddings(), client_settings={"anonymized_telemetry": False})
    
    




def embedAllImages(directory, sessionID):
    base_dir = os.getcwd()
    directory = os.path.normpath(os.path.join(base_dir, directory))
    client = Chroma(persist_directory=setup_session_dir(sessionID), embedding_function=OpenAIEmbeddings())
    list_extensions = [".jpg", ".jpeg", ".png"]
    imageFiles = [f for f in os.listdir(directory) if f.endswith(tuple(list_extensions))]
    #fileIDs should just be the file names without the extension
    fileIDs = [os.path.splitext(f)[0] for f in imageFiles]
    for image in imageFiles:
        embedImage(image, sessionID)

async def chat(question, sessionID = "abc123", ragChain = None):
    sessionDir = setup_session_dir(sessionID)
    try:
        db = Chroma(persist_directory=sessionDir, embedding_function=OpenAIEmbeddings())
    except:
        db = Chroma.from_texts([], persist_directory=sessionDir, embedding_function=OpenAIEmbeddings())
    chain = createChain(db)
    if ragChain is None:
        if sessionID in store:
            ragChain = store[sessionID]
        else:
            ragChain = chatResponseChain(chain)
        store[sessionID] = ragChain

    metadata = None
    async for chunk in chatResponse(ragChain, question, sessionID):
        #check if chunk is a list, if so it contains metadata, save as metadata and do not yield
        if (isinstance(chunk, list)):
            metadata = chunk
        else:
            yield chunk   
    yield (metadata)


store = {}

#time embedding functin


# deleteSession("abc123")
# start = time.time()
# embedImage("C:\\Users\\An\\Downloads\\chatbot\\sessions\\abc123\\uploads\\image.jpg")
# #embed("C:\\Users\\An\\Downloads\\chatbot\\resume.pdf")
# end = time.time()
# print("Time taken: ", end-start)



# Main function to run the async chat function
async def main():
    
    async for value in chat("Tell me about the dog."):
        print(value, end="")
    print("\n")
    async for value in chat("What is on my resume?"):
        print(value, end="")

# Run the main function in the event loop
#asyncio.run(main())