import re
from typing import List, Dict

# 1. МАПІНГ РІВНІВ (Специфічний для Robota.ua, на основі аналізу)
# Використовуємо profLevelId, коли він доступний, як найбільш надійне джерело рівня.
# 2=Junior, 3=Middle/Specialist, 4=Senior/Lead.
ROBOTA_LEVEL_MAPPING: Dict[int, str] = {
    1: "#Trainee",
    2: "#Junior",
    3: "#Middle",
    4: "#Senior",
    5: "#Executive"
}

# 2. ТЕГУВАННЯ НАПРЯМКІВ та ТЕХНОЛОГІЙ (tags_tech)
# Використовується для пошуку у заголовку та описі
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
    34: "#Варшава", # cityId: 34 для цієї вакансії
    # 0 використовуємо для remote, якщо не вказано інше
}

# --- ФУНКЦІЇ ОБРОБКИ ТА ТЕГУВАННЯ ---

def clean_html(raw_html: str) -> str:
    """Видаляє HTML-теги та зайві пробіли."""
    cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    cleantext = re.sub(cleanr, '', raw_html)
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
        tags.add("#Київ_Поділ")

    return list(tags)


def generate_tags(vacancy: Dict) -> Dict[str, List[str]]:
    """Головна функція для генерації тегів на основі JSON-вакансії."""
    
    title = vacancy.get('name', '').lower()
    description_cleaned = clean_html(vacancy.get('description', ''))
    full_text = title + " " + description_cleaned
    
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
    
    # Встановлюємо тег Venture Builder, оскільки це загальний тег SKELAR
    if 'skelar' in company_name or 'venture builder' in full_text:
         company_tags.add("#Venture_Builder")
    
    # 4. Тегування ГЕОГРАФІЇ
    city_id = vacancy.get('cityId', 0)
    address = vacancy.get('vacancyAddress', '')
    company_tags.update(get_geo_tags(city_id, address))

    # 5. Додаткове тегування РІВНЯ з title (якщо ID не було або для DOU/Jooble)
    if not any(tag.startswith('#') and tag[1].isupper() for tag in tech_tags): # Перевіряємо, чи вже є тег рівня
        if 'senior' in title or 'lead' in title:
             tech_tags.add("#Senior")
        elif 'junior' in title or 'trainee' in title:
             tech_tags.add("#Junior")


    return {
        'tags_tech': sorted(list(tech_tags)),
        'tags_company': sorted(list(company_tags))
    }