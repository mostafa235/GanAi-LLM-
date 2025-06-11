from setuptools import find_packages,setup

setup(
    name='medical_chatbot',
    version='0.0.1',
    author='mostafa mohamed elsaht',
    author_email='mostafamohamedelsaht@gmai.com',
    install_requires=["pypdf","deep_translator","langdetect","langchain","flask","flask-cors","streamlit","python-dotenv","langchain_huggingface","langchain-chroma","huggingface_hub ","transformers","langchain-community"],
    packages=find_packages()
)