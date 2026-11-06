"""Build ordinary static pages with relative, GitHub Pages compatible URLs."""
import ast
import hashlib
import html
import json
import shutil
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from replay import ROOT, replay
from localize import english_page

HERE = Path(__file__).resolve().parent
DIST = HERE / 'dist'
DATA = json.loads((HERE / 'content.json').read_text(encoding='utf-8'))
EXAMPLE = json.loads((HERE / 'inputs/player-example.json').read_text(encoding='utf-8'))
POLICIES = {p['id']: p for p in DATA['policies']}
FAMILIES = {f['id']: f for f in DATA['families']}
FEATURES = {
    'collect_needed': 'Сбор нужного снаряжения', 'collect_excess': 'Избыточный сбор (сейчас запрещён)',
    'collect_degree_one': 'Сбор снаряжения с одним внешним входом', 'wins': 'Победа',
    'closes_last_without_win': 'Последний тоннель закрыт без победы',
    'delta_open_tunnels': 'Уменьшение открытых концов', 'delta_visible_water': 'Уменьшение видимой воды',
    'delta_merge_opportunities': 'Прирост возможностей соединения',
    'delta_water_obstruction': 'Уменьшение препятствий возле воды', 'new_trapped_water': 'Новая запертая вода',
    'bounded_merge_setup_gain': 'Положительный прирост ограниченного банка',
    'places_exit_ready': 'Выход при готовом снаряжении', 'places_exit_early': 'Выход до готовности снаряжения',
}


def esc(value):
    return html.escape(str(value), quote=True)


def script_data(id, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    return f'<script type="application/json" id="{id}">{raw}</script>'


def page(path, title, description, content, kind='article'):
    prefix = '../' * (len(Path(path).parts) - 1)
    values = {'PREFIX': prefix, 'TITLE': esc(title), 'DESCRIPTION': esc(description), 'PAGE': kind, 'CONTENT': content,
              'RU_URL': prefix + path, 'EN_URL': prefix + 'en/' + path}
    template = (HERE / 'templates/base.html').read_text(encoding='utf-8')
    for key, value in values.items():
        template = template.replace('__' + key + '__', value)
    target = DIST / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template, encoding='utf-8')
    english = DIST / 'en' / path
    english.parent.mkdir(parents=True, exist_ok=True)
    english.write_text(english_page(template, path), encoding='utf-8')


def link_policy(id, prefix='', context=''):
    p = POLICIES[id]
    return f'<a class="policy-link" href="{prefix}strategies/{id}.html{context}"><strong>{esc(p["name"])}</strong><span>{esc(p["version"])}</span></a>'


def title_block(title, lead, back=None):
    back_link = f'<a class="back" data-return href="{back}">Вернуться к стратегиям</a>' if back else ''
    return f'{back_link}<section class="page-heading"><h1>{title}</h1><p class="lead">{lead}</p></section>'


