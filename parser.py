from pymongo import MongoClient
from tagging_config import generate_tags, clean_html_for_display
from datetime import datetime, UTC # <<< ІМПОРТУЄМО UTC
from typing import Dict, List
import requests
import time

# --- НАЛАШТУВАННЯ ---
MONGO_URI = "mongodb://user:password@localhost:27017/"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.jobswipe_db
vacancies_collection = db.vacancies 

# URL для Robota.ua API пошуку (буде використаний для динамічного формування)
ROBOTA_COMPANY_VACANCIES_BASE_URL = "https://api.rabota.ua/company/{companyId}/vacancies"

# Параметри для імітації "ТОП-роботодавців" (додайте сюди ваші ID)
COMPANY_IDS = [
    6627493,  # SKELAR
    720,      # Приклад компанії з вашого JS (якщо вона не має вакансій, це перевірить виправлення)
    # Додайте інші ID компаній тут
]
# VACANCIES_PER_PAGE = 50 # Не потрібен для цього типу API

# --- ФУНКЦІЇ БАЗИ ДАНИХ ---

def save_vacancy(raw_vacancy_data: Dict):
    """Очищає, тегує та зберігає вакансію в MongoDB."""
    
    vacancy_id = raw_vacancy_data.get('id')
    raw_description = raw_vacancy_data.get('description', '') # Оригінальний опис з HTML

    # URL формуємо на основі ID компанії (notebookId) та вакансії (id)
    source_url = f"https://robota.ua/company/{raw_vacancy_data['notebookId']}/vacancy/{vacancy_id}"

    # 1. Створення основного документа
    processed_data = {
        'id_source': f"robota_{vacancy_id}",
        'source_url': source_url,
        'title': raw_vacancy_data.get('name', 'N/A'),
        'company_name': raw_vacancy_data.get('companyName', 'N/A'),
        'salary_min': raw_vacancy_data.get('salary', 0), 
        'salary_max': raw_vacancy_data.get('salary', 0), 
        'city': raw_vacancy_data.get('vacancyAddress', 'N/A'),
        
        # <<< ВИПРАВЛЕНО: ЗБЕРІГАЄМО ТЕКСТ ДЛЯ ВІДОБРАЖЕННЯ >>>
        'full_description': clean_html_for_display(raw_description), 
        
        'date_published': raw_vacancy_data.get('date'),
        'date_parsed': datetime.now(UTC), 
    }
    
    # 2. Генерація тегів (логіка тегування тепер використовує внутрішню очистку для NLP)
    tags = generate_tags(raw_vacancy_data)
    processed_data.update(tags)
    
    # 3. Перевірка на дублікат (оновлення, якщо вже існує)
    vacancies_collection.update_one(
        {'id_source': processed_data['id_source']},
        {'$set': processed_data},
        upsert=True 
    )
    print(f"✅ Збережено/Оновлено: {processed_data['title']} | Теги: {', '.join(processed_data['tags_tech'])}")


# --- ФУНКЦІЯ ПАРСИНГУ ROBOTA.UA ---

def fetch_and_process_jobs_robota():
    """Виконує API-запити до Robota.ua для кожної компанії та обробляє дані."""
    
    total_processed = 0
    
    for company_id in COMPANY_IDS:
        # 1. Формування повного URL для поточної компанії
        company_url = ROBOTA_COMPANY_VACANCIES_BASE_URL.format(companyId=company_id)
        
        try:
            # 2. Виконання HTTP-запиту
            response = requests.get(company_url, timeout=10)
            response.raise_for_status() 
            data = response.json()
            
            documents = data.get('documents', [])
            total_vacancies = len(documents)

            # <<< ВИПРАВЛЕНО: БЕЗПЕЧНЕ ОТРИМАННЯ НАЗВИ КОМПАНІЇ >>>
            if not documents:
                company_name = f'ID {company_id}'
                print(f"-> Компанія {company_name}: Не знайдено активних вакансій.")
                continue
            
            # Якщо вакансії є, беремо назву компанії з першого документа
            company_name = documents[0].get('companyName', f'ID {company_id}')

            # 3. Обробка та збереження
            company_processed = 0
            for doc in documents:
                # Додаємо CompanyId до doc, щоб save_vacancy могла сформувати коректний source_url
                doc['notebookId'] = company_id 
                save_vacancy(doc)
                total_processed += 1
                company_processed += 1
                
            print(f"✅ Оброблено {company_processed} з {total_vacancies} вакансій компанії {company_name} (ID {company_id}).")

            # 4. Пауза між запитами
            time.sleep(1) 

        except requests.exceptions.RequestException as e:
            print(f"❌ Помилка запиту до Robota.ua (ID: {company_id}): {e}")
            time.sleep(2) 
            continue

    print(f"\n--- ЕТАП ROBOTA.UA ЗАВЕРШЕНО. Всього оброблено {total_processed} вакансій. ---")


if __name__ == "__main__":
    # 1. Перевірка з'єднання з MongoDB
    try:
        client.admin.command('ping')
        print("✅ З'єднання з MongoDB успішно встановлено!")
        
        # 2. Запуск парсингу
        fetch_and_process_jobs_robota()
        
    except Exception as e:
        print(f"❌ Помилка з'єднання з MongoDB. Переконайтесь, що Docker запущено: {e}")