import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint
#from langchain_huggingface import HuggingFacePipeline
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chains import SequentialChain


TEMPLATE = """Text:{text}
You are an expert MCQ maker. Given the above text, create a quiz of {number} multiple choice questions for {subject} students in {tone} tone.
Make sure to format your response as a valid JSON exactly like this example:
{response_json}

Important rules:
1. Return ONLY the JSON
2. Don't add any text before or after the JSON
3. Ensure all questions are from the text
4. Make {number} complete MCQs
"""

load_dotenv()

key = os.getenv("HUGGINGFACEHUB_API_TOKEN")

quiz_generation_prompt = PromptTemplate(
    input_variables=["text", "number", "subject", "tone", "response_json"],
    template=TEMPLATE
    )


llms = HuggingFaceEndpoint(
    huggingfacehub_api_token=key,
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    task="text-generation",
    temperature=0.7,# تقليل العشوائية
    do_sample= True,
    
)


quiz_chain=LLMChain(llm=llms, prompt=quiz_generation_prompt, output_key="quiz", verbose=True)


TEMPLATE2 = """You are an expert english grammarian and writer. Given a Multiple Choice Quiz for {subject} students.
Your task is to:
1. Evaluate the complexity (1-5 scale)
2. Suggest improvements if needed
3. Keep analysis under 50 words

Return your evaluation as a JSON object with these keys:
- "complexity": (number)
- "analysis": (string)
- "suggestions": (string)

Quiz MCQs:
{quiz}

Important: Return ONLY the JSON object, nothing else.
"""


quiz_evaluation_prompt=PromptTemplate(input_variables=["subject", "quiz"], template=TEMPLATE2)

review_chain=LLMChain(llm=llms, prompt=quiz_evaluation_prompt, output_key="review", verbose=True)

generate_evaluate_chain=SequentialChain(chains=[quiz_chain, review_chain], input_variables=["text", "number", "subject", "tone", "response_json"],
                                        output_variables=["quiz", "review"], verbose=True,)