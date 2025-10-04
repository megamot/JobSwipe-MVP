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
        pipeline = [
            {'$match': {'tags_tech': {'$ne': None}}}, 
            {'$sample': {'size': 10}}
        ]
        
        vacancies_cursor = vacancies_collection.aggregate(pipeline)
        
        vacancies_list = []
        for v in vacancies_cursor:
            vacancies_list.append({
                'id_source': v.get('id_source'),
                'title': v.get('title'),
                'company_name': v.get('company_name'),
                'city': v.get('city'),
                'full_description': v.get('full_description'), # <<< ДОДАНО ЦЕ ПОЛЕ
                'tags_tech': v.get('tags_tech', []),
                'tags_company': v.get('tags_company', []),
            })
        
        # Використовуємо jsonify для коректного форматування в JSON
        return jsonify(vacancies_list), 200

    except Exception as e:
        app.logger.error(f"MongoDB Error: {e}")
        return jsonify({'error': 'Failed to fetch vacancies from database'}), 500


@app.route('/api/vacancy/<id_source>', methods=['GET'])
def get_single_vacancy(id_source):
    """Повертає повні дані однієї вакансії за її id_source."""
    try:
        # 1. Шукаємо вакансію за унікальним ідентифікатором
        vacancy = vacancies_collection.find_one({'id_source': id_source})
        
        if not vacancy:
            return jsonify({'error': 'Vacancy not found'}), 404

        # 2. Очищаємо ObjectId (вибираємо потрібні поля) та формуємо об'єкт для відправки
        response_data = {
            'id_source': vacancy.get('id_source'),
            'title': vacancy.get('title'),
            'company_name': vacancy.get('company_name'),
            'city': vacancy.get('city'),
            'full_description': vacancy.get('full_description'), # Повний опис
            'tags_tech': vacancy.get('tags_tech', []),
            'tags_company': vacancy.get('tags_company', []),
            'source_url': vacancy.get('source_url') # Оригінальне посилання на Robota.ua
        }
        
        return jsonify(response_data), 200

    except Exception as e:
        app.logger.error(f"Error fetching single vacancy: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
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