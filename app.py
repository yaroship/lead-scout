#!/usr/bin/env python3
import sys
import os
import argparse
import difflib
import re
import subprocess
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from core.parser import search_2gis, CITY_SLUGS, transliterate_city
from core.exporter import export_to_excel, export_to_json, export_to_html

console = Console()

BANNER = r"""[bold cyan]
  _                     _  ____                  _   
 | |    ___  __ _  __| |/ ___|  ___ ___  _   _| |_ 
 | |   / _ \/ _` |/ _` |\___ \ / __/ _ \| | | | __|
 | |__|  __/ (_| | (_| | ___) | (_| (_) | |_| | |_ 
 |_____\___|\__,_|\__,_||____/ \___\___/ \__,_|\__|
[/bold cyan]
[dim]🔥 Autonomous B2B Lead Extractor for 2GIS | Open-Source Edition[/dim]
"""

STOP_WORDS = {
    "привет", "пока", "hello", "hi", "test", "тест", "йцукен",
    "asdf", "qwer", "123", "1234", "стоп", "stop", "проверка"
}

PRESET_NICHES = {
    "1": ("Барбершопы и мужские стрижки", "барбершоп"),
    "2": ("Салоны красоты и маникюр", "салон красоты"),
    "3": ("Цветы и флористика", "цветы"),
    "4": ("Стоматологии и клиники", "стоматология"),
    "5": ("Автосервисы и детейлинг", "детейлинг"),
    "6": ("СПА и массажные салоны", "спа"),
    "7": ("Ввести свою нишу вручную", "")
}

TOP_CITIES = {
    "1": ("Москва", "Москва"),
    "2": ("Санкт-Петербург", "Санкт-Петербург"),
    "3": ("Казань", "Казань"),
    "4": ("Екатеринбург", "Екатеринбург"),
    "5": ("Краснодар", "Краснодар"),
    "6": ("Ввести другой город вручную", "")
}

# Текущее состояние настроек фильтрации
CURRENT_FILTERS = {
    "skip_franchises": True,     # Исключать сетевые бренды (Додо, TopGun и т.д.)
    "only_mobile": False,         # Только мобильные телефоны под WhatsApp/Telegram
    "require_website": False,     # Только компании с сайтом
    "require_messenger": False,   # Только компании с Telegram или WhatsApp
    "min_rating": 0.0             # Минимальный рейтинг компании
}

def print_banner():
    console.clear()
    console.print(BANNER)

# ==============================================================================
# РАЗДЕЛ 1: СБОР ЛИДОВ (ПОШАГОВЫЙ СЦЕНАРИЙ)
# ==============================================================================

def ask_niche() -> str:
    """Шаг 1: Выбор ниши цифрой или ручной ввод."""
    console.print("\n[bold yellow]Шаг 1 из 3: Выберите сферу бизнеса[/bold yellow]")
    
    niche_table = Table(box=None, show_header=False, pad_edge=False)
    niche_table.add_column("Номер", style="bold cyan", width=4)
    niche_table.add_column("Название сферы", style="white")

    for key, (label, _) in PRESET_NICHES.items():
        niche_table.add_row(f"[{key}]", label)

    console.print(niche_table)
    console.print()

    choice = Prompt.ask(
        "[bold white]Выберите вариант [1-7][/bold white]",
        choices=list(PRESET_NICHES.keys()),
        default="1"
    )

    if choice != "7":
        selected_name, query = PRESET_NICHES[choice]
        console.print(f"[green]✔ Выбрано:[/green] [bold white]{selected_name}[/bold white]\n")
        return query

    # Ручной ввод ниши
    while True:
        custom_query = Prompt.ask(
            "[bold white]Введите сферу бизнеса[/bold white] (например: спа, тату, автомойка)"
        ).strip()

        clean_lower = custom_query.lower()

        if not custom_query:
            console.print("[bold red]❌ Название ниши не может быть пустым.[/bold red]")
            continue

        if clean_lower in STOP_WORDS or bool(re.match(r"^\d+$", clean_lower)):
            console.print(f"[bold red]❌ «{custom_query}» — некорректный запрос. Укажите реальную сферу.[/bold red]")
            continue

        if len(clean_lower) < 2:
            console.print("[bold red]❌ Слишком коротко. Введите минимум 2 символа (например: СПА).[/bold red]")
            continue

        console.print(f"[green]✔ Принято:[/green] [bold white]{custom_query}[/bold white]\n")
        return custom_query

