import streamlit as st
from src.medical_chatbot.Medical_Chatbot import MedicalChatbot

def main():
    # إعداد واجهة المستخدم
    st.set_page_config(
        page_title="Medical Chatbot",
        page_icon="🏥",
        layout="wide"
    )
    
    st.title("🤖 Medical Chatbot (PDF-based)")
    st.write("اسأل أي سؤال طبي بناءً على المستندات المقدمة!")

    # تهيئة الشات بوت
    try:
        chatbot = MedicalChatbot()
        st.success("تم تحميل الشات بوت بنجاح!")
    except Exception as e:
        st.error(f"فشل في تحميل الشات بوت: {str(e)}")
        return

    # إدارة المحادثة
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض الرسائل السابقة
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("sources"):
                st.write("**المصادر:**")
                for src in message["sources"]:
                    st.write(f"- {src}")

    # معالجة المدخلات الجديدة
    if prompt := st.chat_input("اسأل سؤالك الطبي هنا..."):
        # عرض سؤال المستخدم
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # الحصول على الإجابة
        with st.spinner("جاري البحث عن الإجابة..."):
            response = chatbot.ask_question(prompt)
            
            # عرض الإجابة
            with st.chat_message("assistant"):
                st.markdown(response["answer"])
                if response["sources"]:
                    st.write("**المصادر:**")
                    for src in response["sources"]:
                        st.write(f"- {src}")
            
            # حفظ المحادثة
            st.session_state.messages.append({
                "role": "assistant",
                "content": response["answer"],
                "sources": response["sources"]
            })

if __name__ == "__main__":
    main()