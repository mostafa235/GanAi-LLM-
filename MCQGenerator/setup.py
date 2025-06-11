from setuptools import find_packages,setup

setup(
    name='mcqgenrator',
    version='0.0.2',
    author='mostafa mohamed elsaht',
    author_email='mostafamohamedelsaht@gmai.com',
    install_requires=["openai","langchain","langchain-community","streamlit","python-dotenv","huggingface_hub","PyPDF2","langchain_huggingface","transformers"],
    packages=find_packages()
)