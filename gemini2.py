import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

def prompt(comentarios):
    return f"""{comentarios}
    crie um resumo das avaliações do produto"""
    
def gerar_resumo(comentarios):
    genai.configure(api_key=os.getenv('API_KEY'))
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
    response = model.generate_content(prompt(comentarios))
    return response.text
