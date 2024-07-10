import os
import textParser
import openai
from dotenv import load_dotenv
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


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key

def setup_session_dir(session_id):
    # Get the current working directory
    base_dir = os.getcwd()
    # Create the session directory path within the current working directory
    session_dir = os.path.normpath(os.path.join(base_dir, 'sessions', session_id))
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
    db = Chroma.from_documents(chunks, embeddings_function, persist_directory=sessionDir)
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
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise."
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

def chatResponse(chain, question, sessionID):
    store = {}


    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]


    conversational_rag_chain = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )

    response = conversational_rag_chain.invoke(
        {"input": question},
        config={
            "configurable": {"session_id": sessionID}
        },  # constructs a key "abc123" in `store`.
    )["answer"]
    return(response)

def deleteSession(sessionID):
    sessionDir = setup_session_dir(sessionID)
    shutil.rmtree(sessionDir)

def embed(file_path, sessionID):
    text = readFile(file_path)
    chunks = createChunks(text)
    db = vectorStorage(chunks, sessionID)

def embedAllInDirectiory(directory, sessionID):
    base_dir = os.getcwd()
    directory = os.path.normpath(os.path.join(base_dir, directory))
    list_extensions = [".pdf", ".txt", ".ppt", "pptx", "doc", "docx"]
    list_globs = [f"**/*{ext}" for ext in list_extensions]
    loader = DirectoryLoader(path = directory, glob = list_globs)
    docs = loader.load()
    chunks = createChunks(docs)
    db = vectorStorage(chunks, sessionID)
    
def chat (question, sessionID = "abc123"):
    sessionDir = setup_session_dir(sessionID)
    db = Chroma(persist_directory=sessionDir, embedding_function=OpenAIEmbeddings())
    chain = createChain(db)
    response = chatResponse(chain, question, sessionID)
    return response

### example usage ###
# deleteSession("abc123")
# embedAllInDirectiory("filetypes", "abc123")
# print(chat("What is the spy's name?"))
# print(chat("What word echohe through elara's mind?"))
# print(chat("What is the spy's name?"))
# print(chat("What word echohe through elara's mind?"))
