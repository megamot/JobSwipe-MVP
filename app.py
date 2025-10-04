from flask import Flask, jsonify, request
from pymongo import MongoClient
import random
from bson.json_util import dumps

# --- НАЛАШТУВАННЯ ---
app = Flask(__name__)
# Дозволяємо CORS для розробки (ВАЖЛИВО!)
from flask_cors import CORS
CORS(app) 

MONGO_URI = "mongodb://user:password@localhost:27017/"
client = MongoClient(MONGO_URI)
db = client.jobswipe_db
vacancies_collection = db.vacancies 

# --- API МАРШРУТИ ---

@app.route('/api/vacancies', methods=['GET'])
def get_vacancies():
    """Повертає 10 випадкових непереглянутих вакансій."""
    try:
        # Вибираємо 10 випадкових вакансій для MVP
        # $sample забезпечує випадковий вибір без додаткового навантаження
        pipeline = [
            {'$match': {'tags_tech': {'$ne': None}}}, # Фільтр, щоб вибрати тільки теговані
            {'$sample': {'size': 10}}
        ]
        
        vacancies = vacancies_collection.aggregate(pipeline)
        
        # Використовуємо dumps для коректного перетворення об'єктів MongoDB (наприклад, ObjectId)
        json_vacancies = dumps(list(vacancies))
        
        # Повертаємо дані у форматі JSON
        return json_vacancies, 200, {'Content-Type': 'application/json'}

    except Exception as e:
        app.logger.error(f"MongoDB Error: {e}")
        return jsonify({'error': 'Failed to fetch vacancies from database'}), 500

@app.route('/api/swipe', methods=['POST'])
def process_swipe():
    """Обробляє свайп: зберігає реакцію користувача (like/nope)."""
    
    # Отримуємо дані з фронтенду
    data = request.get_json()
    vacancy_id = data.get('id_source')
    swipe_type = data.get('type') # 'like' або 'nope'
    
    # Тут має бути логіка збереження реакції користувача
    # (для MVP просто виводимо в консоль)
    
    if swipe_type == 'like':
        print(f"*** ЛАЙКНУТО: {vacancy_id}")
        # Тут: оновити профіль користувача в БД, додавши ID вакансії до списку 'likes'
        response_msg = "Vacancy liked!"
    elif swipe_type == 'nope':
        print(f"*** ВІДХИЛЕНО: {vacancy_id}")
        # Тут: оновити профіль користувача, додавши ID вакансії до списку 'seen'
        response_msg = "Vacancy rejected."
    else:
        return jsonify({'error': 'Invalid swipe type'}), 400
        
    return jsonify({'status': 'success', 'message': response_msg}), 200


if __name__ == '__main__':
    # Встановіть режим дебагу, щоб сервер автоматично перезавантажувався
    app.run(debug=True, port=5000)