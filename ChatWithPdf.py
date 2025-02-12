import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize ThreadPoolExecutor for async PDF processing
executor = ThreadPoolExecutor()

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            st.warning(f"Error reading PDF: {e}")
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")  # Consider a dynamic filename based on the session or PDF name

def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not
    in provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n
    Answer:
    """
    
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    
    return chain

def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    # Load vector store from disk
    new_db = FAISS.load_local("faiss_index", embeddings)
    docs = new_db.similarity_search(user_question)

    chain = get_conversational_chain()

    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    st.write("**Answer:**", response["output_text"])

def main():
    st.set_page_config(page_title="Interactive PDF Chatbot", page_icon="💬")  # Catchy title with icon
    st.header("Welcome to Chat with PDF 📚💬")
    st.markdown("""
    Upload your PDF documents and ask questions related to their content. 
    The AI will answer based on the text extracted from your PDFs. 💡
    """)

    user_question = st.text_input("Ask a Question from the PDF Files:")

    if user_question:
        with st.spinner("Generating response..."):
            user_input(user_question)

    # Sidebar for file upload and processing
    with st.sidebar:
        st.title("PDF Processing 📝")
        pdf_docs = st.file_uploader("Upload your PDF files here", accept_multiple_files=True)

        if pdf_docs:
            if st.button("Submit & Process"):
                with st.spinner("Processing PDFs and generating the index..."):
                    raw_text = get_pdf_text(pdf_docs)
                    if raw_text.strip() == "":
                        st.error("No text extracted from the PDFs. Please check the files.")
                    else:
                        text_chunks = get_text_chunks(raw_text)
                        get_vector_store(text_chunks)
                        st.success("PDF processing complete and vector index generated!")

if __name__ == "__main__":
    main()