def home():
    family_cards = []
    for f in DATA['families']:
        count = len(f['members'])
        suffix = 'подход' if count == 1 else 'варианта'
        family_cards.append(f'<a class="family-card {"featured" if f["id"] == "water" else ""}" href="families/{f["id"]}.html?view=ideas"><h3>{esc(f["name"])}</h3><p>{esc(f["summary"])}</p><span>{count} {suffix}</span></a>')
    individual = ''.join(link_policy(p['id'], context='?view=policies') for p in DATA['policies'])
    timeline = []
    for stage in DATA['stages']:
        entries = ''.join(link_policy(id, context='?view=journey') for id in stage['members'])
        timeline.append(f'<section class="stage"><div class="stage-label">{esc(stage["label"])}</div><div><h3>{esc(stage["title"])}</h3><p>{esc(stage["problem"])}</p><div class="stage-policies">{entries}</div></div></section>')
    content = f'''
    <section class="hero"><div><h1>Хороший ход.<br>Не просто<br>удачная карта.</h1><p class="lead">Учимся выбирать из того, что есть в руке. На настоящих позициях Bandido: Alcatraz.</p><a class="primary" href="strategies/v4.html#example">Разобрать одну позицию</a><p class="small">Соло-игра · 6 карт в руке</p></div><figure class="hero-board"><div class="board" data-board="home"></div><figcaption>Настоящее поле перед 8-м действием.<br>5 открытых концов, воды нет.</figcaption><div class="pocket"><strong>Закрыть два тоннеля?</strong><span>Сначала проверь, не добавится ли вода.</span></div></figure></section>
    <section class="catalog" id="catalog" aria-labelledby="catalog-heading"><div class="section-intro"><h2 id="catalog-heading">Найди свой способ<br>выбрать ход</h2><p>Один набор стратегий. Начни с игровой задачи, найди конкретный алгоритм или проследи развитие идей.</p></div>
    <div class="catalog-tabs" role="tablist" aria-label="Способ просмотра стратегий"><button type="button" id="tab-ideas" role="tab" aria-selected="true" aria-controls="panel-ideas" data-view="ideas">По игровым задачам</button><button type="button" id="tab-policies" role="tab" aria-selected="false" aria-controls="panel-policies" data-view="policies" tabindex="-1">Все алгоритмы</button><button type="button" id="tab-journey" role="tab" aria-selected="false" aria-controls="panel-journey" data-view="journey" tabindex="-1">История развития</button></div>
    <section id="panel-ideas" role="tabpanel" aria-labelledby="tab-ideas"><p class="panel-intro">Выбери задачу на поле. Близкие варианты собраны вместе, чтобы их было проще сравнить.</p><div class="family-grid">{''.join(family_cards)}</div></section>
    <section id="panel-policies" role="tabpanel" aria-labelledby="tab-policies" hidden><p class="panel-intro">Все 15 алгоритмов, включая базовые и промежуточные варианты. У каждого есть описание, разбор позиции и точный исходный код.</p><div class="policy-grid">{individual}</div></section>
    <section id="panel-journey" role="tabpanel" aria-labelledby="tab-journey" hidden><p class="panel-intro">История идей, а не рейтинг побед. V1–V7 исследовались в прежней модели правил; подход с каталогом — отдельная ветка от V4.</p><div class="timeline">{''.join(timeline)}</div></section>
    <noscript><p>Для переключения вкладок нужен JavaScript. Все стратегии доступны через страницы игровых задач выше.</p></noscript></section>
    <section class="evidence-band"><div><h2>Совет можно проверить</h2><p>Каждый алгоритм получает только публичное поле и видимые карты. На страницах показано, какой ход он выбирает из одной сохранённой позиции.</p></div><div><strong>45 побед из 400 партий</strong><p>Исходный результат V4 в текущей модели правил. Отдельно доступны парные проверки подхода с каталогом карт.</p><a href="results.html">Посмотреть результаты и условия</a></div></section>
    {script_data('board-data', {'original': EXAMPLE['original']})}'''
    page('index.html', 'Стратегии для игрока', 'Игровые задачи, все алгоритмы и история развития стратегий Bandido: Alcatraz.', content, 'home')


def family_pages():
    for f in DATA['families']:
        cards = ''.join(f'<article class="family-option"><div><p class="version">{esc(POLICIES[id]["version"])}</p><h2>{esc(POLICIES[id]["name"])}</h2><p>{esc(POLICIES[id]["summary"])}</p><p class="muted">{esc(POLICIES[id]["difference"])}</p></div><a class="secondary" href="../strategies/{id}.html?view=ideas">Разобрать подход</a></article>' for id in f['members'])
        content = title_block(esc(f['name']), esc(f['summary']), '../index.html?view=ideas#catalog')
        content += f'<div class="family-options">{cards}</div><section class="reading"><h2>Как сравнивать варианты</h2><p>На каждой странице использована одна и та же публичная позиция. Это позволяет увидеть различия в выборе хода. Один пример не заменяет проверку частоты побед на множестве партий.</p><a href="../results.html">Что известно о результатах</a></section>'
        page(f'families/{f["id"]}.html', f['name'], f['summary'], content, 'family')


