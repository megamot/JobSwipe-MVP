from flask import Flask, jsonify, request
from pymongo import MongoClient
import random
from bson.json_util import dumps
from bson import ObjectId
from flask_cors import CORS

# --- НАЛАШТУВАННЯ ---
app = Flask(__name__)
CORS(app)

# MongoDB connection with error handling
try:
    MONGO_URI = "mongodb://user:password@localhost:27017/"
    client = MongoClient(MONGO_URI)
    # Test connection
    client.server_info()
    db = client.jobswipe_db
    vacancies_collection = db.vacancies
    companies_collection = db.companies
    users_collection = db.users
    print("Successfully connected to MongoDB")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise

# --- API МАРШРУТИ ---

# --- USER PROFILE: get selected_tags ---
@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    # Підтримка ObjectId та str
    query = {'_id': ObjectId(user_id)} if ObjectId.is_valid(user_id) else {'_id': user_id}
    user = users_collection.find_one(query)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'selected_tags': user.get('selected_tags', [])}), 200


# --- ВАКАНСІЇ: фільтрація за тегами користувача ---
# MongoDB retry decorator
from functools import wraps
from pymongo.errors import AutoReconnect
import time

def retry_mongo(max_retries=3, delay=0.5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except AutoReconnect:
                    retries += 1
                    if retries == max_retries:
                        raise
                    time.sleep(delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/api/user/remove-liked', methods=['POST'])
@retry_mongo()
def remove_liked_vacancy():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        id_source = data.get('id_source')
        if not user_id or not id_source:
            return jsonify({'status': 'error', 'message': 'user_id and id_source required'}), 400
            
        # If user_id is not ObjectId, use as is
        query = {'_id': ObjectId(user_id)} if ObjectId.is_valid(user_id) else {'_id': user_id}
        
        result = users_collection.update_one(
            query,
            {
                '$pull': {'liked_vacancies': id_source},
                '$addToSet': {'rejected_vacancies': id_source}
            }
        )
        
        if result.matched_count == 0:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vacancies', methods=['GET'])
@retry_mongo()
def get_vacancies():
    """
    Повертає вакансії, відсортовані за датою та відфільтровані за переглядами користувача та тегами.
    """
    user_id = request.args.get('user_id')
    try:
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        # Отримуємо дані користувача
        query = {'_id': ObjectId(user_id)} if ObjectId.is_valid(user_id) else {'_id': user_id}
        user = users_collection.find_one(query)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Отримуємо списки переглянутих вакансій
        liked_vacancies = user.get('liked_vacancies', [])
        rejected_vacancies = user.get('rejected_vacancies', [])
        viewed_vacancies = liked_vacancies + rejected_vacancies

        # Базовий запит: виключаємо переглянуті вакансії
        base_query = {
            'id_source': {'$nin': viewed_vacancies}
        }

        # Додаємо фільтрацію за тегами, якщо вони є
        user_tags = user.get('selected_tags', [])
        if user_tags:
            base_query['$or'] = [
                {'tags_tech': {'$in': user_tags}},
                {'tags_company': {'$in': user_tags}}
            ]

        # Отримуємо вакансії, сортуємо за датою
        vacancies_cursor = vacancies_collection.find(base_query).sort('date', -1).limit(20)
        
        vacancies_list = []
        for v in vacancies_cursor:
            vacancies_list.append({
                'id_source': v.get('id_source'),
                'name': v.get('name'),
                'companyName': v.get('companyName'),
                'cityId': v.get('cityId'),
                'vacancyAddress': v.get('vacancyAddress'),
                'shortDescription': v.get('shortDescription'),
                'description': v.get('description'),
                'tags_tech': v.get('tags_tech', []),
                'tags_company': v.get('tags_company', []),
                'date': v.get('date')
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
            'name': vacancy.get('name'),
            'companyName': vacancy.get('companyName'),
            'cityId': vacancy.get('cityId'),
            'vacancyAddress': vacancy.get('vacancyAddress'),
            'description': vacancy.get('description'),
            'shortDescription': vacancy.get('shortDescription'),
            'tags_tech': vacancy.get('tags_tech', []),
            'tags_company': vacancy.get('tags_company', []),
            'source_url': vacancy.get('source_url')
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
    query = {'_id': ObjectId(user_id)} if ObjectId.is_valid(user_id) else {'_id': user_id}
    user = users_collection.find_one(query)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if swipe_type == 'like':
        users_collection.update_one(
            query,
            {'$addToSet': {'liked_vacancies': vacancy_id}}
        )
        response_msg = "Vacancy liked!"
    else:
        users_collection.update_one(
            query,
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
    query = {'_id': ObjectId(user_id)} if ObjectId.is_valid(user_id) else {'_id': user_id}
    users_collection.update_one(query, {'$set': {'selected_tags': tags}})
    return jsonify({'status': 'success'}), 200

# --- USER CABINET: liked vacancies ---
@app.route('/api/user/liked', methods=['GET'])
def get_liked_vacancies():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    query = {'_id': ObjectId(user_id)} if ObjectId.is_valid(user_id) else {'_id': user_id}
    user = users_collection.find_one(query)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    liked_ids = user.get('liked_vacancies', [])
    vacancies = list(vacancies_collection.find({'id_source': {'$in': liked_ids}}))
    result = []
    for v in vacancies:
        result.append({
            'id_source': v.get('id_source'),
            'title': v.get('name'),
            'company_name': v.get('companyName'),
            'city': v.get('cityId'),
            'tags_tech': v.get('tags_tech', []),
            'tags_company': v.get('tags_company', []),
        })
    return jsonify(result), 200


if __name__ == '__main__':
    # Встановіть режим дебагу, щоб сервер автоматично перезавантажувався
    app.run(debug=True, port=5000)