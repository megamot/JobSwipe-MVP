import re
from typing import List, Dict

# 1. МАПІНГ РІВНІВ (Специфічний для Robota.ua, на основі аналізу)
ROBOTA_LEVEL_MAPPING: Dict[int, str] = {
    1: "#Trainee",
    2: "#Junior",
    3: "#Middle",
    4: "#Senior",
    5: "#Executive"
}

# 2. ТЕГУВАННЯ НАПРЯМКІВ та ТЕХНОЛОГІЙ (tags_tech)
TECH_DIRECTION_TAGS: Dict[str, List[str]] = {
    # IT Розробка та Data
    "#Backend": ['java', 'python', 'node.js', 'golang', 'php', 'django', 'backend'],
    "#Frontend": ['react', 'vue', 'angular', 'javascript', 'typescript', 'frontend'],
    "#QA_Testing": ['qa', 'тестувальник', 'tester', 'selenium', 'cypress', 'automation'],
    "#Data": ['analyst', 'reporting', 'data-driven', 'sql', 'big data', 'bi', 'tableau'],
    
    # Креативні та Маркетинг
    "#Marketing": ['маркетинг', 'smm', 'ppc', 'creative', 'performance', 'ads', 'google ads', 'meta ads', 'копірайтер'],
    "#Design": ['designer', 'графічний', 'motion', 'figma', 'photoshop', 'illustrator', 'ui/ux'],
    
    # Бізнес та Адмін
    "#Product": ['product manager', 'product marketing', 'продуктова', 'продукту', 'продакт'],
    "#Support_CS": ['support', 'customer experience', 'клієнтський сервіс', 'сапорт', 'customer support'],
    "#Legal_Finance": ['legal', 'counsel', 'юридичний', 'finance', 'acounting', 'payroll', 'бух. обліку'],
    "#HR_Admin": ['rekruting', 'admin', 'travel manager', 'office manager', 'клінінг'],
    
    # Інші, що часто зустрічаються
    "#SEO": ['seo', 'linkbuilder', 'serp', 'sem'],
    "#AI_ML": ['ai', 'штучний інтелект', 'midjourney', 'runway', 'elevenlabs', 'sora']
}

# 3. ТЕГУВАННЯ ТИПУ КОМПАНІЇ та ГЕОГРАФІЇ (tags_company)
COMPANY_TYPE_TAGS: Dict[str, List[str]] = {
    "#Продуктова_компанія": ['product company', 'продуктова компанія', 'venture builder', 'стартап', 'startup', 'власний продукт'],
    "#Аутсорс": ['аутсорс', 'outsource', 'аутстаф'],
    "#EdTech": ['brighterly', 'онлайн школу з вивчення математики'],
    "#Entertainment": ['storyby', 'dramashorts', 'alphanovel', 'стрімінг', 'novels', 'романи'],
}

GEOGRAPHY_MAPPING: Dict[int, str] = {
    1: "#Київ",  # cityId: 1
    2: "#Харків",
    3: "#Одеса",
    4: "#Дніпро",
    5: "#Львів",
    34: "#Варшава", 
}


# --- ФУНКЦІЇ ОБРОБКИ ТА ТЕГУВАННЯ ---

def get_raw_description(raw_html: str) -> str:
    """
    Повертає необроблений HTML-рядок. 
    Усі HTML-теги будуть збережені для відображення у браузері.
    """
    return raw_html  # Повертаємо, як є, для відображення


def get_text_for_tagging(text: str) -> str:
    """
    Готує текст для NLP/тегування: видаляє HTML, переводить в нижній регістр та нормалізує пробіли.
    """
    # 1. Видалення всіх HTML-тегів та HTML-сутностей
    cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    cleantext = re.sub(cleanr, '', text)
    
    # 2. Переводимо в нижній регістр та нормалізуємо всі пробіли
    return ' '.join(cleantext.split()).lower()


def get_geo_tags(city_id: int, address: str) -> List[str]:
    """Генерує гео-теги на основі ID та адреси."""
    tags = set()
    address_lower = address.lower()
    
    # 1. Тегування за City ID
    if city_id in GEOGRAPHY_MAPPING:
        tags.add(GEOGRAPHY_MAPPING[city_id])
    
    # 2. Тегування за ключовими словами в адресі
    if 'warsaw' in address_lower or 'poland' in address_lower:
        tags.add("#Польща")
    if 'remote' in address_lower or 'віддалено' in address_lower:
         tags.add("#Віддалено")
    
    # 3. Тегування метро/районів (наприклад, для Києва)
    if 'костянтинівська, 71' in address_lower or 'поділ' in address_lower:
         # Додаємо тег для Києва, якщо його не було в city_id
         tags.add("#Київ")
         tags.add("#Київ_Поділ")

    return list(tags)


def generate_tags(vacancy: Dict) -> Dict[str, List[str]]:
    """Головна функція для генерації тегів на основі JSON-вакансії."""
    
    title = vacancy.get('name', '')
    raw_description = vacancy.get('description', '')
    
    # ВИКОРИСТОВУЄМО ОЧИЩЕНИЙ ТЕКСТ ДЛЯ ТЕГУВАННЯ (викликаємо нову логіку)
    description_for_tagging = get_text_for_tagging(raw_description)
    title_for_tagging = title.lower()
    
    full_text = title_for_tagging + " " + description_for_tagging
    
    tech_tags = set()
    company_tags = set()
    
    # 1. Тегування РІВНЯ (Пріоритет - profLevelId)
    level_id = vacancy.get('profLevelId')
    if level_id in ROBOTA_LEVEL_MAPPING:
        tech_tags.add(ROBOTA_LEVEL_MAPPING[level_id])
    
    # 2. Тегування НАПРЯМКІВ та ТЕХНОЛОГІЙ
    for tag, keywords in TECH_DIRECTION_TAGS.items():
        if any(keyword in full_text for keyword in keywords):
            tech_tags.add(tag)

    # 3. Тегування ТИПУ КОМПАНІЇ та ГЕОГРАФІЇ
    company_name = vacancy.get('companyName', '').lower()
    for tag, keywords in COMPANY_TYPE_TAGS.items():
        if any(keyword in full_text or keyword in company_name for keyword in keywords):
            company_tags.add(tag)
    
    # Встановлюємо тег Venture Builder
    if 'skelar' in company_name or 'venture builder' in full_text:
         company_tags.add("#Venture_Builder")
    
    # 4. Тегування ГЕОГРАФІЇ
    city_id = vacancy.get('cityId', 0)
    address = vacancy.get('vacancyAddress', '')
    company_tags.update(get_geo_tags(city_id, address))

    # 5. Додаткове тегування РІВНЯ з title
    if not any(tag.startswith('#') and tag[1].isupper() for tag in tech_tags):
        if 'senior' in title_for_tagging or 'lead' in title_for_tagging:
             tech_tags.add("#Senior")
        elif 'junior' in title_for_tagging or 'trainee' in title_for_tagging:
             tech_tags.add("#Junior")


    return {
        'tags_tech': sorted(list(tech_tags)),
        'tags_company': sorted(list(company_tags))
    }