import os
import textParser
import openai
import json
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools.retriever import create_retriever_tool
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_community.document_loaders import TextLoader
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key

def readFile(file_path): #reads file
    loader = TextLoader(file_path)
    documents = loader.load()
    return documents

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

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]



def chatResponse(question,chain,sessionID): #Embeds vectorDB into OpenAI
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
    return response

def setup_session_dir(session_id):
    session_dir = os.path.join('/sessions', session_id)
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    return session_dir

def embed(file_path, sessionID):
    text = textParser.extract_text(file_path)
    chunks = createChunks(text)
    vectors = vectorStorage(chunks, sessionID)
    #print("finished")

def chat(question, sessionID):
    session_dir = setup_session_dir(sessionID)
    store_path = os.path.join(session_dir, 'chain_store.json')
    if not os.path.exists(store_path):
        raise ValueError("Session ID not found. Please embed a file first.")
    chain = createChain(vectorStorage([], sessionID))  # Reload the vector DB and chain
    return chatResponse(question, chain, sessionID)

def destroy(sessionID):
    session_dir = setup_session_dir(sessionID)
    if os.path.exists(session_dir):
        for root, dirs, files in os.walk(session_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(session_dir)
    return "Session destroyed."

# def saveVectorDB(vectors, path):
#     vectors.save_local(path)

# def loadVectorDB(path):
#     embeddings = embedding_functions.OpenAIEmbeddingFunction(
#                 api_key=os.getenv("OPENAI_API_KEY"),
#                 model_name="text-embedding-3-small"
#             )
#     vectors = FAISS.load_local(path, embeddings, allow_dangerous_deserialization = True)
#     return vectors

def mergeVectorDB(db1,db2):
    db1.merge_from(db2)
    return db1

###test usage
#store = {}
# question = 'What is the name of the main character?'
# file_path = 'tesla.txt'
# text = readFile(file_path)
# chunks = createChunks(text)
# vectors = vectorStorage(chunks)
# chain = createChain(vectors)
# print(chatResponse(question, chain, "abc123"))
#(embed('filetypes/tesla.txt', "abc123"))

# Uncomment these lines to test saving and loading the vector DB
# saveVectorDB(vectors, "faiss_index")
# vectors = loadVectorDB('faiss_index')
# print(chat(question, vectors))