def ask_city() -> str:
    """Шаг 2: Выбор города цифрой или ручной ввод."""
    console.print("[bold yellow]Шаг 2 из 3: Выберите город[/bold yellow]")
    
    city_table = Table(box=None, show_header=False, pad_edge=False)
    city_table.add_column("Номер", style="bold cyan", width=4)
    city_table.add_column("Город", style="white")

    for key, (label, _) in TOP_CITIES.items():
        city_table.add_row(f"[{key}]", label)

    console.print(city_table)
    console.print()

    choice = Prompt.ask(
        "[bold white]Выберите вариант [1-6][/bold white]",
        choices=list(TOP_CITIES.keys()),
        default="1"
    )

    if choice != "6":
        selected_city, _ = TOP_CITIES[choice]
        console.print(f"[green]✔ Город:[/green] [bold white]{selected_city}[/bold white]\n")
        return selected_city

    # Ручной ввод города
    while True:
        raw_city = Prompt.ask(
            "[bold white]Введите название города[/bold white] (например: Тюмень, Сочи, Нижнекамск)"
        ).strip()

        clean_lower = raw_city.lower()

        if not raw_city:
            return "Москва"

        if clean_lower in STOP_WORDS or bool(re.match(r"^[\d\W]+$", clean_lower)):
            console.print(f"[bold red]❌ «{raw_city}» — некорректное имя города.[/bold red]\n")
            continue

        if any(k in clean_lower for k in CITY_SLUGS.keys()):
            console.print(f"[green]✔ Город найден в базе 2GIS:[/green] [bold white]{raw_city.capitalize()}[/bold white]\n")
            return raw_city.capitalize()

        matches = difflib.get_close_matches(clean_lower, CITY_SLUGS.keys(), n=1, cutoff=0.6)
        if matches:
            suggested = matches[0].capitalize()
            if Confirm.ask(f"[bold cyan]Город «{raw_city}» не найден. Имели в виду «{suggested}»?[/bold cyan]", default=True):
                return suggested
            continue

        if len(clean_lower) >= 3 and re.match(r"^[а-яa-z\- ]+$", clean_lower):
            slug = transliterate_city(clean_lower)
            if Confirm.ask(f"[yellow]Город «{raw_city}» отсутствует в топ-списке. Искать по коду «{slug}»?[/yellow]", default=True):
                return raw_city.capitalize()
            continue

        console.print(f"[bold red]❌ Не удалось распознать город «{raw_city}». Попробуйте еще раз.[/bold red]\n")

def ask_target_leads() -> int:
    """Шаг 3: Выбор количества лидов."""
    console.print("[bold yellow]Шаг 3 из 3: Количество лидов[/bold yellow]")
    
    qty_table = Table(box=None, show_header=False, pad_edge=False)
    qty_table.add_column("Номер", style="bold cyan", width=4)
    qty_table.add_column("Объем", style="white")

    options = {
        "1": ("10 лидов (быстрый сбор)", 10),
        "2": ("25 лидов (рекомендуется)", 25),
        "3": ("50 лидов (максимальный пул)", 50),
        "4": ("Ввести точное число вручную", 0)
    }

    for key, (label, _) in options.items():
        qty_table.add_row(f"[{key}]", label)

    console.print(qty_table)
    console.print()

    choice = Prompt.ask("[bold white]Выберите вариант [1-4][/bold white]", choices=list(options.keys()), default="2")

    if choice != "4":
        val = options[choice][1]
        console.print(f"[green]✔ Цель:[/green] [bold white]{val} лидов[/bold white]\n")
        return val

    while True:
        raw_val = Prompt.ask("[bold white]Сколько лидов собрать?[/bold white] (от 5 до 50)", default="25").strip()
        try:
            val = int(raw_val)
            if 5 <= val <= 50:
                console.print(f"[green]✔ Цель:[/green] [bold white]{val} лидов[/bold white]\n")
                return val
            console.print("[bold red]❌ Число должно быть от 5 до 50.[/bold red]\n")
        except ValueError:
            console.print(f"[bold red]❌ «{raw_val}» — это не число.[/bold red]\n")