def example_section(p, agent):
    ex, m = agent['example'], agent['example']['move']
    reason = {
        'random': 'Случайный выбор использует RNG=0. У него нет оценки качества: другой seed может дать другой допустимый ход.',
        'min-open': 'Алгоритм выбирает минимум открытых концов. В этой позиции он сокращает их до трёх, одновременно добавляя воду.',
        'v0': 'Небольшой штраф за новую воду не перевешивает выигрыш от двух закрытых концов. Это показывает пределы ближайшей оценки с исходными весами.',
        'v1': 'В этой руке нет карты снаряжения, поэтому специальный штраф V1 не срабатывает. Совпадение с V0 здесь не означает, что политики одинаковы.',
        'discard-v2': 'В текущих правилах избыточный сбор запрещён. На этом поле изменение исторического веса не влияет на выбор относительно V0.',
        'v5': 'Выход уже виден в руке. Защитный фильтр V5 поэтому выключен, и выбор совпадает с V4-250.',
        'v6': 'Алгоритм учитывает лучшее следующее действие оставшейся видимой рукой. Его выбор здесь отличается от ближайшей оценки V4.',
        'v7': 'Сначала проверяются двухшаговые продолжения, затем немедленная оценка среди равных. На этом поле выбор совпал с V6.',
        'catalog': 'После выбора близких по V4 ходов учитывается поддержка каталога. Здесь итог совпал с V4 при том же RNG; это не означает, что добавка меняет каждую позицию.',
    }.get(p['id'], 'Алгоритм предпочитает продолжение картой 3 без новой воды. Пять открытых концов сейчас оказываются предпочтительнее трёх с новой водной задачей.')
    scores = ''
    if ex['local_AB_scores']:
        a, b = ex['local_AB_scores']
        scores = f'<div class="score-pair"><div><span>Ход A: карта 3, без воды</span><strong>{a:+,}</strong></div><div><span>Ход B: карта 5, новая вода</span><strong>{b:+,}</strong></div></div><p class="small">Немедленные взвешенные оценки двух фиксированных ходов. Для V5–V7 и подхода с каталогом они не заменяют полный порядок выбора.</p>'
    return f'''<section class="reading" id="example"><div class="section-intro"><h2>Одна позиция.<br>Выбор этого алгоритма.</h2><p>Перед 8-м действием: 6 карт в руке, 1 из 3 плащей и 1 из 2 верёвок. Выход виден в руке, ещё не размещён.</p></div><div class="lesson-grid"><div><figure class="game-mat"><div class="board" data-board="lesson"></div><figcaption id="board-caption" aria-live="polite">5 открытых концов · воды нет</figcaption></figure><p class="small board-key">Синяя рамка — старт. Кольца — открытые концы. Цветная рамка — добавленная карта.</p></div><div class="lesson-notes"><div class="choice-controls" role="group" aria-label="Состояние поля"><button type="button" data-step="before" aria-pressed="true">До хода</button><button type="button" data-step="chosen" aria-pressed="false">Выбор алгоритма</button></div><h3>Карта {m['hand_index'] + 1}, поворот {m['quarter_turns'] * 90}°</h3><p>{esc(reason)}</p><p>После хода: <strong>{ex['open']} открытых концов · {ex['water']} водных полуполей</strong>.</p><details><summary>Точные координаты хода</summary><div><p>Индекс в исходной руке: <code>{m['hand_index']}</code>. Origin: <code>{esc(m['origin'])}</code>, четвертей поворота: <code>{m['quarter_turns']}</code>.</p></div></details></div></div><h3 class="hand-heading">Все шесть карт до хода</h3><div class="hand" id="hand"></div><div class="position-note"><h3>Что именно показано</h3><p>Настоящая сохранённая позиция, seed 1000263, решение 8. Выбор пересчитан текущим кодом с <code>Random(0)</code>. Исторический ход и состояние RNG не сохранены; будущий добор и исход партии здесь не предсказываются.</p></div>{scores}<p><a href="../example.html">Сравнить ходы A и B на этом же поле</a></p></section>'''


