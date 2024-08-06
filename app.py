from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from flasgger import Swagger
from dotenv import load_dotenv
import cachetools
import os
from gemini2 import gerar_resumo

load_dotenv()

app = Flask(__name__)
swagger = Swagger(app)

try:
    client = MongoClient(os.getenv('MONGO_URI'), serverSelectionTimeoutMS=5000)  # Timeout para conexão
    db = client[os.getenv('DATABASE_NAME')]
    collection = db[os.getenv('COLLECTION_NAME')]
    # Testar a conexão
    client.server_info()
except ServerSelectionTimeoutError:
    print("Erro ao conectar ao MongoDB")
    collection = None

# Configuração do cache
cache = cachetools.TTLCache(maxsize=100, ttl=3600)  # Armazena resumos por produto por 1 hora

def filtrar_comentarios(reviews):
    return [avaliacao['avaliacao'] for avaliacao in reviews[:20]]  # Pega apenas os primeiros 20 itens

@app.route('/save_review', methods=['POST'])
def save_review():
    """
    Adiciona uma nova avaliação para um produto no banco de dados.
    ---
    tags:
      - Avaliações
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            produto_id:
              type: string
              description: ID do produto que está sendo avaliado
              example: produto123
            nome_usuario:
              type: string
              description: Nome do usuário que faz a avaliação
              example: Ana
            nota:
              type: integer
              description: Nota da avaliação (de 1 a 5)
              example: 5
            avaliacao:
              type: string
              description: Texto da avaliação
              example: Excelente!
    responses:
      201:
        description: Avaliação salva com sucesso
        schema:
          type: object
          properties:
            message:
              type: string
              example: Avaliação salva com sucesso
      400:
        description: Dados inválidos
        schema:
          type: object
          properties:
            error:
              type: string
              example: Dados inválidos
      500:
        description: Erro de conexão com o banco de dados
        schema:
          type: object
          properties:
            error:
              type: string
              example: Erro de conexão com o banco de dados
    """
    if collection is None:
        return jsonify({'error': 'Erro de conexão com o banco de dados'}), 500

    data = request.json
    produto_id = data.get('produto_id')
    nome_usuario = data.get('nome_usuario')
    nota = data.get('nota')
    avaliacao = data.get('avaliacao')

    if not (produto_id and nome_usuario and 1 <= nota <= 5 and avaliacao):
        return jsonify({'error': 'Dados inválidos'}), 400

    review = {
        'produto_id': produto_id,
        'nome_usuario': nome_usuario,
        'nota': nota,
        'avaliacao': avaliacao
    }

    collection.insert_one(review)
    return jsonify({'message': 'Avaliação salva com sucesso'}), 201

@app.route('/get_reviews', methods=['GET'])
def get_reviews():
    """
    Retorna todas as avaliações para um produto específico e o resumo das avaliações.
    ---
    tags:
      - Avaliações
    parameters:
      - name: produto_id
        in: query
        required: true
        type: string
        description: ID do produto para o qual as avaliações são solicitadas
        example: produto123
    responses:
      200:
        description: Lista de avaliações e o resumo das avaliações
        schema:
          type: object
          properties:
            resumo_avaliacao:
              type: string
              example: "Nenhum resumo disponível."
            avaliacoes:
              type: array
              items:
                type: object
                properties:
                  produto_id:
                    type: string
                    example: produto123
                  nome_usuario:
                    type: string
                    example: Ana
                  nota:
                    type: integer
                    example: 5
                  avaliacao:
                    type: string
                    example: Excelente!
      500:
        description: Erro de conexão com o banco de dados
        schema:
          type: object
          properties:
            error:
              type: string
              example: Erro de conexão com o banco de dados
    """
    if collection is None:
        return jsonify({'error': 'Erro de conexão com o banco de dados'}), 500

    produto_id = request.args.get('produto_id')

    if not produto_id:
        return jsonify({'error': 'ID do produto é obrigatório'}), 400

    reviews = list(collection.find({'produto_id': produto_id}, {'_id': 0}).sort('data', -1))  # Exclui o campo _id dos resultados

    if not reviews:
        return jsonify({
            'resumo_avaliacao': 'Nenhum resumo disponível.',
            'media': 0,
            'avaliacoes': []
        }), 200

    notas = [review['nota'] for review in reviews]
    media_nota = round(sum(notas) / len(notas), 2) if notas else 0

    resumo_avaliacao = cache.get(produto_id)
    if not resumo_avaliacao:
        comentarios = filtrar_comentarios(reviews)
        resumo_avaliacao = gerar_resumo(comentarios)
        cache[produto_id] = resumo_avaliacao

    return jsonify({
        'resumo_avaliacao': resumo_avaliacao,
        'media': media_nota,
        'avaliacoes': reviews
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
