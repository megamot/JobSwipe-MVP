
from pymongo import MongoClient
from tagging_config import generate_tags, get_raw_description
from datetime import datetime, UTC
from typing import Dict, List
import requests
import time

# --- НАЛАШТУВАННЯ ---

MONGO_URI = "mongodb://user:password@localhost:27017/"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.jobswipe_db
vacancies_collection = db.vacancies
companies_collection = db.companies
users_collection = db.users

# URL для Robota.ua API пошуку (буде використаний для динамічного формування)
ROBOTA_COMPANY_VACANCIES_BASE_URL = "https://api.rabota.ua/company/{companyId}/vacancies"
ROBOTA_COMPANY_BASE_URL = "https://api.rabota.ua/company/{companyId}"

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
    source_url = f"https://robota.ua/company{raw_vacancy_data['notebookId']}/vacancy{vacancy_id}"

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
        'full_description': get_raw_description(raw_description),  
        
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
    """
    1. Парсить компанії (GET /company/{id}) і зберігає в companies (upsert).
    2. Парсить вакансії (GET /company/{id}/vacancies) і зберігає всі поля в vacancies (upsert).
    3. Тегування — лише копія, не змінює оригінал.
    """
    total_processed = 0
    for company_id in COMPANY_IDS:
        # --- 1. Парсинг компанії ---
        company_url = ROBOTA_COMPANY_BASE_URL.format(companyId=company_id)
        try:
            company_resp = requests.get(company_url, timeout=10)
            company_resp.raise_for_status()
            company_data = company_resp.json()
            # Зберігаємо всі поля компанії (upsert)
            companies_collection.update_one(
                {'id': company_data.get('id')},
                {'$set': company_data},
                upsert=True
            )
            print(f"✅ Компанія {company_data.get('name', company_id)} збережена/оновлена.")
        except Exception as e:
            print(f"❌ Помилка парсингу компанії (ID: {company_id}): {e}")
            continue

        # --- 2. Парсинг вакансій ---
        vacancies_url = ROBOTA_COMPANY_VACANCIES_BASE_URL.format(companyId=company_id)
        try:
            response = requests.get(vacancies_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            documents = data.get('documents', [])
            total_vacancies = len(documents)
            if not documents:
                print(f"-> Компанія ID {company_id}: Не знайдено активних вакансій.")
                continue
            company_name = documents[0].get('companyName', f'ID {company_id}')
            company_processed = 0
            for doc in documents:
                doc['notebookId'] = company_id
                # --- Тегування на копії ---
                doc_copy = dict(doc)
                tags = generate_tags(doc_copy)
                doc_copy.update(tags)
                # Зберігаємо всі поля з тегами (upsert)
                vacancies_collection.update_one(
                    {'id_source': f"robota_{doc_copy.get('id')}"},
                    {'$set': doc_copy},
                    upsert=True
                )
                total_processed += 1
                company_processed += 1
            print(f"✅ Оброблено {company_processed} з {total_vacancies} вакансій компанії {company_name} (ID {company_id}).")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Помилка парсингу вакансій (ID: {company_id}): {e}")
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