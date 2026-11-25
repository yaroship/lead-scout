import re
from typing import Tuple, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Черный список известных сетевых франшиз (чтобы искать только независимый бизнес)
FRANCHISE_BLACKLIST = [
    # Барбершопы
    "oldboy", "олдбой", "topgun", "топган", "borodach", "бородач", "chop-chop", "чоп-чоп",
    "чоп чоп", "бритва", "britva", "площадка", "супермен", "supermen", "big bro", "биг бро",
    "франт", "frant", "13 by timati", "барбершоп 13", "честер", "chester", "headshot",
    
    # Салоны красоты, ногти, эпиляция
    "точка красоты", "персона", "persona", "моне", "mone", "пальчики", "palchiki",
    "4hands", "4 hands", "saxap", "сахар", "кисти", "прядки в порядке", "laserlove",
    "лазерлав", "чио чио", "chio chio", "цирюльникъ", "цирюльник",
    
    # Цветы
    "flowwow", "флоувов", "союзцветторг", "цветовик", "простоцветы", "мосцветторг",
    "ирис", "цветочный ряд",
    
    # Спа и массаж
    "тайрай", "tairai", "wai thai", "вай тай", "asia beauty spa", "royal thai",
    "роял тай", "твойтай",
    
    # Общепит и сети доставки
    "додо", "dodo", "папа джонс", "papa john", "доминос", "domino", "ташир",
    "пиццафабрика", "вкусно и точка", "ростикс", "rostics", "kfc", "бургер кинг",
    "burger king", "ёбидоёби", "yobidoyobi", "суши wok", "сушивок", "суши маркет",
    "шоколадница", "кофемания", "stars coffee", "one price coffee", "cofix", "кофикс"
]

def check_franchise(company_name: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет название компании на принадлежность к франшизам.
    Возвращает (is_franchise, brand_name).
    """
    if not company_name:
        return False, None
    name_clean = company_name.lower().replace("-", " ")
    for brand in FRANCHISE_BLACKLIST:
        brand_norm = brand.replace("-", " ")
        if re.search(rf"\b{re.escape(brand_norm)}\b", name_clean) or brand_norm in name_clean:
            return True, brand
    return False, None

def clean_company_name(raw_name: str) -> str:
    """Очищает название компании от длинных описательных хвостов 2GIS."""
    if not raw_name:
        return ""
    name = raw_name.strip()
    # Убираем типичные хвосты через разделители
    for sep in [" — ", " - ", " | ", ", сеть ", ", студия ", ", салон ", ", центр "]:
        if sep in name:
            parts = name.split(sep)
            if len(parts[0].strip()) >= 3:
                name = parts[0].strip()
    return name

def clean_website(url: Optional[str]) -> str:
    """Удаляет UTM-метки, клик-ид и трекеры из ссылки на сайт."""
    if not url:
        return ""
    u = str(url).strip()
    if not u:
        return ""
    bad_params = {"yclid", "gclid", "fbclid", "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "_openstat"}
    try:
        p = urlparse(u if "://" in u else "https://" + u)
        q = parse_qsl(p.query, keep_blank_values=False)
        clean_q = [(k, v) for k, v in q if k.lower() not in bad_params and not k.lower().startswith("utm_")]
        new_q = urlencode(clean_q)
        path = p.path.rstrip("/")
        res = urlunparse((p.scheme, p.netloc, path, "", new_q, ""))
        return res.rstrip("?")
    except Exception:
        return re.sub(r"\?(?:yclid|utm_[^&]+|gclid)[^#]*", "", u).rstrip("?&/")

def format_phone(phone: str) -> Tuple[str, str]:
    """
    Нормализует телефон к формату +7XXXXXXXXXX и определяет тип:
    - mobile: мобильный номер (+7 9xx...) - идеально для WhatsApp/Telegram
    - tollfree: горячая линия (8-800...)
    - landline: городской номер
    - unknown: неизвестно
    """
    if not phone:
        return "", "unknown"
    digits = re.sub(r"\D", "", phone)
    
    if len(digits) == 11 and digits.startswith(("7", "8")):
        normalized = "+7" + digits[1:]
    elif len(digits) == 10:
        normalized = "+7" + digits
    else:
        return phone.strip(), "unknown"
        
    # Детект типа номера
    prefix = normalized[2:5]
    if prefix.startswith("9"):
        phone_type = "mobile"
    elif prefix == "800":
        phone_type = "tollfree"
    else:
        phone_type = "landline"
        
    return normalized, phone_type
