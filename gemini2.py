import google.generativeai as genai

def prompt(comentarios):
    return f"""{comentarios}
    crie um resumo das avaliações do produto"""
    
def gerar_resumo(comentarios):
    genai.configure(api_key="AIzaSyB4xM33MZdQLMnylXKKEYBimdybfVkmCuc")
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
    response = model.generate_content(prompt(comentarios))
    return response.text
