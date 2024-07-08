import os
from dotenv import load_dotenv
import openai
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.llms import openai
from langchain_community.document_loaders import TextLoader
import chromadb.utils.embedding_functions as embedding_functions


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key

def createVectorDB(): #create vectorDB using Chroma
    embeddings = OpenAIEmbeddings(api_key=api_key)
    vectorDB = Chroma(embedding_function=embeddings)
    return vectorDB

def readFile(file_path): #reads file
    loader = TextLoader(file_path)
    documents = loader.load()
    return documents

def createChunks(text): #appends files to vectorDB
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    chunks = text_splitter.split_documents(text)
    return chunks

def vectorStorage(chunks):
    embeddings_function = OpenAIEmbeddings(
                api_key=os.getenv("OPENAI_API_KEY")
            )
    db = Chroma.from_documents(chunks, embeddings_function, persist_directory="./chroma_db")
    return db
    


def chat(question,vectors): #Embeds vectorDB into OpenAI
    docs = vectors.similarity_search(question)
    return docs[0].page_content


def saveVectorDB(vectors, path):
    vectors.save_local(path)

def loadVectorDB(path):
    embeddings = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
    vectors = FAISS.load_local(path, embeddings, allow_dangerous_deserialization = True)
    return vectors

def mergeVectorDB(db1,db2):
    db1.merge_from(db2)
    return db1

###test usage
question = 'What is your name?'
file_path = 'tesla.txt'
text = readFile(file_path)
chunks = createChunks(text)
vectors = vectorStorage(chunks)
print(chat(question, vectors))


# Uncomment these lines to test saving and loading the vector DB
# saveVectorDB(vectors, "faiss_index")
# vectors = loadVectorDB('faiss_index')
# print(chat(question, vectors))