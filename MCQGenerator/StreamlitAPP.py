import os
import json
import pandas as pd
import streamlit as st
from src.mcqgenrator.utils import read_file,get_table_data
from src.mcqgenrator.logger import logging
from src.mcqgenrator.MCQGenerator import generate_evaluate_chain
import traceback
import json

with open("Response.json", "r") as f:
    RESPONSE_JSON = json.load(f)

st.title("MCQ Creater application with langchain and huggingface using llama model 🧠")

with st.form("user_inputs"):
    uploaded_file=st.file_uploader("upload pdf ot text file")
    mcq_count=st.number_input("NO. of MCQ",min_value=3,max_value=50)
    subject=st.text_input("inser a subject",max_chars=20)
    tone=st.text_input("insert alevel of Questions ",max_chars=20,placeholder="simple")
    butoon=st.form_submit_button("CREATE MCQ.")

    if butoon and uploaded_file is not None and mcq_count and subject and tone:

        with st.spinner("load..."):
            try:
                text=read_file(uploaded_file)

                response = generate_evaluate_chain.invoke({
                    "text": text,
                    "number":int( mcq_count),
                    "subject": subject,
                    "tone": tone,
                    "response_json": json.dumps(RESPONSE_JSON)
                })
                #st.write(response)
            except Exception  as e:
                
                traceback.print_exception(type(e),e,e.__traceback__)   
            else:
                quiz_table_data=get_table_data(response)
                # تحويل القائمة إلى DataFrame
                df = pd.DataFrame(quiz_table_data)

                # عرض الجدول في Streamlit
                st.table(df)


