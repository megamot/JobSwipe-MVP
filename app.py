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
companies_collection = db.companies
users_collection = db.users

# --- API МАРШРУТИ ---


# --- ВАКАНСІЇ: фільтрація за тегами користувача ---
@app.route('/api/vacancies', methods=['GET'])
def get_vacancies():
    """
    Повертає вакансії, релевантні тегам користувача (якщо передано user_id), інакше випадкові.
    """
    user_id = request.args.get('user_id')
    try:
        if user_id:
            user = users_collection.find_one({'_id': user_id})
            if not user:
                return jsonify({'error': 'User not found'}), 404
            user_tags = user.get('selected_tags', [])
            # Повертаємо вакансії, які мають хоча б один тег з user_tags
            query = {'tags_tech': {'$in': user_tags}}
            vacancies_cursor = vacancies_collection.find(query).limit(20)
        else:
            # Випадкові вакансії (MVP fallback)
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
                'full_description': v.get('full_description'),
                'tags_tech': v.get('tags_tech', []),
                'tags_company': v.get('tags_company', []),
            })
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
    

# --- SWIPE: збереження реакції користувача ---
@app.route('/api/swipe', methods=['POST'])
def process_swipe():
    """
    Зберігає реакцію користувача (like/nope) в users.liked_vacancies/rejected_vacancies.
    Очікує: {user_id, id_source, type}
    """
    data = request.get_json()
    user_id = data.get('user_id')
    vacancy_id = data.get('id_source')
    swipe_type = data.get('type')
    if not user_id or not vacancy_id or swipe_type not in ['like', 'nope']:
        return jsonify({'error': 'Invalid input'}), 400
    user = users_collection.find_one({'_id': user_id})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if swipe_type == 'like':
        users_collection.update_one(
            {'_id': user_id},
            {'$addToSet': {'liked_vacancies': vacancy_id}}
        )
        response_msg = "Vacancy liked!"
    else:
        users_collection.update_one(
            {'_id': user_id},
            {'$addToSet': {'rejected_vacancies': vacancy_id}}
        )
        response_msg = "Vacancy rejected."
    return jsonify({'status': 'success', 'message': response_msg}), 200

# --- USER REGISTRATION ---
@app.route('/api/register', methods=['POST'])
def register_user():
    """
    Реєстрація користувача: username, password. Повертає user_id.
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if users_collection.find_one({'username': username}):
        return jsonify({'error': 'Username already exists'}), 409
    user_doc = {
        'username': username,
        'password': password,  # Для MVP, не хешується!
        'selected_tags': [],
        'liked_vacancies': [],
        'rejected_vacancies': []
    }
    result = users_collection.insert_one(user_doc)
    return jsonify({'user_id': str(result.inserted_id)}), 201

# --- USER LOGIN ---
@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = users_collection.find_one({'username': username, 'password': password})
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    return jsonify({'user_id': str(user['_id'])}), 200

# --- USER TAG SELECTION ---
@app.route('/api/user/tags', methods=['POST'])
def set_user_tags():
    data = request.get_json()
    user_id = data.get('user_id')
    tags = data.get('tags', [])
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    users_collection.update_one({'_id': user_id}, {'$set': {'selected_tags': tags}})
    return jsonify({'status': 'success'}), 200

# --- USER CABINET: liked vacancies ---
@app.route('/api/user/liked', methods=['GET'])
def get_liked_vacancies():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    user = users_collection.find_one({'_id': user_id})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    liked_ids = user.get('liked_vacancies', [])
    vacancies = list(vacancies_collection.find({'id_source': {'$in': liked_ids}}))
    result = []
    for v in vacancies:
        result.append({
            'id_source': v.get('id_source'),
            'title': v.get('title'),
            'company_name': v.get('company_name'),
            'city': v.get('city'),
            'tags_tech': v.get('tags_tech', []),
            'tags_company': v.get('tags_company', []),
        })
    return jsonify(result), 200


if __name__ == '__main__':
    # Встановіть режим дебагу, щоб сервер автоматично перезавантажувався
    app.run(debug=True, port=5000)