def agent_section(p, agent):
    source = (ROOT / agent['source']).read_text(encoding='utf-8')
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == p['code'])
    code = '\n'.join(source.splitlines()[node.lineno - 1:node.end_lineno])
    source_name = agent['source'].replace('/', '--') + '.txt'
    table = ''
    if agent['weights']:
        rows = ''.join(f'<tr><th scope="row">{esc(FEATURES[k])}<code>{k}</code></th><td>{v:+,}</td></tr>' for k, v in agent['weights'].items())
        table = f'<table class="weights"><caption>Полные веса этой конфигурации</caption><thead><tr><th scope="col">Признак</th><th scope="col">Вес</th></tr></thead><tbody>{rows}</tbody></table>'
    extra = ''
    if p['id'] == 'v4':
        extra = '<p><strong>Укажи setup_weight=250 явно.</strong> Конструктор по умолчанию использует 500, что не соответствует показанному базовому эксперименту.</p>'
    if p['id'] == 'catalog':
        extra += '<p>Поддержка цели считается по физическим записям карт, с насыщением на 4. Сначала случайно выбирается максимум V4; если это COLLECT, он возвращается. Иначе рассматриваются он и до двух PLACE из стабильной сортировки по убыванию V4 в пределах 1000. Выбор меняется только при строго большей минимальной поддержке; равенство сохраняет предыдущий.</p>'
    if p['id'] in ('v6', 'v7'):
        extra += '<p>Оценка последовательности: score(first) + max(score(second)). Если после первого действия победа, ноль открытых концов или нет второго действия, используется только score(first). Второе действие берётся из оставшейся видимой руки, без добора.</p>'
    return f'''<details class="agent" id="agent"><summary>Точный алгоритм для агента</summary><div><h2>{esc(p['code'])}</h2><p>{esc(p['contract'])}</p>{extra}<p>Вход: публичное PlayerObservation, видимая рука, публичный каталог (когда нужен) и переданный RNG. Скрытая колода недоступна. При отсутствии допустимых ходов возвращается None.</p><p>Порядок ходов задаёт движок. Равенство разрешается rng.choice в порядке кандидатов, кроме явно описанных дополнительных ступеней.</p>{table}<h3>Определение признаков</h3><p>Уменьшения: «до − после». Прирост соединений: «после − до». Возможности соединения — сумма n(n−1)/2 для пустых клеток, в которые направлены n открытых концов. Ограниченный банк — min(возможности, 6), пока открытых концов ≤ 10, иначе 0; его прирост — max(0, после − до). Запертая вода не имеет свободных соседей по четырём сторонам. Новая запертая вода — max(0, число после − число до).</p><p>COLLECT оценивается только по снаряжению. Полные определения, порядок ходов и геометрия включены в пакет исходников.</p><h3>Реализация класса</h3><pre><code>{esc(code)}</code></pre><p>Исходник: <a href="../sources/{source_name}">{esc(agent['source'])}</a><br>SHA-256: <code>{agent['source_sha256']}</code></p><div class="download-links"><a class="secondary" href="../agents/{p['id']}.json" download>Скачать описание JSON</a><a class="secondary" href="../downloads/strategy-source.zip" download>Скачать код и воспроизведение</a></div><pre><code>py -3.11 replay.py</code></pre><p>После распаковки пакета. Python 3.11 или новее; библиотеки и сеть не нужны. Скрипт проверяет позицию и выводит 15 легальных ходов с RNG=0. Это воспроизведение примера, не всех исследовательских партий.</p></div></details>'''


def strategy_pages(agents):
    for p in DATA['policies']:
        agent, f = agents[p['id']], FAMILIES[p['family']]
        siblings = [id for id in f['members'] if id != p['id']] or ['v4']
        related = ''.join(link_policy(id, '../') for id in siblings)
        badge = 'Текущая модель: базовый эксперимент' if p['id'] == 'v4' else 'Текущая модель: парные проверки' if p['id'] == 'catalog' else 'Исторический подход; пример пересчитан по текущим правилам'
        content = title_block(esc(p['name']), esc(p['summary']), '../index.html#catalog')
        content += f'<p class="version">{esc(p["version"])} · {badge}</p><nav class="contents" aria-label="Содержание стратегии"><a href="#player">Как применять</a><a href="#example">Разбор хода</a><a href="#evidence">Результаты</a><a href="#agent">Для агента</a></nav>'
        content += f'<div class="strategy-layout"><div><section class="player-rule" id="player"><h2>Как действовать игроку</h2><p>{esc(p["rule"])}</p></section><section class="difference"><h2>Чем отличается</h2><p>{esc(p["difference"])}</p><p class="muted">Совет для человека упрощает взвешенную оценку. Чтобы точно повторить алгоритм, используй описание и исходники ниже.</p></section></div><aside><h2>Близкие подходы</h2>{related}<a class="family-back" href="../families/{f["id"]}.html?view=ideas">{esc(f["name"])}</a></aside></div>'
        content += example_section(p, agent)
        anchor = p['id'] if p['id'] in ('v4', 'catalog') else 'historical'
        content += f'<section class="reading" id="evidence"><h2>Что показала проверка</h2><p>{esc(p["evidence"])}</p><p>Одиночный пересчёт хода выше не измеряет частоту побед и не превращает старый результат в проверку по новым правилам.</p><a href="../results.html#{anchor}">Условия, ограничения и источники</a></section>'
        content += agent_section(p, agent)
        content += '<div class="return"><a class="secondary" data-return href="../index.html#catalog">Вернуться к стратегиям</a></div>'
        content += script_data('board-data', {'original': EXAMPLE['original'], 'chosen': agent['example']['after'], 'chosenMove': agent['example']['move']})
        page(f'strategies/{p["id"]}.html', p['name'], p['summary'], content, 'strategy')


