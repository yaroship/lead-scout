#!/usr/bin/env python3
import sys
import os
import argparse
import difflib
import re
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
    "6": ("Ввести свою нишу вручную", "")
}

def print_banner():
    console.clear()
    console.print(BANNER)
    console.print(Panel(
        "[bold green]✔ Автономный парсинг без платных API ключей[/bold green]\n"
        "[bold yellow]✔ Умная фильтрация сетевых франшиз[/bold yellow]\n"
        "[bold magenta]✔ Детект мобильных телефонов под WhatsApp/Telegram[/bold magenta]\n"
        "[bold blue]✔ Авто-экспорт в Excel (.xlsx), JSON и HTML дашборд[/bold blue]",
        title="[bold white]О возможностях[/bold white]",
        border_style="cyan"
    ))
    console.print()

def ask_niche() -> str:
    """Шаг 1: Выбор ниши из списка или ручной ввод с валидацией."""
    console.print("[bold yellow]Шаг 1 из 4: Выберите сферу бизнеса[/bold yellow]")
    
    niche_table = Table(box=None, show_header=False, pad_edge=False)
    niche_table.add_column("Номер", style="bold cyan", width=4)
    niche_table.add_column("Название сферы", style="white")

    for key, (label, _) in PRESET_NICHES.items():
        niche_table.add_row(f"[{key}]", label)

    console.print(niche_table)
    console.print()

    choice = Prompt.ask(
        "[bold white]Выберите вариант [1-6][/bold white]",
        choices=list(PRESET_NICHES.keys()),
        default="1"
    )

    if choice != "6":
        selected_name, query = PRESET_NICHES[choice]
        console.print(f"[green]✔ Выбрано:[/green] [bold white]{selected_name}[/bold white]\n")
        return query

    # Ручной ввод ниши
    while True:
        custom_query = Prompt.ask(
            "[bold white]Введите сферу бизнеса[/bold white] (например: спа, автомойка, массаж)"
        ).strip()

        clean_lower = custom_query.lower()

        if not custom_query:
            console.print("[bold red]❌ Название ниши не может быть пустым. Попробуйте еще раз.[/bold red]")
            continue

        if clean_lower in STOP_WORDS or bool(re.match(r"^\d+$", clean_lower)):
            console.print(f"[bold red]❌ «{custom_query}» — некорректная сфера бизнеса. Введите реальную нишу (например: спа, тату, фитнес).[/bold red]")
            continue

        if len(clean_lower) < 2:
            console.print("[bold red]❌ Слишком короткое название. Введите минимум 2 символа (например: СПА).[/bold red]")
            continue

        console.print(f"[green]✔ Принято:[/green] [bold white]{custom_query}[/bold white]\n")
        return custom_query

def ask_city() -> str:
    """Шаг 2: Ввод города с проверкой по базе 2GIS и автоподсказками."""
    console.print("[bold yellow]Шаг 2 из 4: Укажите город[/bold yellow]")
    
    while True:
        raw_city = Prompt.ask(
            "[bold white]Введите город[/bold white] (например: Москва, СПб, Казань, Тюмень)",
            default="Москва"
        ).strip()

        clean_lower = raw_city.lower()

        if not raw_city:
            return "Москва"

        # 1. Проверка на очевидный мусор / стоп-слова / числа
        if clean_lower in STOP_WORDS or bool(re.match(r"^[\d\W]+$", clean_lower)):
            console.print(f"[bold red]❌ «{raw_city}» не является названием города. Введите реальный город.[/bold red]\n")
            continue

        # 2. Прямое совпадение в словаре
        if any(k in clean_lower for k in CITY_SLUGS.keys()):
            console.print(f"[green]✔ Город найден в базе 2GIS:[/green] [bold white]{raw_city.capitalize()}[/bold white]\n")
            return raw_city.capitalize()

        # 3. Нечеткий поиск (опечатки: Масква -> Москва, Питир -> Питер)
        matches = difflib.get_close_matches(clean_lower, CITY_SLUGS.keys(), n=1, cutoff=0.6)
        if matches:
            suggested = matches[0].capitalize()
            is_correct = Confirm.ask(
                f"[bold cyan]Город «{raw_city}» не найден. Возможно, вы имели в виду «{suggested}»?[/bold cyan]",
                default=True
            )
            if is_correct:
                console.print(f"[green]✔ Выбран город:[/green] [bold white]{suggested}[/bold white]\n")
                return suggested
            else:
                console.print("[dim]Попробуйте ввести название города еще раз.[/dim]\n")
                continue

        # 4. Если город редкий, но валидный (состоит из букв и дефисов, длина >= 3)
        if len(clean_lower) >= 3 and re.match(r"^[а-яa-z\- ]+$", clean_lower):
            slug = transliterate_city(clean_lower)
            confirm_search = Confirm.ask(
                f"[yellow]Город «{raw_city}» отсутствует в основном топ-списке. Попробовать поиск по коду «{slug}»?[/yellow]",
                default=True
            )
            if confirm_search:
                console.print(f"[green]✔ Принято:[/green] [bold white]{raw_city.capitalize()}[/bold white]\n")
                return raw_city.capitalize()
            else:
                continue

        console.print(f"[bold red]❌ Не удалось распознать город «{raw_city}». Пожалуйста, укажите существующий город РФ.[/bold red]\n")

