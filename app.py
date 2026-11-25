#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from core.parser import search_2gis, CITY_SLUGS
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

def interactive_mode():
    print_banner()

    # 1. Запрос города
    default_city = "Москва"
    city = Prompt.ask(
        "[bold white]Введите город[/bold white] (например: Москва, СПб, Казань, Краснодар)",
        default=default_city
    ).strip()

    # 2. Запрос ниши
    default_query = "барбершоп"
    query = Prompt.ask(
        "[bold white]Поисковый запрос[/bold white] (например: барбершоп, цветы, спа, стоматология)",
        default=default_query
    ).strip()

    # 3. Количество страниц
    pages_str = Prompt.ask(
        "[bold white]Сколько страниц собрать?[/bold white] (1 стр ≈ 15-20 фирм)",
        default="2",
        choices=["1", "2", "3", "4", "5"]
    )
    max_pages = int(pages_str)

    # 4. Пропускать франшизы
    skip_franchises = Confirm.ask(
        "[bold white]Отфильтровать сетевые франшизы?[/bold white] (TopGun, Додо и т.д.)",
        default=True
    )

    console.print()
    console.print(f"[bold green]🚀 Запускаем сбор:[/bold green] [cyan]{query}[/cyan] в [magenta]{city}[/magenta] ({max_pages} стр.)...")
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
            max_pages=max_pages,
            skip_franchises=skip_franchises,
            progress_callback=update_status
        )

    if not leads:
        console.print("[bold red]❌ Ничего не найдено или 2GIS ограничил выдачу. Попробуйте другой запрос/город.[/bold red]")
        return

    console.print()
    console.print(f"[bold green]✨ Успешно собрано:[/bold green] [bold white]{len(leads)}[/bold white] независимых компаний!\n")

    # Вывод таблицы с превью первых 10 лидов
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
    parser.add_argument("-p", "--pages", type=int, default=2, help="Количество страниц (по умолчанию: 2)")
    parser.add_argument("--allow-franchises", action="store_true", help="Не фильтровать сетевые франшизы")
    args = parser.parse_args()

    if args.query:
        # CLI режим с флагами
        print_banner()
        console.print(f"[cyan]Поиск:[/cyan] {args.query} в {args.city}...")
        leads = search_2gis(
            query=args.query,
            city=args.city,
            max_pages=args.pages,
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
        # Интерактивный TUI режим
        interactive_mode()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Сбор прерван пользователем.[/yellow]")
        sys.exit(0)
