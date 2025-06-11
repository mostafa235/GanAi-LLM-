import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langchain_community.llms import HuggingFacePipeline
load_dotenv()

token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
print("Token loaded:", bool(token))
print("Token:", token)

try:
    tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B", token=token)
    model = AutoModelForCausalLM.from_pretrained("deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B", token=token)

    # إنشاء pipeline للنص التوليدي
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
    
    # استخدام HuggingFacePipeline من langchain_huggingface (تأكد من استيرادها)
    llm = HuggingFacePipeline(pipeline=pipe)
    
    output = llm.invoke("Hello world!")
    print("Output:", output)
except Exception as e:
    print("Error:", e)
