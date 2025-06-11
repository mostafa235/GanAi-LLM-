import os
import traceback

from src.medical_chatbot.utilis import (
    read_pdf,
    text_split,
    download_hugging_face_embeddings,
    get_llm,
    chroma_database,
    retrieval_data
)
from src.medical_chatbot.logger import logging

class MedicalChatbot:
    def __init__(self, data_path="data"):
        self.data_path = data_path
        self.qa_chain = None
        self.initialize_bot()

    def initialize_bot(self):
        """تهيئة الشات بوت مع تحميل البيانات والنماذج"""
        try:
            logging.info("جاري تهيئة Medical Chatbot")
            
            # تحميل وتجهيز البيانات
            documents = read_pdf(self.data_path)
            text_chunks = text_split(documents)
            
            # إنشاء قاعدة البيانات المتجهة
            embeddings = download_hugging_face_embeddings()
            vectordb = chroma_database(text_chunks, embeddings)
            
            # تحميل نموذج LLM
            llm = get_llm()
            
            # إنشاء سلسلة الاسترجاع
            self.qa_chain = retrieval_data(llm, vectordb)
            
            logging.info("تم تهيئة الشات بوت بنجاح")
            
        except Exception as e:
            logging.error(f"خطأ في تهيئة الشات بوت: {str(e)}")
            raise Exception(f"فشل في تهيئة الشات بوت: {str(e)}")

    def ask_question(self, question):

        try:
            if not self.qa_chain:
                return {
                    "answer": "System not ready yet",
                    "sources": []
                }
            
            # جرب invoke مع dict بدلاً من run
            response = self.qa_chain.invoke({"query": question})
            
            answer = response.get("result", "")
            #answer=clean_output(answer)

            sources = list(set(
                os.path.basename(doc.metadata["source"])
                for doc in response.get("source_documents", [])
                if doc.metadata.get("source")
            ))
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            traceback.print_exc()
            return {
                "answer": f"Error: {str(e)}",
                "sources": []
            }
