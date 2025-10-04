from pymongo import MongoClient
import sys

try:
    # З'єднання з MongoDB (застосовуємо ваші облікові дані з docker-compose.yml)
    MONGO_URI = "mongodb://user:password@localhost:27017/"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # Спроба перевірити з'єднання
    client.admin.command('ping')
    
    print("✅ Успіх! Бібліотеки встановлено, і з'єднання з MongoDB встановлено коректно.")
    
except Exception as e:
    print(f"❌ Помилка з'єднання або встановлення: {e}")
    sys.exit(1)
finally:
    client.close()