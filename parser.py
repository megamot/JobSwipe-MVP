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

# URL для Robota.ua API
ROBOTA_COMPANY_VACANCIES_BASE_URL = "https://api.rabota.ua/company/{companyId}/vacancies"
ROBOTA_COMPANY_BASE_URL = "https://api.rabota.ua/company/{companyId}"

def get_company_ids() -> List[int]:
    """Отримує список всіх ID компаній з колекції company_ids."""
    try:
        companies = db.company_ids.find({}, {'company_id': 1, '_id': 0})
        return [company['company_id'] for company in companies]
    except Exception as e:
        print(f"❌ Помилка отримання списку компаній з MongoDB: {e}")
        return []

def update_company_status(company_id: int, success: bool = True, error_message: str = None):
    """Оновлює статус та час парсингу компанії."""
    update_data = {
        'last_parsed': datetime.now(UTC),
        'last_status': 'success' if success else 'error'
    }
    if error_message:
        update_data['last_error'] = error_message
    
    try:
        db.company_ids.update_one(
            {'company_id': company_id},
            {'$set': update_data}
        )
    except Exception as e:
        print(f"❌ Помилка оновлення статусу компанії {company_id}: {e}")

def save_vacancy(raw_vacancy_data: Dict):
    """Очищає, тегує та зберігає вакансію в MongoDB."""
    
    vacancy_id = raw_vacancy_data.get('id')
    raw_description = raw_vacancy_data.get('description', '')

    # URL формуємо на основі ID компанії та вакансії
    source_url = f"https://robota.ua/company{raw_vacancy_data['notebookId']}/vacancy{vacancy_id}"

    # 1. Створення основного документа
    processed_data = {
        'id_source': f"robota_{vacancy_id}",
        'source_url': source_url,
        'name': raw_vacancy_data.get('name', 'N/A'),
        'companyName': raw_vacancy_data.get('companyName', 'N/A'),
        'cityId': raw_vacancy_data.get('cityId'),
        'vacancyAddress': raw_vacancy_data.get('vacancyAddress', 'N/A'),
        'description': get_raw_description(raw_description),
        'shortDescription': raw_vacancy_data.get('shortDescription'),
        'date': raw_vacancy_data.get('date'),
        'date_parsed': datetime.now(UTC),
    }
    
    # 2. Генерація тегів
    tags = generate_tags(raw_vacancy_data)
    processed_data.update(tags)
    
    # 3. Оновлення/вставка в базу даних
    vacancies_collection.update_one(
        {'id_source': processed_data['id_source']},
        {'$set': processed_data},
        upsert=True
    )
    print(f"✅ Збережено/Оновлено: {processed_data['name']} | Теги: {', '.join(processed_data['tags_tech'])}")

def fetch_and_process_jobs_robota():
    """
    1. Отримує список компаній з колекції company_ids
    2. Парсить компанії та їх вакансії
    3. Оновлює статус парсингу кожної компанії
    """
    total_processed = 0
    companies_to_parse = get_company_ids()
    
    if not companies_to_parse:
        print("ℹ️ Немає компаній для парсингу. Додайте компанії через init_db.py")
        return
    
    print(f"📋 Знайдено {len(companies_to_parse)} компаній для обробки")
    
    for company_id in companies_to_parse:
        # --- 1. Парсинг компанії ---
        company_url = ROBOTA_COMPANY_BASE_URL.format(companyId=company_id)
        try:
            company_resp = requests.get(company_url, timeout=10)
            company_resp.raise_for_status()
            company_data = company_resp.json()
            
            # Зберігаємо дані компанії
            companies_collection.update_one(
                {'id': company_data.get('id')},
                {'$set': company_data},
                upsert=True
            )
            print(f"✅ Компанія {company_data.get('name', company_id)} збережена/оновлена.")
            
        except Exception as e:
            error_msg = f"Помилка парсингу компанії: {str(e)}"
            print(f"❌ {error_msg}")
            update_company_status(company_id, success=False, error_message=error_msg)
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
                update_company_status(company_id, success=True)
                continue

            company_name = documents[0].get('companyName', f'ID {company_id}')
            company_processed = 0

            for doc in documents:
                doc['notebookId'] = company_id
                save_vacancy(doc)
                total_processed += 1
                company_processed += 1

            print(f"✅ Оброблено {company_processed} з {total_vacancies} вакансій компанії {company_name}")
            update_company_status(company_id, success=True)
            
            time.sleep(1)  # Антиспам пауза
            
        except Exception as e:
            error_msg = f"Помилка парсингу вакансій: {str(e)}"
            print(f"❌ {error_msg}")
            update_company_status(company_id, success=False, error_message=error_msg)
            time.sleep(2)
            continue

    print(f"\n🎉 ПАРСИНГ ЗАВЕРШЕНО")
    print(f"📊 Всього оброблено {total_processed} вакансій з {len(companies_to_parse)} компаній")

if __name__ == "__main__":
    try:
        # Перевірка з'єднання з MongoDB
        client.admin.command('ping')
        print("✅ З'єднання з MongoDB встановлено!")
        
        # Запуск парсингу
        fetch_and_process_jobs_robota()
        
    except Exception as e:
        print(f"❌ Помилка з'єднання з MongoDB: {e}")