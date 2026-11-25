import urllib.request
import urllib.parse
import re
import json
import random
import time
from typing import List, Dict, Any, Optional

from .filter import clean_company_name, check_franchise, clean_website, format_phone

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
]

CITY_SLUGS = {
    # Миллионники
    "москва": "moscow",
    "санкт-петербург": "spb",
    "питер": "spb",
    "новосибирск": "novosibirsk",
    "екатеринбург": "ekaterinburg",
    "казань": "kazan",
    "нижний новгород": "n_novgorod",
    "челябинск": "chelyabinsk",
    "красноярск": "krasnoyarsk",
    "самара": "samara",
    "уфа": "ufa",
    "ростов-на-дону": "rostov",
    "ростов": "rostov",
    "краснодар": "krasnodar",
    "омск": "omsk",
    "воронеж": "voronezh",
    "пермь": "perm",
    "волгоград": "volgograd",

    # Крупные города
    "саратов": "saratov",
    "тюмень": "tyumen",
    "тольятти": "tolyatti",
    "ижевск": "izhevsk",
    "барнаул": "barnaul",
    "ульяновск": "ulyanovsk",
    "иркутск": "irkutsk",
    "хабаровск": "khabarovsk",
    "ярославль": "yaroslavl",
    "владивосток": "vladivostok",
    "махачкала": "makhachkala",
    "томск": "tomsk",
    "оренбург": "orenburg",
    "кемерово": "kemerovo",
    "новокузнецк": "novokuznetsk",
    "рязань": "ryazan",
    "набережные челны": "chelny",
    "челны": "chelny",
    "пенза": "penza",
    "липецк": "lipetsk",
    "тула": "tula",
    "сочи": "sochi",
    "калининград": "kaliningrad",
    "курск": "kursk",
    "тверь": "tver",
    "магнитогорск": "magnitogorsk",
    "иваново": "ivanovo",
    "брянск": "bryansk",
    "сургут": "surgut",
    "белгород": "belgorod",
    "владимир": "vladimir",
    "чита": "chita",
    "архангельск": "arkhangelsk",
    "калуга": "kaluga",
    "смоленск": "smolensk",
    "волжский": "volzhsky",
    "череповец": "cherepovets",
    "саранск": "saransk",
    "вологда": "vologda",
    "якутск": "yakutsk",
    "владикавказ": "vladikavkaz",
    "грозный": "grozny",
    "мурманск": "murmansk",
    "тамбов": "tambov",
    "петрозаводск": "petrozavodsk",
    "кострома": "kostroma",
    "нижневартовск": "nizhnevartovsk",
    "новороссийск": "novorossiysk",
    "йошкар-ола": "yoshkarola",
    "таганрог": "taganrog",
    "комсомольск-на-амуре": "komsomolsk",
    "сыктывкар": "syktyvkar",
    "нальчик": "nalchik",
    "шахты": "shakhty",
    "дзержинск": "dzerzhinsk",
    "орск": "orsk",
    "братск": "bratsk",
    "ангарск": "angarsk",
    "энгельс": "engels",
    "благовещенск": "blagoveshchensk",
    "старыйоскол": "staryoskol",
    "великий новгород": "novgorod",
    "псков": "pskov",
    "бийск": "biysk",
    "прокопьевск": "prokopyevsk",
    "рыбинск": "rybinsk",
    "балаково": "balakovo",
    "армавир": "armavir",
    "северодвинск": "severodvinsk",
    "петропавловск-камчатский": "kamchatsk",
    "абакан": "abakan",
    "норильск": "norilsk",
    "сызрань": "syzran",
    "волгодонск": "volgodonsk",
    "новочеркасск": "novocherkassk",
    "каменск-уральский": "kamensk_uralskiy",
    "златоуст": "zlatoust",
    "уссурийск": "ussuriysk",
    "электросталь": "elektrostal",
    "альметьевск": "almetevsk",
    "салават": "salavat",
    "миасс": "miass",
    "находка": "nakhodka",
    "копейск": "kopeysk",
    "пятигорск": "pyatigorsk",
    "кисловодск": "kislovodsk",
    "ессентуки": "essentuki",
    "рубцовск": "rubtsovsk",
    "березники": "berezniky",
    "коломна": "kolomna",
    "майкоп": "maykop",
    "одинцово": "odintsovo",
    "красногорск": "krasnogorsk",
    "серпухов": "serpukhov",
    "орехово-зуево": "orekhovo_zuevo",
    "домодедово": "domodedovo",
    "щелково": "shchelkovo",
    "нижнекамск": "nizhnekamsk"
}

TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya', ' ': '_'
}

def transliterate_city(city: str) -> str:
    """Транслитерирует название любого неизвестного города для поиска в 2GIS."""
    clean = (city or "").strip().lower()
    res = []
    for char in clean:
        if char in TRANSLIT_MAP:
            res.append(TRANSLIT_MAP[char])
        elif char.isalnum() or char in ('_', '-'):
            res.append(char)
    slug = "".join(res).strip('_-')
    return slug or "moscow"

def get_city_slug(city: str) -> str:
    clean = (city or "").strip().lower()
    # 1. Поиск по словарю точных совпадений
    for key, slug in CITY_SLUGS.items():
        if key in clean:
            return slug
    # 2. Если город не найден в словаре - умная транслитерация (вместо сброса на Москву)
    return transliterate_city(clean)

def fetch_firm_details(city_slug: str, pid: str) -> Dict[str, Any]:
    """Запрашивает карточку компании для извлечения контактов и соцсетей."""
    url = f"https://2gis.ru/{city_slug}/firm/{pid}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": f"dg5_museum_accept=1; _2gis_city={city_slug}",
        "Referer": f"https://2gis.ru/{city_slug}/"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        matches = re.findall(r"JSON\.parse\('(.*?)'\);", html)
        for m in matches:
            if pid in m and 'contact_groups' in m:
                clean = m.replace(r"\'", "'").replace(r'\"', '"').replace(r'\\', '\\')
                obj = json.loads(clean)
                profiles = obj.get('data', {}).get('entity', {}).get('profile', {})
                if pid in profiles:
                    p = profiles[pid].get('data', {})
                    return {
                        'contact_groups': p.get('contact_groups') or [],
                        'links': p.get('links') or {},
                        'url': p.get('url') or '',
                        'booking': p.get('booking') or {},
                        'custom_button': p.get('custom_button') or {}
                    }
    except Exception:
        pass
    return {}

def extract_contacts(details: Dict[str, Any]) -> Dict[str, str]:
    """Извлекает телефон, сайт, telegram, whatsapp, vk из структуры контактов."""
    res = {
        "phone": "",
        "phone_type": "unknown",
        "website": "",
        "telegram": "",
        "whatsapp": "",
        "vk": "",
        "booking_url": ""
    }
    
    # 1. Прямой сайт из карточки
    raw_url = details.get('url') or ''
    if raw_url:
        res["website"] = clean_website(raw_url)
        
    # 2. Кнопка онлайн-записи
    booking = details.get('booking') or {}
    if booking.get('url'):
        res["booking_url"] = booking.get('url')
    custom_btn = details.get('custom_button') or {}
    if custom_btn.get('url'):
        btn_url = custom_btn.get('url', '')
        if 'yclients' in btn_url or 'dikidi' in btn_url:
            res["booking_url"] = btn_url
            
    # 3. Группы контактов
    groups = details.get('contact_groups') or []
    for g in groups:
        for c in g.get('contacts', []):
            ctype = c.get('type', '')
            val = c.get('value', '')
            text = c.get('text', '')
            url = c.get('url', '')
            
            # Телефон
            if ctype == 'phone' and not res["phone"]:
                norm_phone, p_type = format_phone(val or text)
                if norm_phone:
                    res["phone"] = norm_phone
                    res["phone_type"] = p_type
                    
            # Сайт
            elif ctype == 'website' and not res["website"]:
                res["website"] = clean_website(url or val or text)
                
            # Соцсети и мессенджеры
            elif 'telegram' in ctype or 't.me' in url or 't.me' in text:
                res["telegram"] = url or val or text
            elif 'whatsapp' in ctype or 'wa.me' in url:
                res["whatsapp"] = url or val or text
            elif 'vkontakte' in ctype or 'vk.com' in url or 'vk.com' in text:
                res["vk"] = url or val or text
                
    return res

