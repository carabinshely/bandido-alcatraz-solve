"""Full player lessons and agent contracts for the four completed experiments."""
import html
import json
from pathlib import Path

from recent import STUDIES, IDEAS
from result_data import percent, recorded_results

HERE = Path(__file__).resolve().parent
RULES = {
    110: ['Если EXIT уже в руке, снаряжение ещё не собрано и каталог советует другую карту, проверь раннюю постановку выхода.',
          'Ищи сухую постановку, которая убирает одну целевую клетку и полностью сохраняет остальные открытые направления. Хотя бы один открытый конец должен остаться.',
          'Попытка планирования только одна за партию. Если подходящего размещения нет или достигнут лимит, продолжай по каталогу. Ранний выход может помешать дальнейшей геометрии.'],
    113: ['Сначала размести EXIT и собери ровно три плаща и две верёвки. До этого используй каталог.',
          'Среди трёх близких по оценке ходов отбрасывай те, после которых хотя бы одна цель совсем не поддерживается каталогом карт.',
          'Выбирай меньше открытых концов. При равенстве — лучшую поддержку, затем оценку V4 и стабильный порядок. Это приоритет завершения тоннелей, а не гарантия победы.'],
    127: ['После EXIT и полного снаряжения сравни несколько близких ходов, уже рассмотренных каталогом.',
          'Считай открытые целевые клетки и воду общей задачей: соседние задачи иногда можно обслужить одной картой. Графовая оценка L приближает минимальный объём оставшейся работы.',
          'Меняй ход каталога только при строго меньшем L и ненулевой поддержке. Такое отклонение разрешено один раз за партию; затем снова следуй каталогу.'],
    129: ['Используй то же сравнение оставшейся работы, что в варианте 127, но внимательнее проверь воду.',
          'Соседство воды с целью учитывай только тогда, когда у водной клетки есть тоннель, направленный к этой цели. Просто стоять рядом недостаточно.',
          'Нужны размещённый EXIT, три плаща и две верёвки. Разрешена одна замена хода каталога, только при строго меньшем L; равенство сохраняет прежний выбор.'],
}
CONTRACTS = {
    110: 'Сначала вызвать baseline.choose с переданным RNG. Вернуть fallback без планирования при None, COLLECT, уже размещённом EXIT, выборе EXIT самим каталогом, готовом снаряжении, использованной попытке, иной конфигурации руки/игрока или отложенных картах. При единственном каноническом EXIT в руке установить planned=True. Перебирать отсортированные цели, повороты 0–3 и клетки EXIT; удалить повторы origin/rotation. Допустим только точный остаток Counter целей после удаления одной цели и post_open>0. Выбрать максимум V4, первое равенство сохранить. Лимиты: 48 исходных клеток, 50 после хода, 12 целей, 96 выравниваний, кооперативный срок 3 секунды. При лимите или исключении вернуть уже рассчитанный fallback. Состояние planned/returned_none сохранять всю партию.',
    113: 'Полный порядок: допустимые ходы; немедленная победа через rng.choice; затем максимум V4-250 через rng.choice. COLLECT вернуть сразу. Построить до трёх кандидатов: выбранный максимум и PLACE в стабильном порядке (-V4score, legal_index), отстающие не более чем на 1000. После EXIT и готового снаряжения оставить support>0 и минимизировать (open_tunnels, -support, -V4score, legal_index). Если подходящих нет либо ветка ещё не включена, применить обычное строгое улучшение weakest-support каталога. Отдельного межходового состояния нет.',
    127: 'Сначала выполнить замороженный CatalogSupportPolicy с исходным RNG и захватить именно его обращения к _weakest_support: от одного до трёх уникальных PLACE. Сохранить None, COLLECT и немедленную победу. Ветка требует exit_placed=True, (raincoats,ropes)==(3,2), departed=False и support(anchor)>0. Для кандидатов с support>0 построить Q=targets∪water. Рёбра — соседство по Манхэттену на один, кроме water–water. Через максимальное двудольное паросочетание M вычислить L=|Q|−|M|, проверить равенство размеров matching и vertex cover. При |Q|>64 или неизвестном capture вернуть anchor. Заменять только при строго меньшем L в захваченном порядке; равенство сохраняет текущий выбор. После фактической замены установить departed=True до конца партии.',
    129: 'Контракт состояния, capture, fallback, лимита Q≤64 и строгого сравнения L полностью совпадает с вариантом 127. Отличается разрешение рёбер: dry–dry допускается, water–water запрещено; water–target допускается только при наличии у water тоннельного порта в сторону target. Используются публичные board.cells и tunnel_edges, без скрытой колоды. Значение L — эвристическая нижняя оценка в ослабленной модели, а не сертификат выигрыша или отсутствия потерь.',
}
REASONS = {
    110: 'В руке есть EXIT, но не хватает двух плащей и одной верёвки. Каталог продолжает тоннель картой 3. Ранняя постановка EXIT картой 1 убирает цель (−3, 0), оставляя остальные цели прежними: открытых концов становится четыре вместо пяти. Её оценка V4 ниже, но специальное правило предпочитает подходящий ранний выход.',
    113: 'Выход уже размещён, снаряжение собрано. Каталог выбирает карту 6 и оставляет шесть открытых концов. Вариант выбирает карту 2 и оставляет четыре: после выхода уменьшение числа концов имеет приоритет среди близких ходов с поддержкой каталога.',
    127: 'Каталог выбирает карту 2. Вариант предпочитает карту 1: открытых концов четыре вместо шести, а общая оценка работы L уменьшается с 4 до 3. Немедленная оценка V4 при этом немного хуже — алгоритм осознанно предпочитает меньшую оставшуюся задачу.',
    129: 'На поле есть вода, EXIT размещён и снаряжение собрано. В захваченном наборе ходов оценка с учётом портов даёт L=8 для хода каталога и L=7 для выбранного хода. Ниже можно проверить цели, рёбра паросочетания и ориентацию карты; одна лишь близость воды не считается совместной задачей.',
}