def reference_pages():
    for name in ('rules', 'results', 'method', 'example'):
        source = (HERE / 'templates' / (name + '.html')).read_text(encoding='utf-8')
        if name == 'example':
            source += script_data('board-data', {'original': EXAMPLE['original'], 'a': EXAMPLE['choices'][0]['observation'], 'b': EXAMPLE['choices'][1]['observation'], 'ab': True})
        titles = {'rules': 'Правила модели', 'results': 'Результаты проверок', 'method': 'Как воспроизвести', 'example': 'Разбор двух ходов'}
        page(name + '.html', titles[name], titles[name] + ' Bandido: Alcatraz: условия, источники и проверка.', source, name)


def copy_sources(agents):
    source_paths = {a['source'] for a in agents.values()} | {'docs/modeling-v2.md', 'docs/catalog-support-policy.md', 'src/bandido_alcatraz/strategy.py', *[f'experiments/real-deck-policy-v{i}/README.md' for i in range(1, 5)]}
    for source in sorted(source_paths):
        shutil.copyfile(ROOT / source, DIST / 'sources' / (source.replace('/', '--') + '.txt'))
    manifests = {
        'baseline': 'experiments/canonical-quota-limited-solo-baseline/baseline-2026-10-01.manifest.json',
        'v5': 'experiments/real-deck-policy-v5/visible-repair-reserve-development-evaluation-2026-09-24.manifest.json',
        'v6': 'experiments/real-deck-policy-v6/current-model-spent-development-1000-1099-2026-09-28.json',
        'v7': 'experiments/real-deck-policy-v7/fresh-development-1000000-1000399-2026-09-30.manifest.json',
    }
    for name, source in manifests.items():
        shutil.copyfile(ROOT / source, DIST / 'sources' / (name + '.manifest.json'))
    manifest = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'ruleset': EXAMPLE['ruleset'], 'example_snapshot_sha256': EXAMPLE['source_snapshot_sha256'], 'policy_count': len(agents), 'source_files': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(source_paths | set(manifests.values()))}}
    (DIST / 'sources/site-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for id, data in agents.items():
        (DIST / 'agents' / (id + '.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copyfile(HERE / 'inputs/bandido-example-reproduction.zip', DIST / 'downloads/bandido-example-reproduction.zip')
    modules = ['__init__', 'board', 'deck_data', 'game', 'model', 'moves', 'photo_geometry', 'physical_deck', 'policies', 'rules', 'setup', 'strategy', 'catalog_support', 'simulate']
    files = [ROOT / f'src/bandido_alcatraz/{name}.py' for name in modules]
    files += [ROOT / f'src/bandido_alcatraz/worker32/{name}.py' for name in ['__init__', 'inputs', 'evidence']]
    files += [ROOT / 'scripts/run_worker26.py'] + [ROOT / f'data/{name}.json' for name in ['deck-v1', 'deck-observations-v0']]
    payload = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    payload.update({'replay.py': (HERE / 'replay.py').read_bytes(), 'content.json': (HERE / 'content.json').read_bytes(), 'player-example.json': (HERE / 'inputs/player-example.json').read_bytes()})
    payload['SHA256SUMS.json'] = json.dumps({p: hashlib.sha256(raw).hexdigest() for p, raw in payload.items()}, indent=2).encode()
    with ZipFile(DIST / 'downloads/strategy-source.zip', 'w', ZIP_DEFLATED) as archive:
        for name, raw in payload.items():
            archive.writestr(name, raw)


def main():
    for name in ('assets', 'sources', 'agents', 'downloads'):
        (DIST / name).mkdir(parents=True, exist_ok=True)
    for source in (HERE / 'assets').iterdir():
        if source.is_file():
            shutil.copyfile(source, DIST / 'assets' / source.name)
    agents = replay(DATA, EXAMPLE)
    home()
    family_pages()
    strategy_pages(agents)
    reference_pages()
    copy_sources(agents)
    (DIST / '.nojekyll').write_text('', encoding='utf-8')
    print(f'Built {len(list(DIST.rglob("*.html")))} pages, {len(agents)} policies. Output: {DIST}')


if __name__ == '__main__':
    main()