def search_2gis(
    query: str,
    city: str = "Москва",
    max_pages: int = 2,
    skip_franchises: bool = True,
    progress_callback = None
) -> List[Dict[str, Any]]:
    """
    Основная функция поиска по 2GIS.
    Возвращает список нормализованных лидов.
    """
    city_slug = get_city_slug(city)
    encoded_query = urllib.parse.quote(query)
    parsed_leads = []
    seen_names = set()

    for page in range(1, max_pages + 1):
        if progress_callback:
            progress_callback(f"Загрузка страницы {page}/{max_pages} из 2GIS ({city})...")
            
        url = f"https://2gis.ru/{city_slug}/search/{encoded_query}/page/{page}"
        html = ""
        for attempt in range(2):
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": f"https://2gis.ru/{city_slug}/",
                "Cookie": f"dg5_museum_accept=1; _2gis_city={city_slug}"
            }
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    if html:
                        break
            except Exception:
                time.sleep(1)

        if not html:
            break

        profiles = {}
        # Поиск JSON-блоков в SSR коде
        matches = re.findall(r"JSON\.parse\('(.*?)'\);", html)
        for m in matches:
            if 'profile' in m and 'address_name' in m:
                clean = m.replace(r"\'", "'").replace(r'\"', '"').replace(r'\\', '\\')
                try:
                    obj = json.loads(clean)
                    p_dict = obj.get('data', {}).get('entity', {}).get('profile', {})
                    for pid, p_wrap in p_dict.items():
                        if pid not in profiles:
                            profiles[pid] = p_wrap
                except Exception:
                    pass

        if not profiles:
            break

        # Обработка каждой найденной фирмы
        for pid, p_wrap in profiles.items():
            data = p_wrap.get('data', {})
            raw_name = data.get('name') or ''
            clean_name = clean_company_name(raw_name)
            
            if not clean_name or clean_name.lower() in seen_names:
                continue
            seen_names.add(clean_name.lower())

            # Фильтрация франшиз
            is_franchise, brand = check_franchise(clean_name)
            if skip_franchises and is_franchise:
                continue

            address = data.get('address_name') or ''
            rating = data.get('reviews', {}).get('general_rating') or 0.0
            reviews_count = data.get('reviews', {}).get('general_review_count') or 0

            # Подгрузка контактов (карточка фирмы)
            if progress_callback:
                progress_callback(f"Сбор контактов: {clean_name[:25]}...")
                
            details = fetch_firm_details(city_slug, pid)
            contacts = extract_contacts(details)

            lead = {
                "pid": pid,
                "name": clean_name,
                "city": city.capitalize(),
                "address": address,
                "phone": contacts["phone"],
                "phone_type": contacts["phone_type"],
                "website": contacts["website"],
                "telegram": contacts["telegram"],
                "whatsapp": contacts["whatsapp"],
                "vk": contacts["vk"],
                "booking_url": contacts["booking_url"],
                "is_franchise": is_franchise,
                "franchise_brand": brand,
                "rating": rating,
                "reviews_count": reviews_count,
                "url_2gis": f"https://2gis.ru/{city_slug}/firm/{pid}"
            }
            parsed_leads.append(lead)
            time.sleep(random.uniform(0.4, 0.9))

        time.sleep(random.uniform(1.0, 1.8))

    return parsed_leads
