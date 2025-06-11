import os
import PyPDF2
import json
import re

def read_file(file):
    if file.name.endswith(".pdf"):
        try:
            pdf_reader = PyPDF2.PdfFileReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            raise Exception(f"Error reading the PDF file: {e}")
        
    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    
    else:
        raise Exception(
            "Unsupported file format. Only PDF and TXT files supported."
        )

import json

def extract_json_from_response(text):
    try:
        start = text.find("{")
        if start == -1:
            print("No JSON object start found.")
            return None

        # نبحث عن نهاية JSON بحساب توازن الأقواس
        open_braces = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == "{":
                open_braces += 1
            elif char == "}":
                open_braces -= 1
            
            if open_braces == 0:
                end = i
                break
        
        json_str = text[start:end+1]

        return json.loads(json_str)
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None

def get_table_data(response):
    quiz_str = response.get("quiz", "")
    print("quiz_str content (first 300 chars):", quiz_str[:300])

    quiz_data = extract_json_from_response(quiz_str)
    if not isinstance(quiz_data, dict):
        print("Error: quiz_data is not a dictionary")
        return []

    quiz_table_data = []
    for key, value in quiz_data.items():
        mcq = value.get("mcq", "")
        options = " | ".join([f"{opt}: {val}" for opt, val in value.get("options", {}).items()])
        correct = value.get("correct", "")
        quiz_table_data.append({"MCQ": mcq, "Choices": options, "Correct": correct})

    return quiz_table_data