def ask_target_leads() -> int:
    """Шаг 3: Запрос точного количества лидов (до 50)."""
    console.print("[bold yellow]Шаг 3 из 4: Объем сбора[/bold yellow]")
    
    while True:
        raw_val = Prompt.ask(
            "[bold white]Сколько лидов собрать?[/bold white] (от 5 до 50)",
            default="25"
        ).strip()

        try:
            val = int(raw_val)
            if 5 <= val <= 50:
                console.print(f"[green]✔ Цель:[/green] [bold white]{val} лидов[/bold white]\n")
                return val
            else:
                console.print("[bold red]❌ Введите число в диапазоне от 5 до 50 (например: 20 или 50).[/bold red]\n")
        except ValueError:
            console.print(f"[bold red]❌ «{raw_val}» — это не число. Укажите число от 5 до 50.[/bold red]\n")

def ask_skip_franchises() -> bool:
    """Шаг 4: Фильтрация франшиз."""
    console.print("[bold yellow]Шаг 4 из 4: Фильтрация сетей[/bold yellow]")
    skip = Confirm.ask(
        "[bold white]Отфильтровать сетевые франшизы?[/bold white] (TopGun, Додо, OldBoy и др.)",
        default=True
    )
    console.print()
    return skip

def interactive_mode():
    print_banner()

    # Пошаговый сценарий
    query = ask_niche()
    city = ask_city()
    target_count = ask_target_leads()
    skip_franchises = ask_skip_franchises()

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
            skip_franchises=skip_franchises,
            progress_callback=update_status
        )

    if not leads:
        console.print("[bold red]❌ Ничего не найдено или 2GIS ограничил выдачу. Попробуйте другой запрос/город.[/bold red]")
        return

    console.print()
    console.print(f"[bold green]✨ Успешно собрано:[/bold green] [bold white]{len(leads)}[/bold white] независимых компаний!\n")

    # Вывод таблицы с превью первых 12 лидов
    table = Table(title=f"🎯 Топ найденных лидов ({query} — {city})", border_style="cyan")
    table.add_column("№", style="dim", width=4)
    table.add_column("Название компании", style="bold white", min_width=20)
    table.add_column("Телефон", style="green", min_width=15)
    table.add_column("Тип", style="yellow")
    table.add_column("Сайт", style="blue")
    table.add_column("Мессенджеры", style="magenta")

    for i, l in enumerate(leads[:12], 1):
        messengers = []
        if l.get("telegram"): messengers.append("TG")
        if l.get("whatsapp"): messengers.append("WA")
        if l.get("vk"): messengers.append("VK")
        messengers_str = ", ".join(messengers) if messengers else "—"

        p_type = "📱 Моб" if l.get("phone_type") == "mobile" else "☎️ Гор" if l.get("phone_type") == "landline" else "—"
        table.add_row(
            str(i),
            l.get("name", "")[:28],
            l.get("phone") or "—",
            p_type,
            "Да" if l.get("website") else "—",
            messengers_str
        )

    console.print(table)
    if len(leads) > 12:
        console.print(f"[dim]... и еще {len(leads) - 12} компаний сохранены в файл.[/dim]\n")

    # Авто-экспорт
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

def main():
    parser = argparse.ArgumentParser(description="LeadScout CLI - Автономный экстрактор лидов 2GIS")
    parser.add_argument("-q", "--query", help="Поисковый запрос (например: барбершоп)")
    parser.add_argument("-c", "--city", default="Москва", help="Город поиска (по умолчанию: Москва)")
    parser.add_argument("-l", "--leads", type=int, default=25, help="Количество лидов до 50 (по умолчанию: 25)")
    parser.add_argument("--allow-franchises", action="store_true", help="Не фильтровать сетевые франшизы")
    args = parser.parse_args()

    if args.query:
        print_banner()
        target = min(max(args.leads, 5), 50)
        console.print(f"[cyan]Поиск:[/cyan] {args.query} в {args.city} (цель: {target} лидов)...")
        leads = search_2gis(
            query=args.query,
            city=args.city,
            target_count=target,
            skip_franchises=not args.allow_franchises
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
        interactive_mode()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Сбор прерван пользователем.[/yellow]")
        sys.exit(0)
