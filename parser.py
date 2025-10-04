from pymongo import MongoClient
from tagging_config import generate_tags, clean_html 
from datetime import datetime
from typing import Dict, List
import requests
import time

# --- НАЛАШТУВАННЯ ---
MONGO_URI = "mongodb://user:password@localhost:27017/"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.jobswipe_db
vacancies_collection = db.vacancies 

# URL для Robota.ua API пошуку
ROBOTA_API_URL = "https://api.robota.ua/vacancy/search"

# Параметри для імітації "ТОП-роботодавців" (на прикладі SKELAR)
# Вказуємо ID компанії, щоб отримати її вакансії
COMPANY_IDS = [
    6627493,  # SKELAR
    # Тут будуть додані ID інших ТОП-компаній
]
VACANCIES_PER_PAGE = 50

# --- ФУНКЦІЇ БАЗИ ДАНИХ ---

def save_vacancy(raw_vacancy_data: Dict):
    """Очищає, тегує та зберігає вакансію в MongoDB."""
    
    vacancy_id = raw_vacancy_data.get('id')
    
    # URL формуємо на основі ID компанії (notebookId) та вакансії (id)
    source_url = f"https://robota.ua/company/{raw_vacancy_data['notebookId']}/vacancy/{vacancy_id}"

    # 1. Створення основного документа
    processed_data = {
        'id_source': f"robota_{vacancy_id}",
        'source_url': source_url,
        'title': raw_vacancy_data.get('name', 'N/A'),
        'company_name': raw_vacancy_data.get('companyName', 'N/A'),
        'salary_min': raw_vacancy_data.get('salary', 0), # Robota.ua повертає одне поле salary
        'salary_max': raw_vacancy_data.get('salary', 0), 
        'city': raw_vacancy_data.get('vacancyAddress', 'N/A'),
        'full_description': clean_html(raw_vacancy_data.get('description', '')),
        'date_published': raw_vacancy_data.get('date'),
        'date_parsed': datetime.utcnow(),
    }
    
    # 2. Генерація тегів
    tags = generate_tags(raw_vacancy_data)
    processed_data.update(tags)
    
    # 3. Перевірка на дублікат (оновлення, якщо вже існує)
    vacancies_collection.update_one(
        {'id_source': processed_data['id_source']},
        {'$set': processed_data},
        upsert=True # Якщо не знайдено, створити новий (insert)
    )
    print(f"✅ Збережено/Оновлено: {processed_data['title']} | Теги: {', '.join(processed_data['tags_tech'])}")


# --- ФУНКЦІЯ ПАРСИНГУ ROBOTA.UA ---

def fetch_and_process_jobs_robota():
    """Виконує API-запити до Robota.ua та обробляє дані."""
    
    total_processed = 0
    
    for company_id in COMPANY_IDS:
        page = 0
        company_processed = 0
        
        while True:
            # 1. Формування параметрів запиту
            params = {
                'CompanyId': company_id,
                'page': page,
                'count': VACANCIES_PER_PAGE
            }
            
            try:
                # 2. Виконання HTTP-запиту
                response = requests.get(ROBOTA_API_URL, params=params, timeout=10)
                response.raise_for_status() # Виклик помилки для поганих статус-кодів
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"❌ Помилка запиту до Robota.ua (ID: {company_id}, сторінка {page}): {e}")
                break

            documents = data.get('documents', [])
            total_vacancies = data.get('total', 0)

            if not documents:
                break # Вакансії на цій сторінці закінчилися

            # 3. Обробка та збереження
            for doc in documents:
                save_vacancy(doc)
                total_processed += 1
                company_processed += 1
                
            print(f"-> Оброблено {company_processed} з {total_vacancies} вакансій компанії ID {company_id}")

            # 4. Перехід на наступну сторінку та пауза
            page += 1
            if company_processed >= total_vacancies or page * VACANCIES_PER_PAGE >= 1000:
                break # Захист від нескінченного циклу або досягнення ліміту
            
            time.sleep(1) # Пауза 1 секунда між запитами для уникнення блокування

    print(f"\n--- ЕТАП ROBOTA.UA ЗАВЕРШЕНО. Обробка {total_processed} вакансій. ---")


if __name__ == "__main__":
    # 1. Перевірка з'єднання з MongoDB
    try:
        client.admin.command('ping')
        print("✅ З'єднання з MongoDB успішно встановлено!")
        
        # 2. Запуск парсингу
        fetch_and_process_jobs_robota()
        
    except Exception as e:
        print(f"❌ Помилка з'єднання з MongoDB. Переконайтесь, що Docker запущено: {e}")