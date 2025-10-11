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

# 2. ТЕГУВАННЯ Посади та Компетенції (Програми, Мови) - Адміністративний напрямок

ADMIN_DIRECTION_TAGS: Dict[str, List[str]] = {
    # Посади / Roles
    "#OfficeManager": ['офіс-менеджер', 'office manager', 'адміністратор офісу', 'head of office', 'administration'],
    "#ExecutiveAssistant": ['асистент керівника', 'помічник керівника', 'executive assistant', 'personal assistant', 'pa', 'виконавчий асистент'],
    "#AdministrativeAssistant": ['адміністративний асистент', 'admin assistant', 'administrative support', 'адміністративна підтримка', 'секретар', 'receptionist', 'адміністратор'],
    "#ProcurementManager": ['менеджер із закупівель', 'procurement specialist', 'purchasing manager', 'закупник', 'buyer', 'фахівець з постачання', 'постачальник'],
    "#SaleAssistant": ['sale assistant', 'sale support', 'асистент з продажів', 'менеджер з продажу', 'продавець-консультант', 'sales'],
    "#BusinessOwner": ['підприємець', 'керівник', 'власний бізнес', 'business owner', 'founder', 'ceo', 'керівник кондитерської'],
    "#LogisticsManager": ['менеджер з транспорту', 'логіст', 'координація логістики', 'logistics', 'transport manager', 'складання маршрутів', 'supply chain'],

    # Компетенції / Competencies
    "#DocumentManagement": ['документообіг', 'договірна робота', 'робота з документами', 'супровід документообігу', 'договори', 'contract management'],
    "#OfficeMaintenance": ['підтримка життєдіяльності офісу', 'життєдіяльність офісу', 'office support', 'адміністративно-господарська діяльність', 'забезпечення офісу'],
    "#VendorManagement": ['взаємодія з постачальниками', 'пошук постачальників', 'робота з постачальниками', 'постачання', 'vendors', 'постачальники'],
    "#CustomerService": ['робота з клієнтами', 'клієнтський сервіс', 'customer service', 'customer support', 'обслуговування клієнтів'],
    "#Purchasing": ['закупівлі', 'постачання продукції', 'замовлення', 'контроль постачання', 'buying', 'procurement'],
    "#StaffManagement": ['управління персоналом', 'підбір персоналу', 'team management', 'керівництво командою'],
    "#Budgeting": ['бюджетування', 'фінансовий контроль', 'кошторис', 'фінанси'],
    "#PrimaryAccounting": ['ведення первинної бухгалтерії', 'первинна документація', 'робота в 1с', 'координація з бухгалтерією', 'invoices', 'бухгалтерія', 'cash'],

    # Програми / Tools
    "#1C": ['1с', '1с:бухгалтерія', 'робота в 1с'],
    "#MicrosoftOffice": ['microsoft office', 'word', 'excel', 'powerpoint', 'MS office'],
    "#CRM": ['crm', 'customer relationship management', 'срм'],
    "#Trello": ['trello', 'трелло', 'project management tool'],
    "#PhotoshopAdobe": ['photoshop', 'adobe', 'графічні редактори', 'дизайн'],

    # Мови / Languages
 # Рівні англійської мови
    "#EnglishBeginner": ['англійська початковий', 'beginner', 'a1', 'a2', 'elementary', 'pre-intermediate', 'базовий'],
    "#EnglishIntermediate": ['англійська середній', 'intermediate', 'b1', 'b2', 'upper-intermediate', 'середній', 'розмовний', 'розмовна англійська'],
    "#EnglishAdvanced": ['англійська просунутий', 'advanced', 'c1', 'c2', 'fluent', 'proficiency', 'вільно', 'просунутий', 'вільне володіння', 'native speaker', 'рідна мова'],

    # Загальні та описові теги
    "#English": ['англійська', 'english', 'мова', 'language', 'іноземна'],
    "#UkrainianFluent": ['українська', 'вільно', 'ukrainian', 'fluent', 'рідна мова'],
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
    
    # 2. Тегування АДМІНІСТРАТИВНОГО НАПРЯМКУ
    for tag, keywords in ADMIN_DIRECTION_TAGS.items():
        if any(keyword in full_text for keyword in keywords):
            tech_tags.add(tag)

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