import PyPDF2
import docx
import pandas as pd
from bs4 import BeautifulSoup
from langchain_community.document_loaders import TextLoader, UnstructuredExcelLoader, PyPDFLoader, PyMuPDFLoader, Docx2txtLoader, UnstructuredHTMLLoader
from langchain_community.document_loaders.csv_loader import CSVLoader

def extract_text_from_pdf(filepath):
    try:
        loader = PyMuPDFLoader(filepath)
    except:
        loader = PyPDFLoader(filepath)
    documents = loader.load()
    return documents

def extract_text_from_docx(filepath):
    loader = Docx2txtLoader(filepath)
    documents = loader.load()
    return documents

def extract_text_from_excel(filepath):
    loader = UnstructuredExcelLoader(filepath)
    documents = loader.load()
    return documents
def extract_text_from_txt(filepath):
    loader = TextLoader(filepath)
    documents = loader.load()
    return documents

def extract_text_from_csv(filepath):
    loader = CSVLoader(filepath)
    documents = loader.load()
    return documents

def extract_text_from_html(filepath):
    loader = UnstructuredHTMLLoader(filepath)
    documents = loader.load()
    return documents

def extract_text(filepath):
    if filepath.endswith('.pdf'):
        return extract_text_from_pdf(filepath)
    elif filepath.endswith('.docx'):
        return extract_text_from_docx(filepath)
    elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
        return extract_text_from_excel(filepath)
    elif filepath.endswith('.txt'):
        return extract_text_from_txt(filepath)
    elif filepath.endswith('.html'):
        return extract_text_from_html(filepath)
    elif filepath.endswith('.csv'):
        return extract_text_from_csv(filepath)
    else:
        raise ValueError("Unsupported file type:" + filepath + ". Supported file types are: .pdf, .docx, .xlsx, .xls, .txt, .html)")


# Example usage:
#file_path = 'text.txt'  # Change to your file path
#print(extract_text(file_path))
