from pymongo import MongoClient
from typing import List, Dict
import os

# --- НАЛАШТУВАННЯ ---

# Використовуйте вашу локальну URI
MONGO_URI = "mongodb://user:password@localhost:27017/" 
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.jobswipe_db
company_id_collection = db.company_ids 

# ВАШ ПОВНИЙ СПИСОК ID КОМПАНІЙ
# Додайте всі ID, які ви зібрали, до цього списку:
FULL_COMPANY_ID_LIST: List[int] = [
    6627493,  # SKELAR    
    782154,  # Genesis
    # ДОДАЙТЕ ВСІ ВАШІ КОМПАНІЇ СЮДИ
    5319794,  # FRACTAL (ex-Netpeak Group)
    # ...
]

def insert_new_company_batch(new_ids: List[int]):
    """
    Вставляє список ID компаній у колекцію company_ids, 
    уникаючи вставлення вже існуючих ID.
    """
    if not new_ids:
        print("Список нових ID порожній. Вставлення скасовано.")
        return

    print(f"-> Починаємо перевірку та вставлення {len(new_ids)} ID...")

    # Отримуємо ID, які вже є в базі, для уникнення дублікатів
    existing_ids = {doc['company_id'] for doc in company_id_collection.find({}, {'_id': 0, 'company_id': 1})}
    
    # Фільтруємо список: залишаємо лише ті ID, яких немає в базі
    ids_to_insert = [id for id in new_ids if id not in existing_ids]

    if not ids_to_insert:
        print("✅ Усі ID зі списку вже є в колекції. Нових вставлень не відбулося.")
        return
        
    # Перетворення простого списку на формат MongoDB [{"company_id": ID}, ...]
    documents_to_insert = [{'company_id': id} for id in ids_to_insert]

    try:
        # insert_many виконує вставку всіх нових документів одним запитом
        result = company_id_collection.insert_many(documents_to_insert)
        
        print(f"✅ Успішно вставлено {len(result.inserted_ids)} нових ID компаній.")
        print(f"   ({len(new_ids) - len(ids_to_insert)} ID були пропущені як дублікати).")
        
    except Exception as e:
        print(f"❌ Помилка при масовій вставці: {e}")


if __name__ == "__main__":
    try:
        # Перевірка з'єднання
        client.admin.command('ping')
        print("✅ З'єднання з MongoDB успішно встановлено!")
        
        # Запуск вставки
        insert_new_company_batch(FULL_COMPANY_ID_LIST)
        
    except Exception as e:
        print(f"❌ Помилка з'єднання з MongoDB. Переконайтесь, що Docker запущено: {e}")