def generate_recent_pages(page, title_block, script_data, agents):
    e = html.escape
    baseline_rate = next(percent(r['wins'],r['games']) for r in recorded_results()['catalog'] if r['primary'])
    for s in STUDIES:
        n = s['number']
        a = agents[str(n)]
        ex = a['example']
        m, b, original = ex['move'], ex['baseline_move'], ex['original']
        rule = ''.join('<li>' + e(text) + '</li>' for text in RULES[n])
        graph_row = ''
        if n in (127,129):
            d = ex['diagnostics']
            graph_row = f'<tr><th scope="row">Оценка оставшейся работы L</th><td>{d["anchor_L"]}</td><td>{d["chosen_L"]}</td></tr>'
        code = (HERE / 'inputs/research-code' / s['code_file']).read_text(encoding='utf-8')
        result = f'''<section class="strategy-result" id="evidence"><h2>Процент побед в завершённой проверке</h2>
        <div class="score-pair"><div><span>Экспериментальный вариант</span><strong>{percent(s['wins_candidate'],s['pairs'])}</strong><span>{s['wins_candidate']} / {s['pairs']}</span></div><div><span>Контроль: каталог карт</span><strong>{percent(s['wins_control'],s['pairs'])}</strong><span>{s['wins_control']} / {s['pairs']}</span></div></div>
        <p>Превосходство не подтверждено; вариант не принят базовой стратегией.</p><p>Seeds: <code>{s['seeds']}</code> · {s['date']}</p><a href="../results.html#recent-{n}">Условия, статистика и точный код</a></section>'''
        content = title_block(e(s['name']), e(IDEAS[n]), '../index.html#catalog')
        content += f'<p class="version">#{n} · Экспериментальный вариант · 6 карт</p>' + result
        content += '<nav class="contents" aria-label="Содержание стратегии"><a href="#player">Как применять</a><a href="#example">Разбор хода</a><a href="#evidence">Результаты</a><a href="#agent">Для агента</a></nav>'
        content += f'<section class="reading" id="player"><h2>Как действовать игроку</h2><ol class="player-steps">{rule}</ol><p class="muted">Совет для человека упрощает алгоритм. Для точного повторения используй контракт и исходники ниже.</p><p><a href="../strategies/catalog.html">Сверяться с каталогом карт · {baseline_rate}</a></p></section>'
        content += f'''<section class="reading" id="example"><h2>Настоящая позиция. Два решения.</h2>
        <p>Seed / номер решения:</p><p><code>{ex['game_seed']} / {ex['decision']}</code></p><p>Снаряжение до хода: плащи / верёвки</p><p><code>{original['raincoats']} / {original['ropes']}</code></p>
        <div class="choice-controls" role="group" aria-label="Состояние поля"><button type="button" data-step="before" aria-pressed="true">До хода</button><button type="button" data-step="catalog" aria-pressed="false">Ход каталога</button><button type="button" data-step="chosen" aria-pressed="false">Выбор алгоритма</button></div>
        <figure class="game-mat"><div class="board {'wide-board' if n == 129 else ''}" data-board="lesson" tabindex="0" role="region" aria-label="Игровое поле"></div><figcaption id="board-caption" aria-live="polite"></figcaption></figure>
        {'<p class="small">Большое поле можно прокручивать по горизонтали, в том числе стрелками с клавиатуры.</p>' if n == 129 else ''}
        <p>{REASONS[n]}</p>
        {'<p>Водная клетка (12, 5) имеет тоннели на север и юг. Цель (11, 5) находится к западу, где порта нет. Прежняя оценка объединяет их и даёт ходу каталога L=7; проверка направления убирает это ребро и даёт L=8.</p>' if n == 129 else ''}
        <p class="small board-key">Синяя рамка — старт. Кольца — открытые концы. Цветная рамка — добавленная карта.</p>
        <table><caption>Два пересчитанных хода на одной позиции</caption><thead><tr><th scope="col">Показатель</th><th scope="col">Ход каталога</th><th scope="col">Выбор алгоритма</th></tr></thead><tbody>
        <tr><th scope="row">Карта в руке</th><td>{b['hand_index']+1}</td><td>{m['hand_index']+1}</td></tr>
        <tr><th scope="row">Поворот</th><td>{b['quarter_turns']*90}°</td><td>{m['quarter_turns']*90}°</td></tr>
        <tr><th scope="row">Открытых концов после хода</th><td>{ex['baseline_open']}</td><td>{ex['open']}</td></tr>
        <tr><th scope="row">Водных полуполей после хода</th><td>{ex['baseline_water']}</td><td>{ex['water']}</td></tr>
        <tr><th scope="row">Немедленная оценка V4</th><td>{ex['baseline_v4_score']}</td><td>{ex['v4_score']}</td></tr>{graph_row}</tbody></table>
        <h3 class="hand-heading">Все шесть карт до хода</h3><div class="hand" id="hand"></div>
        <details><summary>Координаты и вычисления</summary><div><p>Origin / четвертей поворота / индекс карты (с нуля):</p><pre><code>{e(json.dumps(dict(catalog=b,chosen=m),indent=2))}</code></pre><p>Диагностика специального правила:</p><pre><code>{e(json.dumps(ex['diagnostics'],indent=2))}</code></pre></div></details>
        <div class="position-note"><h3>Что именно показано</h3><p>Публичное поле и рука взяты из сохранённой партии. Оба выбора заново рассчитаны с Random(0); это не восстановленный исторический RNG. Новая колода не разыгрывается, будущий добор и исход партии не предсказываются.</p><p>Состояние политики перед решением явно записано в JSON. Это заданные условия отдельного пересчёта, а не восстановление всей истории партии. Один разбор показывает механизм выбора, а не общую частоту побед.</p><p>SHA-256 публичной позиции: <code>{a['provenance']['source_snapshot_sha256']}</code></p></div></section>'''
        content += f'''<details class="agent" id="agent"><summary>Точный алгоритм для агента</summary><div><h2>{s['class_name']}</h2><p>{CONTRACTS[n]}</p>
        <p>Создавай новый экземпляр политики для новой партии; сохраняй тот же экземпляр между ходами. Вход — публичный PlayerObservation, видимая рука, публичный каталог и переданный RNG. Скрытая колода недоступна.</p>
        <h3>Реализация класса</h3><pre><code>{e(code)}</code></pre>
        <p><a href="../sources/{s['code_file']}">Замороженный исходник политики</a> · <a href="../sources/local92_catalog_baseline.py.txt">CatalogSupport: замороженный контроль</a></p><p>SHA-256: <code>{s['policy_sha256']}</code></p>
        <div class="download-links"><a class="secondary" href="../agents/research-{n}.json" download>Скачать описание JSON</a><a class="secondary" href="../downloads/recent-strategy-source.zip" download>Скачать код и воспроизведение</a></div>
        <pre><code>python replay_recent.py</code></pre><p>После распаковки пакета. Python 3.11 или новее; библиотеки и сеть не нужны. Проверяются четыре отдельных решения, легальность, контрольные суммы и неизменность входа; новые партии не запускаются.</p>
        <p><a href="../sources/recent-examples.json">Публичные позиции и происхождение</a> · <a href="../sources/recent-research.json">Агрегаты, seeds и версии исходников</a></p></div></details>'''
        content += '<div class="return"><a class="secondary" data-return href="../index.html#catalog">Вернуться к стратегиям</a></div>'
        content += script_data('board-data',dict(original=original,chosen=ex['after'],chosenMove=m,catalog=ex['baseline_after'],catalogMove=b))
        page(f'strategies/research-{n}.html',s['name'],IDEAS[n],content,'strategy')
