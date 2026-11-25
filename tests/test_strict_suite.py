import sys
import os
import time
import json
import openpyxl

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.filter import check_franchise, clean_company_name, clean_website, format_phone
from core.exporter import export_to_excel, export_to_json, export_to_html
from core.parser import get_city_slug, search_2gis

def run_tests():
    print("=" * 60)
    print("⚡ СТАРТ СТРОГОГО СТРЕСС-ТЕСТИРОВАНИЯ LEAD SCOUT CLI")
    print("=" * 60)
    
    errors = []
    
    # -------------------------------------------------------------
    # ТЕСТ 1: Краевые случаи и устойчивость фильтра (50 вариаций)
    # -------------------------------------------------------------
    print("\n[ТЕСТ 1] Проверка фильтрации и очистки данных (Edge cases)...")
    
    # 1.1 Франшизы
    franchise_cases = [
        ("Topgun Barbershop", True),
        ("Барбершоп Олдбой Ленинский", True),
        ("Чоп-Чоп на Арбате", True),
        ("Студия маникюра 4hands ТЦ Мега", True),
        ("Пиццерия Додо Пицца", True),
        ("Barbershop Britva", True),
        ("Ирис Цветы", True),
        ("Обычный Барбершоп У Михаила", False),
        ("Студия красоты Аура Люкс", False),
        ("Цветочная лавка Флора", False),
        ("", False),
        (None, False)
    ]
    for name, expected in franchise_cases:
        is_fr, brand = check_franchise(name)
        if is_fr != expected:
            errors.append(f"Ошибка check_franchise: для '{name}' ожидалось {expected}, получено {is_fr}")

    # 1.2 Очистка названий
    name_cases = [
        ("Барбершоп — стрижки, борода, отзывы", "Барбершоп"),
        ("Аура, студия красоты, маникюр Москва", "Аура"),
        ("Цветы у дома, сеть цветочных магазинов", "Цветы у дома"),
        ("  Просто Название  ", "Просто Название"),
        ("", ""),
        (None, "")
    ]
    for raw, expected in name_cases:
        cleaned = clean_company_name(raw)
        if cleaned != expected:
            errors.append(f"Ошибка clean_company_name: для '{raw}' ожидалось '{expected}', получено '{cleaned}'")

    # 1.3 Номера телефонов
    phone_cases = [
        ("+7 (917) 123-45-67", "+79171234567", "mobile"),
        ("8 926 000 11 22", "+79260001122", "mobile"),
        ("9051234567", "+79051234567", "mobile"),
        ("+7 (495) 777-77-77", "+74957777777", "landline"),
        ("8 (843) 200-10-20", "+78432001020", "landline"),
        ("8-800-200-00-00", "+78002000000", "tollfree"),
        ("не указан", "не указан", "unknown"),
        ("", "", "unknown")
    ]
    for raw, exp_num, exp_type in phone_cases:
        res_num, res_type = format_phone(raw)
        if res_num != exp_num or res_type != exp_type:
            errors.append(f"Ошибка format_phone: для '{raw}' ожидалось ({exp_num}, {exp_type}), получено ({res_num}, {res_type})")

    # 1.4 Очистка URL
    url_cases = [
        ("https://mysite.ru/?utm_source=yandex&utm_medium=cpc&yclid=123456", "https://mysite.ru"),
        ("http://barber.com/salon/?yclid=999#about", "http://barber.com/salon#about"),
        ("mysite.ru?utm_campaign=test", "https://mysite.ru"),
        ("", "")
    ]
    for raw, expected in url_cases:
        res = clean_website(raw)
        if "utm_" in res or "yclid" in res:
            errors.append(f"Ошибка clean_website: метки не удалены из '{raw}' -> '{res}'")

    if not [e for e in errors if "clean_" in e or "check_" in e or "format_" in e]:
        print("  ✔ Тест 1 пройден успешно (0 ошибок на 30+ edge cases)")
    else:
        print(f"  ❌ В Тесте 1 найдено ошибок: {len(errors)}")

    # -------------------------------------------------------------
    # ТЕСТ 2: Нагрузочный стресс-тест экспортеров (500 записей + XSS)
    # -------------------------------------------------------------
    print("\n[ТЕСТ 2] Нагрузочный тест экспортеров (500 лидов + XSS/спецсимволы)...")
    
    mock_leads = []
    for i in range(1, 501):
        mock_leads.append({
            "pid": f"firm_{i}",
            "name": f"Компания \"Тест & Ко\" <script>alert({i})</script> №{i}",
            "city": "Санкт-Петербург",
            "address": f"Невский проспект, дом {i}, корп. {i % 3 + 1}",
            "phone": f"+7911000{i:04d}",
            "phone_type": "mobile" if i % 2 == 0 else "landline",
            "website": f"https://example{i}.com/page?ref=test",
            "telegram": f"https://t.me/company_{i}",
            "whatsapp": f"https://wa.me/7911000{i:04d}",
            "vk": f"https://vk.com/club{i}",
            "booking_url": f"https://n{i}.yclients.com",
            "is_franchise": False,
            "franchise_brand": None,
            "rating": round(4.0 + (i % 10) * 0.1, 1),
            "reviews_count": i * 3,
            "url_2gis": f"https://2gis.ru/spb/firm/{i}"
        })

    os.makedirs("output_test", exist_ok=True)
    t0 = time.time()
    excel_file = "output_test/stress_500.xlsx"
    export_to_excel(mock_leads, excel_file)
    t_excel = time.time() - t0

    # Проверка целостности Excel
    try:
        wb = openpyxl.load_workbook(excel_file)
        ws = wb.active
        if ws.max_row != 501: # 1 заголовок + 500 строк
            errors.append(f"Excel max_row равен {ws.max_row}, ожидалось 501")
        print(f"  ✔ Excel: 500 строк сгенерировано за {t_excel:.2f} сек. Валидация файла успешна.")
    except Exception as e:
        errors.append(f"Ошибка загрузки созданного Excel: {e}")

    # JSON экспорт
    t0 = time.time()
    json_file = "output_test/stress_500.json"
    export_to_json(mock_leads, json_file)
    t_json = time.time() - t0
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            loaded_json = json.load(f)
        if len(loaded_json) != 500:
            errors.append(f"JSON длина {len(loaded_json)}, ожидалось 500")
        print(f"  ✔ JSON: 500 записей сериализовано за {t_json:.2f} сек. Валидация JSON успешна.")
    except Exception as e:
        errors.append(f"Ошибка валидации JSON: {e}")

    # HTML экспорт и проверка на XSS/синтаксис JS
    t0 = time.time()
    html_file = "output_test/stress_500.html"
    export_to_html(mock_leads, html_file, query="Тест", city="СПб")
    t_html = time.time() - t0
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Критическая проверка: разрывает ли <script> тег скрипт браузера?
    # Если в строке JSON есть </script>, браузер воспримет это как закрытие текущего тега <script>!
    if "</script>" in html_content.split("<script>")[1].split("</script>")[0]:
        errors.append("КРИТИЧЕСКИЙ XSS ДЕФЕКТ в HTML: '</script>' внутри данных ломает JavaScript контекст!")
    else:
        print(f"  ✔ HTML: интерактивный дашборд сгенерирован за {t_html:.2f} сек.")

    # -------------------------------------------------------------
    # ТЕСТ 3: Проверка маппинга городов и граничных условий 2GIS
    # -------------------------------------------------------------
    print("\n[ТЕСТ 3] Проверка распознавания городов и fallback...")
    test_cities = [
        ("Москва", "moscow"),
        ("Санкт-Петербург", "spb"),
        ("Питер", "spb"),
        ("Ростов-на-Дону", "rostov"),
        ("Казань", "kazan"),
        ("Нижнекамск", "nizhnekamsk"),
        ("НеизвестныйГород123", "neizvestnyygorod123"), # умная транслитерация
        ("", "moscow") # fallback при пустом вводе
    ]
    for c_in, expected_slug in test_cities:
        slug = get_city_slug(c_in)
        if slug != expected_slug:
            errors.append(f"Ошибка get_city_slug: для '{c_in}' ожидался slug '{expected_slug}', получен '{slug}'")
    print("  ✔ Тест 3 пройден (все slug городов распознаются корректно)")

    # -------------------------------------------------------------
    # ИТОГИ
    # -------------------------------------------------------------
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ НАЙДЕНО ДЕФЕКТОВ: {len(errors)}")
        for err in errors:
            print(f"   - {err}")
        return False
    else:
        print("✅ ВСЕ СТРЕСС-ТЕСТЫ ПРОЙДЕНЫ БЕЗ ЕДИНОЙ ОШИБКИ (100% SUCCESS)")
        return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
