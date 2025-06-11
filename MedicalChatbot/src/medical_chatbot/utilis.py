import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEndpoint
from langchain.prompts import PromptTemplate
import torch
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.medical_chatbot.logger import logging



# Load environment variables
load_dotenv()

def read_pdf(data):
    """Load PDF documents with error handling"""
    try:
        loader = PyPDFDirectoryLoader(
            path=data,
            glob="*.pdf",
        )
        documents = loader.load()
        if not documents:
            logging.warning(f"No PDF files found in directory: {data}")
        return documents
    except Exception as e:
        logging.error(f"Error loading PDFs: {str(e)}")
        raise

def text_split(extracted_data):
    """Split text into chunks with medical-optimized settings"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,  # Increased overlap for better medical context
        separators=["\n\n", "\n", " ", ""]  # Medical document-specific splitting
    )
    return text_splitter.split_documents(extracted_data)

def download_hugging_face_embeddings():
    """Download embeddings with medical specialization"""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'}
    )

def get_llm():
    """Get medical-optimized LLM with fallback options"""
    
    # Primary medical model
    repo_id = "meta-llama/Llama-3.1-8B-Instruct"

    llm = HuggingFaceEndpoint(
        repo_id=repo_id,
        max_new_tokens=100,
        temperature=0.2,  # More conservative for medical answers
        top_p=0.7,
        huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
    )
    return llm


def chroma_database(text_chunks, embeddings):
    """Create/load Chroma DB with medical focus"""
    persist_directory = "medical-chatbot"
    
    try:
        # إنشاء أو تحميل قاعدة البيانات بنفس المعلمة لكلتا الحالتين
        if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
            logging.info("Creating new Chroma database")
            return Chroma.from_documents(
                documents=text_chunks,
                embedding=embeddings,  # تغيير من embedding_function إلى embedding
                persist_directory=persist_directory
            )
        
        logging.info("Loading existing Chroma database")
        return Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings  # يمكن تركها كما هي هنا أو تغييرها إلى embedding
        )
    except Exception as e:
        logging.error(f"Chroma DB error: {str(e)}")
        raise

def retrieval_data(llm, vectordb):
    """Create retrieval chain with medical-optimized prompt"""
    prompt_template = """
    You are a medical assistant . Answer based ONLY on:
    
    Context: {context}
    Question: {question}
    
    Guidelines:
    1- Provide brief, accurate medical information (1-2 lines)
    2- If uncertain, say "Consult a doctor i dont know"
    3-Avoid repeating the same sentence or phrase.
    Medical Answer:
    """

    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    
    retriever = vectordb.as_retriever(
        search_type="mmr",           # ✅ ضع هنا
        search_kwargs={"k": 4}     )
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={
            "prompt": PROMPT,
            "verbose": False
        },
        return_source_documents=True
    )


