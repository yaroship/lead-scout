import json
import os
from typing import List, Dict, Any
from datetime import datetime

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

def export_to_excel(leads: List[Dict[str, Any]], filepath: str) -> str:
    """Экспортирует лиды в красиво оформленный Excel (.xlsx)."""
    if not HAS_OPENPYXL:
        raise ImportError("Библиотека openpyxl не установлена. Установите: pip install openpyxl")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Найденные лиды"

    # Стили
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    headers = [
        "№", "Название", "Город", "Адрес", "Телефон",
        "Тип номера", "Сайт", "Telegram", "WhatsApp",
        "VK", "Онлайн-запись", "Рейтинг", "Отзывов", "Ссылка 2GIS"
    ]

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align

    for idx, lead in enumerate(leads, 1):
        row_data = [
            idx,
            lead.get("name", ""),
            lead.get("city", ""),
            lead.get("address", ""),
            lead.get("phone", ""),
            "Мобильный (мессенджеры)" if lead.get("phone_type") == "mobile" else "Городской" if lead.get("phone_type") == "landline" else lead.get("phone_type", ""),
            lead.get("website", ""),
            lead.get("telegram", ""),
            lead.get("whatsapp", ""),
            lead.get("vk", ""),
            lead.get("booking_url", ""),
            lead.get("rating", 0.0),
            lead.get("reviews_count", 0),
            lead.get("url_2gis", "")
        ]
        ws.append(row_data)
        current_row = idx + 1
        for col_idx in range(1, len(row_data) + 1):
            c = ws.cell(row=current_row, column=col_idx)
            c.font = data_font
            c.border = thin_border
            if col_idx in (1, 3, 6, 12, 13):
                c.alignment = center_align
            else:
                c.alignment = left_align

    # Автоматическая ширина колонок
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 45)

    wb.save(filepath)
    return filepath

def export_to_json(leads: List[Dict[str, Any]], filepath: str) -> str:
    """Экспортирует лиды в формат JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    return filepath

def export_to_html(leads: List[Dict[str, Any]], filepath: str, query: str = "", city: str = "") -> str:
    """Генерирует автономный интерактивный HTML-дашборд с поиском и бейджами."""
    leads_json = json.dumps(leads, ensure_ascii=False)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LeadScout: {query} ({city})</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --border: #334155;
            --primary: #38bdf8;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .title {{
            font-size: 22px;
            font-weight: 700;
            color: var(--primary);
        }}
        .meta {{
            color: var(--text-dim);
            font-size: 14px;
        }}
        .search-box {{
            width: 100%;
            max-width: 400px;
            padding: 10px 14px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
            margin-bottom: 16px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }}
        th {{
            background: #1e293b;
            color: var(--text-dim);
            font-weight: 600;
        }}
        tr:hover td {{
            background: #24324a;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-mobile {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .badge-landline {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        a {{
            color: var(--primary);
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="title">🎯 LeadScout Dashboard</div>
            <div class="meta">Запрос: <b>{query}</b> | Город: <b>{city}</b> | Найдено: <b>{len(leads)} компаний</b></div>
        </div>
        <div class="meta">Собрано: {datetime.now().strftime('%d.%m.%Y %H:%M')}</div>
    </div>

    <input type="text" id="searchInput" class="search-box" placeholder="🔍 Быстрый поиск по таблице..." onkeyup="filterTable()">

    <table id="leadsTable">
        <thead>
            <tr>
                <th>№</th>
                <th>Компания</th>
                <th>Телефон</th>
                <th>Тип</th>
                <th>Сайт / Ссылка</th>
                <th>Мессенджеры</th>
                <th>Адрес</th>
            </tr>
        </thead>
        <tbody id="tableBody"></tbody>
    </table>

    <script>
        const leads = {leads_json};
        const tbody = document.getElementById("tableBody");

        function renderRows(items) {{
            tbody.innerHTML = items.map((l, i) => `
                <tr>
                    <td>${{i + 1}}</td>
                    <td><b>${{l.name}}</b><br><small style="color: #94a3b8">⭐ ${{l.rating}} (${{l.reviews_count}} отзывов)</small></td>
                    <td>${{l.phone || '—'}}</td>
                    <td>
                        ${{l.phone_type === 'mobile' ? '<span class="badge badge-mobile">📱 Мобильный</span>' : 
                          l.phone_type === 'landline' ? '<span class="badge badge-landline">☎️ Городской</span>' : '—'}}
                    </td>
                    <td>${{l.website ? `<a href="${{l.website}}" target="_blank">🌐 Перейти</a>` : '—'}}</td>
                    <td>
                        ${{l.telegram ? `<a href="${{l.telegram}}" target="_blank">✈️ TG</a> ` : ''}}
                        ${{l.whatsapp ? `<a href="${{l.whatsapp}}" target="_blank">💬 WA</a> ` : ''}}
                        ${{l.vk ? `<a href="${{l.vk}}" target="_blank">🟦 VK</a>` : ''}}
                        ${{!l.telegram && !l.whatsapp && !l.vk ? '—' : ''}}
                    </td>
                    <td>${{l.address || '—'}}</td>
                </tr>
            `).join('');
        }}

        function filterTable() {{
            const val = document.getElementById("searchInput").value.toLowerCase();
            const filtered = leads.filter(l => 
                (l.name && l.name.toLowerCase().includes(val)) ||
                (l.phone && l.phone.toLowerCase().includes(val)) ||
                (l.address && l.address.toLowerCase().includes(val))
            );
            renderRows(filtered);
        }}

        renderRows(leads);
    </script>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filepath
