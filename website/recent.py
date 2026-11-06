"""Presentation of completed experiments, separate from adopted policies."""
import html
import json
from pathlib import Path

from result_data import percent

STUDIES = json.loads((Path(__file__).parent / 'inputs/recent-research.json').read_text(encoding='utf-8'))['studies']
IDEAS = {
    110: 'Один раз попробовать ранний сухой выход, который убирает одну цель и оставляет продолжение. Если безопасный план не найден, использовать каталог.',
    113: 'После размещения выхода и сбора снаряжения предпочитать меньше открытых тоннелей среди близких по V4 ходов с ненулевой поддержкой каталога.',
    127: 'После выхода и сбора снаряжения оценивать оставшиеся тоннели и воду общей графовой нижней оценкой работы. Разрешено только одно фактическое отклонение от каталога.',
    129: 'Уточнить графовую оценку: вода связана с соседней целью только при наличии направленного к ней тоннеля. Остальные ограничения варианта 127 сохранены.',
}


def recent_links(prefix=''):
    return '<div class="stage-policies">' + ''.join(
        f'<a class="policy-link" href="{prefix}results.html#recent-{s["number"]}"><strong>{html.escape(s["name"])}</strong><span>#{s["number"]} · {percent(s["wins_candidate"], s["pairs"])}</span></a>'
        for s in STUDIES) + '</div>'


def recent_results():
    sections = []
    for s in reversed(STUDIES):
        n = s['number']
        low, high = s['paired_risk_difference_95pct_interval']
        interval = f'{100 * low:+.2f} … {100 * high:+.2f}'
        diff = f'{100 * s["paired_win_difference"]:+.2f}'
        sections.append(f'''<article class="reading recent-study" id="recent-{n}">
        <p class="version">{s['date']} · #{n}</p><h3>{html.escape(s['name'])}</h3>
        <div class="score-pair"><div><span>Экспериментальный вариант</span><strong>{percent(s['wins_candidate'], s['pairs'])}</strong><span>{s['wins_candidate']} / {s['pairs']}</span></div>
        <div><span>Контроль: каталог карт</span><strong>{percent(s['wins_control'], s['pairs'])}</strong><span>{s['wins_control']} / {s['pairs']}</span></div></div>
        <p>{IDEAS[n]}</p><p>Превосходство не подтверждено; вариант не принят базовой стратегией.</p>
        <details><summary>Условия, статистика и точный код</summary><div>
        <p>Текущая модель · 6 карт. Каждый процент рассчитан на число пар: одна партия на алгоритм в каждой паре. Наборы не объединяются.</p>
        <p>Seeds: <code>{s['seeds']}</code></p><p>Разница в процентных пунктах / 95%-й интервал:</p><p><code>{diff} / [{interval}]</code></p>
        <p>Точный двусторонний парный p: <code>{s['exact_two_sided_discordant_p']}</code></p>
        <p>Графовая оценка не является гарантией победы. Точный порядок выбора, ограничения и fallback заданы исходным кодом.</p>
        <p><a href="sources/{s['code_file']}">{s['class_name']}</a> · <a href="sources/local92_catalog_baseline.py.txt">CatalogSupport: замороженный контроль</a></p>
        <p>SHA-256: <code>{s['policy_sha256']}</code></p><p>SHA-256 исходной сводки: <code>{s['source_summary_sha256']}</code></p>
        <p><a href="sources/recent-research.json">Агрегаты, seeds и версии исходников</a></p>
        <p>Сводки и исходники проверены по SHA-256. Сырые партии остаются в закрытом архиве владельца; сайт публикует агрегаты и замороженные политики.</p>
        </div></details></article>''')
    return '<section id="recent"><h2>Последние завершённые проверки</h2><p>Обновлено 6 ноября 2026. Это экспериментальные варианты каталога, а не новые принятые версии стратегии.</p>' + ''.join(sections) + '</section>'
