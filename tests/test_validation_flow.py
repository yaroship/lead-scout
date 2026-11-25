import sys
import os
import difflib
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.parser import CITY_SLUGS, transliterate_city
from app import STOP_WORDS

def test_niche_validator(val: str) -> bool:
    clean = val.strip().lower()
    if not clean:
        return False
    if clean in STOP_WORDS or bool(re.match(r"^\d+$", clean)):
        return False
    if len(clean) < 2:
        return False
    return True

def test_city_validator(raw_city: str):
    clean_lower = raw_city.strip().lower()
    if not clean_lower or clean_lower in STOP_WORDS or bool(re.match(r"^[\d\W]+$", clean_lower)):
        return "INVALID"
    if any(k in clean_lower for k in CITY_SLUGS.keys()):
        return "EXACT"
    matches = difflib.get_close_matches(clean_lower, CITY_SLUGS.keys(), n=1, cutoff=0.6)
    if matches:
        return f"SUGGEST:{matches[0]}"
    if len(clean_lower) >= 3 and re.match(r"^[а-яa-z\- ]+$", clean_lower):
        return f"TRANSLIT:{transliterate_city(clean_lower)}"
    return "INVALID"

def run_checks():
    print("Проверка валидатора ниш:")
    assert test_niche_validator("спа") == True, "Ниша 'спа' должна быть валидной!"
    assert test_niche_validator("сто") == True, "Ниша 'сто' должна быть валидной!"
    assert test_niche_validator("тату") == True, "Ниша 'тату' должна быть валидной!"
    assert test_niche_validator("привет") == False, "'привет' должен быть отклонен!"
    assert test_niche_validator("12345") == False, "'12345' должно быть отклонено!"
    assert test_niche_validator("а") == False, "'а' должна быть отклонена!"
    print("✔ Все проверки ниш пройдены!")

    print("\nПроверка валидатора городов:")
    assert test_city_validator("привет") == "INVALID", "'привет' должен быть INVALID!"
    assert test_city_validator("123") == "INVALID", "'123' должно быть INVALID!"
    assert test_city_validator("Казань") == "EXACT", "'Казань' должна быть EXACT!"
    assert test_city_validator("Масква").startswith("SUGGEST:"), "'Масква' должна дать SUGGEST!"
    assert test_city_validator("Питир").startswith("SUGGEST:"), "'Питир' должен дать SUGGEST!"
    assert test_city_validator("Иннополис").startswith("TRANSLIT:"), "'Иннополис' должен дать TRANSLIT!"
    print("✔ Все проверки городов пройдены!")

if __name__ == "__main__":
    run_checks()