def run_parsing_flow():
    """Запуск сбора лидов."""
    print_banner()

    # Сводка активных фильтров
    active_badges = []
    if CURRENT_FILTERS["skip_franchises"]: active_badges.append("[green]✔ Без сетей[/green]")
    if CURRENT_FILTERS["only_mobile"]: active_badges.append("[magenta]✔ Только моб (+7 9xx)[/magenta]")
    if CURRENT_FILTERS["require_website"]: active_badges.append("[blue]✔ Только с сайтом[/blue]")
    if CURRENT_FILTERS["require_messenger"]: active_badges.append("[cyan]✔ Только с TG/WA[/cyan]")
    if CURRENT_FILTERS["min_rating"] > 0: active_badges.append(f"[yellow]✔ Рейтинг от {CURRENT_FILTERS['min_rating']}+[/yellow]")
    if not active_badges: active_badges.append("[dim]Стандартные фильтры[/dim]")

    console.print(Panel(
        " • ".join(active_badges),
        title="[bold white]Активные фильтры (настраиваются в меню [2])[/bold white]",
        border_style="cyan"
    ))

    query = ask_niche()
    city = ask_city()
    target_count = ask_target_leads()

    console.print(f"[bold green]🚀 Запускаем сбор:[/bold green] [cyan]{query}[/cyan] в [magenta]{city}[/magenta] (цель: [bold white]{target_count}[/bold white] лидов)...")
    console.print()

    leads = []
    with Progress(
        SpinnerColumn(style="bold cyan"),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        task = progress.add_task("[cyan]Подключение к 2GIS...", total=None)

        def update_status(text: str):
            progress.update(task, description=f"[cyan]{text}")

        leads = search_2gis(
            query=query,
            city=city,
            target_count=target_count,
            skip_franchises=CURRENT_FILTERS["skip_franchises"],
            only_mobile=CURRENT_FILTERS["only_mobile"],
            require_website=CURRENT_FILTERS["require_website"],
            require_messenger=CURRENT_FILTERS["require_messenger"],
            min_rating=CURRENT_FILTERS["min_rating"],
            progress_callback=update_status
        )

    if not leads:
        console.print("[bold red]❌ Ничего не найдено или компании не прошли строгие фильтры. Попробуйте ослабить настройки фильтра или изменить запрос.[/bold red]")
        Prompt.ask("\nНажмите Enter, чтобы вернуться в главное меню")
        return

    console.print()
    console.print(f"[bold green]✨ Успешно собрано:[/bold green] [bold white]{len(leads)}[/bold white] компаний, прошедших все фильтры!\n")

    # ВЫВОД ВСЕЙ БАЗЫ ЦЕЛИКОМ В ТЕРМИНАЛ
    table = Table(title=f"🎯 Полная база найденных лидов ({query} — {city} | {len(leads)} шт.)", border_style="cyan")
    table.add_column("№", style="dim", width=4)
    table.add_column("Название компании", style="bold white", min_width=20)
    table.add_column("Телефон", style="green", min_width=15)
    table.add_column("Тип", style="yellow", width=8)
    table.add_column("Сайт", style="blue")
    table.add_column("Мессенджеры", style="magenta")
    table.add_column("Рейтинг", style="yellow", width=7)

    for i, l in enumerate(leads, 1):
        messengers = []
        if l.get("telegram"): messengers.append("TG")
        if l.get("whatsapp"): messengers.append("WA")
        if l.get("vk"): messengers.append("VK")
        messengers_str = ", ".join(messengers) if messengers else "—"

        p_type = "📱 Моб" if l.get("phone_type") == "mobile" else "☎️ Гор" if l.get("phone_type") == "landline" else "—"
        r_str = f"⭐ {l.get('rating')}" if l.get('rating') else "—"

        table.add_row(
            str(i),
            l.get("name", "")[:28],
            l.get("phone") or "—",
            p_type,
            "Да" if l.get("website") else "—",
            messengers_str,
            r_str
        )

    console.print(table)
    console.print()

    # Сохранение файлов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    clean_q = "".join(c for c in query if c.isalnum() or c in (" ", "_")).replace(" ", "_")
    base_name = f"leads_{clean_q}_{timestamp}"

    os.makedirs("output", exist_ok=True)
    excel_path = os.path.join("output", f"{base_name}.xlsx")
    html_path = os.path.join("output", f"{base_name}.html")
    json_path = os.path.join("output", f"{base_name}.json")

    export_to_excel(leads, excel_path)
    export_to_html(leads, html_path, query=query, city=city)
    export_to_json(leads, json_path)

    console.print(Panel(
        f"[bold green]✔ Excel таблица:[/bold green] [cyan]{excel_path}[/cyan]\n"
        f"[bold green]✔ Интерактивный дашборд:[/bold green] [cyan]{html_path}[/cyan]\n"
        f"[bold green]✔ JSON база:[/bold green] [cyan]{json_path}[/cyan]",
        title="[bold white]Результаты сохранены в папку /output[/bold white]",
        border_style="green"
    ))

    # Быстрые действия после сбора
    console.print("[bold yellow]Что сделать дальше?[/bold yellow]")
    console.print(" [1] 🌐 Открыть интерактивный HTML-дашборд в браузере")
    console.print(" [2] 🔄 Сделать новый поиск")
    console.print(" [0] 🔙 Вернуться в главное меню\n")

    after_choice = Prompt.ask("Выберите действие [0-2]", choices=["0", "1", "2"], default="1")
    if after_choice == "1":
        try:
            subprocess.run(["open", html_path], check=False)
            console.print("[green]✔ Дашборд открыт в браузере![/green]")
        except Exception:
            pass
        Prompt.ask("\nНажмите Enter, чтобы вернуться в меню")
    elif after_choice == "2":
        run_parsing_flow()

# ==============================================================================
# РАЗДЕЛ 2: НАСТРОЙКИ ФИЛЬТРАЦИИ (ОТДЕЛЬНЫЕ ОКНА ДЛЯ КАЖДОГО ПАРАМЕТРА)
# ==============================================================================

def edit_filter_franchise():
    """Окно настройки 1: Фильтр франшиз."""
    print_banner()
    console.print(Panel(
        "[bold white]Параметр: Фильтрация сетевых франшиз[/bold white]\n\n"
        "Позволяет отсекать крупные сети (Додо, TopGun, OldBoy, 4hands и др.),\n"
        "оставляя только частных владельцев бизнеса (быстрее принимают решения).",
        border_style="cyan"
    ))
    curr = "ВКЛ (исключать сети)" if CURRENT_FILTERS["skip_franchises"] else "ВЫКЛ (брать всё)"
    console.print(f"Текущее значение: [bold green]{curr}[/bold green]\n")
    console.print(" [1] 🛡️ [bold green]ВКЛЮЧИТЬ[/bold green] — исключать сетевые франшизы")
    console.print(" [2] 🌐 [bold yellow]ВЫКЛЮЧИТЬ[/bold yellow] — собирать все компании подряд")
    console.print(" [0] 🔙 Назад в меню фильтров\n")

    c = Prompt.ask("Выберите [0-2]", choices=["0", "1", "2"], default="1")
    if c == "1":
        CURRENT_FILTERS["skip_franchises"] = True
        console.print("[green]✔ Фильтр франшиз включен![/green]")
    elif c == "2":
        CURRENT_FILTERS["skip_franchises"] = False
        console.print("[yellow]✔ Фильтр франшиз выключен (будут собираться и сети).[/yellow]")

def edit_filter_phones():
    """Окно настройки 2: Тип телефона."""
    print_banner()
    console.print(Panel(
        "[bold white]Параметр: Тип телефонных номеров[/bold white]\n\n"
        "Позволяет оставлять в базе ТОЛЬКО мобильные номера (+7 9xx...).\n"
        "Идеально для прямых рассылок и сообщений в WhatsApp и Telegram.",
        border_style="cyan"
    ))
    curr = "ВКЛ (только мобильные)" if CURRENT_FILTERS["only_mobile"] else "ВЫКЛ (все номера)"
    console.print(f"Текущее значение: [bold green]{curr}[/bold green]\n")
    console.print(" [1] 📱 [bold green]ВКЛЮЧИТЬ[/bold green] — только мобильные телефоны (+7 9xx...)")
    console.print(" [2] ☎️ [bold yellow]ВЫКЛЮЧИТЬ[/bold yellow] — любые номера (городские, 8-800 и др.)")
    console.print(" [0] 🔙 Назад в меню фильтров\n")

    c = Prompt.ask("Выберите [0-2]", choices=["0", "1", "2"], default="1")
    if c == "1":
        CURRENT_FILTERS["only_mobile"] = True
        console.print("[green]✔ Режим «Только мобильные» включен![/green]")
    elif c == "2":
        CURRENT_FILTERS["only_mobile"] = False
        console.print("[yellow]✔ Включены все типы номеров.[/yellow]")

def edit_filter_website():
    """Окно настройки 3: Наличие сайта."""
    print_banner()
    console.print(Panel(
        "[bold white]Параметр: Обязательное наличие сайта[/bold white]\n\n"
        "Отсекает компании, у которых нет своего действующего сайта.\n"
        "Полезно для анализа уровня диджитализации компании.",
        border_style="cyan"
    ))
    curr = "ВКЛ (только с сайтом)" if CURRENT_FILTERS["require_website"] else "ВЫКЛ (не важно)"
    console.print(f"Текущее значение: [bold green]{curr}[/bold green]\n")
    console.print(" [1] 🌐 [bold green]ВКЛЮЧИТЬ[/bold green] — только компании с сайтом")
    console.print(" [2] ⚪ [bold yellow]ВЫКЛЮЧИТЬ[/bold yellow] — собирать даже без сайта")
    console.print(" [0] 🔙 Назад в меню фильтров\n")

    c = Prompt.ask("Выберите [0-2]", choices=["0", "1", "2"], default="1")
    if c == "1":
        CURRENT_FILTERS["require_website"] = True
        console.print("[green]✔ Фильтр сайта включен![/green]")
    elif c == "2":
        CURRENT_FILTERS["require_website"] = False
        console.print("[yellow]✔ Будут собираться компании и без сайта.[/yellow]")

def edit_filter_messengers():
    """Окно настройки 4: Наличие Telegram/WhatsApp."""
    print_banner()
    console.print(Panel(
        "[bold white]Параметр: Обязательное наличие мессенджера[/bold white]\n\n"
        "Оставляет только компании, у которых в 2GIS указана прямая ссылка\n"
        "на канал/чат в Telegram или контакт в WhatsApp.",
        border_style="cyan"
    ))
    curr = "ВКЛ (только с TG/WA)" if CURRENT_FILTERS["require_messenger"] else "ВЫКЛ (не важно)"
    console.print(f"Текущее значение: [bold green]{curr}[/bold green]\n")
    console.print(" [1] 💬 [bold green]ВКЛЮЧИТЬ[/bold green] — только при наличии Telegram или WhatsApp")
    console.print(" [2] ⚪ [bold yellow]ВЫКЛЮЧИТЬ[/bold yellow] — собирать независимо от мессенджеров")
    console.print(" [0] 🔙 Назад в меню фильтров\n")

    c = Prompt.ask("Выберите [0-2]", choices=["0", "1", "2"], default="1")
    if c == "1":
        CURRENT_FILTERS["require_messenger"] = True
        console.print("[green]✔ Фильтр мессенджеров включен![/green]")
    elif c == "2":
        CURRENT_FILTERS["require_messenger"] = False
        console.print("[yellow]✔ Фильтр мессенджеров выключен.[/yellow]")

def edit_filter_rating():
    """Окно настройки 5: Минимальный рейтинг."""
    print_banner()
    console.print(Panel(
        "[bold white]Параметр: Минимальный рейтинг в 2GIS[/bold white]\n\n"
        "Позволяет отсекать компании с плохими отзывами клиентов.",
        border_style="cyan"
    ))
    curr = f"от {CURRENT_FILTERS['min_rating']}+" if CURRENT_FILTERS["min_rating"] > 0 else "Без ограничений"
    console.print(f"Текущее значение: [bold green]{curr}[/bold green]\n")
    console.print(" [1] ⚪ Без ограничений (любой рейтинг)")
    console.print(" [2] ⭐ Только высокий рейтинг (4.0+)")
    console.print(" [3] ⭐⭐ Премиум рейтинг (4.5+)")
    console.print(" [0] 🔙 Назад в меню фильтров\n")

    c = Prompt.ask("Выберите [0-3]", choices=["0", "1", "2", "3"], default="1")
    if c == "1":
        CURRENT_FILTERS["min_rating"] = 0.0
        console.print("[green]✔ Ограничение рейтинга снято.[/green]")
    elif c == "2":
        CURRENT_FILTERS["min_rating"] = 4.0
        console.print("[green]✔ Установлен порог: 4.0+[/green]")
    elif c == "3":
        CURRENT_FILTERS["min_rating"] = 4.5
        console.print("[green]✔ Установлен порог: 4.5+[/green]")

def filters_menu():
    """Главный экран настроек фильтров."""
    while True:
        print_banner()

        t = Table(title="⚙️ Настройки фильтрации поиска", border_style="cyan")
        t.add_column("№", style="bold cyan", width=4)
        t.add_column("Параметр фильтра", style="white", min_width=30)
        t.add_column("Текущий статус", style="bold", width=25)

        t.add_row(
            "[1]",
            "Исключать сетевые франшизы (Додо, TopGun...)",
            "[bold green]ВКЛ (только частники)[/bold green]" if CURRENT_FILTERS["skip_franchises"] else "[dim]ВЫКЛ (все сети)[/dim]"
        )
        t.add_row(
            "[2]",
            "Только мобильные телефоны (+7 9xx...)",
            "[bold green]ВКЛ (под TG/WA)[/bold green]" if CURRENT_FILTERS["only_mobile"] else "[dim]ВЫКЛ (включая город)[/dim]"
        )
        t.add_row(
            "[3]",
            "Обязательное наличие сайта",
            "[bold green]ВКЛ (только с сайтом)[/bold green]" if CURRENT_FILTERS["require_website"] else "[dim]ВЫКЛ (не важно)[/dim]"
        )
        t.add_row(
            "[4]",
            "Обязательное наличие мессенджера (TG/WA)",
            "[bold green]ВКЛ (только с чатом)[/bold green]" if CURRENT_FILTERS["require_messenger"] else "[dim]ВЫКЛ (не важно)[/dim]"
        )
        t.add_row(
            "[5]",
            "Минимальный рейтинг в 2GIS",
            f"[bold green]от {CURRENT_FILTERS['min_rating']}+[/bold green]" if CURRENT_FILTERS["min_rating"] > 0 else "[dim]Любой рейтинг[/dim]"
        )

        console.print(t)
        console.print()
        console.print("[bold yellow]Выберите пункт для настройки:[/bold yellow]")
        console.print(" [1-5] Переключить параметр в отдельном окне")
        console.print(" [9]   🚀 [bold green]Перейти к парсингу с этими фильтрами[/bold green]")
        console.print(" [0]   🔙 Назад в главное меню\n")

        choice = Prompt.ask("Ваш выбор", choices=["0", "1", "2", "3", "4", "5", "9"], default="9")

        if choice == "1": edit_filter_franchise()
        elif choice == "2": edit_filter_phones()
        elif choice == "3": edit_filter_website()
        elif choice == "4": edit_filter_messengers()
        elif choice == "5": edit_filter_rating()
        elif choice == "9":
            run_parsing_flow()
            break
        elif choice == "0":
            break

# ==============================================================================
# РАЗДЕЛ 3: ПОДКЛЮЧЕНИЕ К ИИ-АГЕНТУ
# ==============================================================================

def ai_integration_menu():
    """Меню подключения к ИИ-агенту."""
    print_banner()

    console.print(Panel(
        "[bold white]🤖 Как подключить LeadScout CLI к ИИ-агенту[/bold white]\n\n"
        "LeadScout CLI изначально спроектирован для работы в связке с нейросетями\n"
        "(ChatGPT, Claude, Gemini, Cursor или Antigravity).\n\n"
        "[bold cyan]1. Прямой импорт в Python код:[/bold cyan]\n"
        "```python\n"
        "from core.parser import search_2gis\n\n"
        "leads = search_2gis(\n"
        "    query='барбершоп', city='Москва', target_count=20,\n"
        "    only_mobile=True, skip_franchises=True\n"
        ")\n"
        "```\n\n"
        "[bold cyan]2. Готовый системный промпт:[/bold cyan]\n"
        "В корне проекта лежит файл [bold green]ai_agent_prompt.txt[/bold green].\n"
        "Скопируйте его содержимое и вставьте в чат вашему ИИ-агенту.\n"
        "ИИ поймет структуру собранных лидов и сам напишет персонализированные\n"
        "сообщения каждому директору без шаблонов и спама.",
        border_style="magenta"
    ))

    console.print("[bold yellow]Действия:[/bold yellow]")
    console.print(" [1] 📋 Показать системный промпт на экране")
    console.print(" [2] 🚀 Перейти к сбору лидов")
    console.print(" [0] 🔙 Главное меню\n")

    c = Prompt.ask("Выберите вариант [0-2]", choices=["0", "1", "2"], default="1")
    if c == "1":
        prompt_path = os.path.join(os.path.dirname(__file__), "ai_agent_prompt.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
            console.print("\n" + "=" * 60)
            console.print(content)
            console.print("=" * 60 + "\n")
        else:
            console.print("[red]Файл ai_agent_prompt.txt не найден.[/red]")
        Prompt.ask("Нажмите Enter для возврата в меню")
    elif c == "2":
        run_parsing_flow()

# ==============================================================================
# ТОЧКА ВХОДА (ГЛАВНОЕ МЕНЮ)
# ==============================================================================

def main_menu():
    """Главный экран программы."""
    while True:
        print_banner()

        menu_table = Table(box=None, show_header=False, pad_edge=False)
        menu_table.add_column("Кнопка", style="bold cyan", width=5)
        menu_table.add_column("Действие", style="white")

        menu_table.add_row("[1]", "🚀 [bold white]Запустить парсинг лидов[/bold white] (сбор контактов 2GIS)")
        menu_table.add_row("[2]", "⚙️ [bold white]Настройки фильтрации[/bold white] (сети, мобильные, сайты, рейтинг)")
        menu_table.add_row("[3]", "🤖 [bold white]Как подключить к ИИ-агенту[/bold white] (промпт и интеграция)")
        menu_table.add_row("[0]", "🚪 [dim]Выход из программы[/dim]")

        console.print(Panel(menu_table, title="[bold white]Главное меню[/bold white]", border_style="cyan"))
        console.print()

        choice = Prompt.ask("[bold white]Выберите пункт [0-3][/bold white]", choices=["0", "1", "2", "3"], default="1")

        if choice == "1":
            run_parsing_flow()
        elif choice == "2":
            filters_menu()
        elif choice == "3":
            ai_integration_menu()
        elif choice == "0":
            console.print("[yellow]До встречи![/yellow]")
            sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="LeadScout CLI - Автономный экстрактор лидов 2GIS")
    parser.add_argument("-q", "--query", help="Поисковый запрос")
    parser.add_argument("-c", "--city", default="Москва", help="Город")
    parser.add_argument("-l", "--leads", type=int, default=25, help="Количество лидов")
    parser.add_argument("--only-mobile", action="store_true", help="Только мобильные")
    parser.add_argument("--allow-franchises", action="store_true", help="Включать франшизы")
    args = parser.parse_args()

    if args.query:
        print_banner()
        target = min(max(args.leads, 5), 50)
        console.print(f"[cyan]Поиск:[/cyan] {args.query} в {args.city} (цель: {target} лидов)...")
        leads = search_2gis(
            query=args.query,
            city=args.city,
            target_count=target,
            skip_franchises=not args.allow_franchises,
            only_mobile=args.only_mobile
        )
        if leads:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            os.makedirs("output", exist_ok=True)
            excel_path = os.path.join("output", f"leads_{args.city}_{timestamp}.xlsx")
            export_to_excel(leads, excel_path)
            console.print(f"[bold green]✔ Сохранено {len(leads)} лидов в {excel_path}[/bold green]")
        else:
            console.print("[red]Лиды не найдены.[/red]")
    else:
        main_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Сбор прерван пользователем.[/yellow]")
        sys.exit(0)
