"""Public-site integrity: inventories, reproducible contracts and portable URLs."""
import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'website'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.urls.append(attrs[key])


def test_complete_site_and_local_links():
    assert (SITE / 'build.py').exists(), 'Static site builder is missing'
    subprocess.run([sys.executable, str(SITE / 'build.py')], cwd=ROOT, check=True)
    content = json.loads((SITE / 'content.json').read_text(encoding='utf-8'))
    policies = content['policies']
    assert len(policies) == 15
    assert len({p['id'] for p in policies}) == 15
    for grouping in ('families', 'stages'):
        members = [id for group in content[grouping] for id in group['members']]
        assert sorted(members) == sorted(p['id'] for p in policies)
    dist = SITE / 'dist'
    for policy in policies:
        page = dist / 'strategies' / (policy['id'] + '.html')
        assert page.exists()
        agent = json.loads((dist / 'agents' / (policy['id'] + '.json')).read_text(encoding='utf-8'))
        assert agent['class'] == policy['code']
        assert agent['source_sha256']
        assert agent['example']['move']
        if policy['id'] == 'v4':
            assert agent['parameters'] == {'setup_weight': 250}
            assert agent['weights']['bounded_merge_setup_gain'] == 250
    for page in dist.rglob('*.html'):
        parser = Links()
        parser.feed(page.read_text(encoding='utf-8'))
        assert len(parser.ids) == len(set(parser.ids)), f'Duplicate ids: {page}'
        for raw in parser.urls:
            url = urlsplit(raw)
            if url.scheme or url.netloc:
                continue
            assert not url.path.startswith('/'), f'Absolute URL breaks project prefix: {raw}'
            target = (page.parent / unquote(url.path)).resolve() if url.path else page
            assert target.is_file(), f'Broken link {page}: {raw}'
            if url.fragment and target.suffix == '.html':
                other = Links()
                other.feed(target.read_text(encoding='utf-8'))
                assert unquote(url.fragment) in other.ids, f'Missing anchor: {raw}'


def test_agent_sources_match_repository():
    import hashlib
    dist = SITE / 'dist'
    for path in (dist / 'agents').glob('*.json'):
        data = json.loads(path.read_text(encoding='utf-8'))
        if path.stem.startswith('research-'):
            continue
        assert hashlib.sha256((ROOT / data['source']).read_bytes()).hexdigest() == data['source_sha256']
    assert (dist / 'agents/v7.json').exists()


def test_downloaded_reproduction_runs_without_repository(tmp_path):
    from zipfile import ZipFile
    for archive_name, script in [('strategy-source.zip', 'replay.py'),
                                 ('bandido-example-reproduction.zip', 'verify_example.py'),
                                 ('recent-strategy-source.zip', 'replay_recent.py')]:
        target = tmp_path / archive_name.removesuffix('.zip')
        with ZipFile(SITE / 'dist/downloads' / archive_name) as archive:
            archive.extractall(target)
        result = subprocess.run([sys.executable, str(target / script)], cwd=target,
                                capture_output=True, text=True, check=True)
        assert 'PASS:' in result.stdout


def test_english_has_every_page_and_no_russian_ui():
    import re
    dist = SITE / 'dist'
    russian_pages = [p for p in dist.rglob('*.html') if 'en' not in p.relative_to(dist).parts]
    for source in russian_pages:
        counterpart = dist / 'en' / source.relative_to(dist)
        assert counterpart.exists(), f'Missing English page: {counterpart}'
        text = counterpart.read_text(encoding='utf-8')
        assert '<html lang="en">' in text
        assert not re.search('[А-Яа-яЁё]', text.replace('Русский', '')), f'Untranslated Russian text: {counterpart}'
        assert 'id="language-switch"' in text
        assert 'hreflang="ru"' in text and 'hreflang="en"' in text
    assert len(russian_pages) == 31


def test_language_switches_link_equivalent_pages():
    dist = SITE / 'dist'
    for page in dist.rglob('*.html'):
        class LanguageLinks(HTMLParser):
            target = None

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if attrs.get('id') == 'language-switch':
                    self.target = attrs['href']

        parser = LanguageLinks()
        parser.feed(page.read_text(encoding='utf-8'))
        assert parser.target, f'Language switch missing: {page}'
        target = (page.parent / urlsplit(parser.target).path).resolve()
        assert target.is_file()
        source_relative = page.relative_to(dist).as_posix().removeprefix('en/')
        target_relative = target.relative_to(dist).as_posix().removeprefix('en/')
        assert source_relative == target_relative
        assert page != target


def test_numeric_results_are_shared_by_summary_and_strategy_pages():
    dist = SITE / 'dist'
    registry_path = dist / 'sources/strategy-results.json'
    assert registry_path.exists(), 'Missing sourced results registry'
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    policies = json.loads((SITE / 'content.json').read_text(encoding='utf-8'))['policies']
    assert set(registry) == {p['id'] for p in policies}
    expected = {'random': [(0, 20)], 'min-open': [(0, 20)], 'v0': [(1, 20)],
                'v1': [(0, 20)], 'discard-v2': [(0, 50)], 'water-v2': [(0, 50)],
                'combined-v2': [(0, 50)], 'merge-v3': [(1, 50)], 'space-v3': [(0, 50)],
                'combined-v3': [(1, 50)], 'v4': [(45, 400)], 'v5': [(3, 23)],
                'v6': [(5, 100)], 'v7': [(14, 400)], 'catalog': [(57, 400)]}
    for id, records in registry.items():
        primary = [record for record in records if record['primary']]
        assert [(r['wins'], r['games']) for r in primary] == expected[id]
        for record in records:
            assert 0 <= record['wins'] <= record['games']
            assert record['source_url'] and record['source_file']
            assert record['model'] in ('current', 'historical')
        for prefix in ('', 'en/'):
            detail = (dist / prefix / 'strategies' / (id + '.html')).read_text(encoding='utf-8')
            for record in primary:
                marker = f'data-result-id="{record["id"]}"'
                assert marker in detail
                assert f'{record["wins"]} / {record["games"]}' in detail
            for summary in ('index.html', 'results.html'):
                document = (dist / prefix / summary).read_text(encoding='utf-8')
                assert f'data-result-policy="{id}"' in document
                for record in primary:
                    assert f'data-result-id="{record["id"]}"' in document


def test_percentage_labels_in_history_and_related_links():
    from decimal import Decimal, ROUND_HALF_UP
    registry = json.loads((SITE / 'dist/sources/strategy-results.json').read_text(encoding='utf-8'))
    for locale in ('', 'en/'):
        for document in (SITE / 'dist' / locale).rglob('*.html'):
            if not locale and 'en' in document.relative_to(SITE / 'dist').parts:
                continue
            class PolicyLinks(HTMLParser):
                policy = None
                label = ''

                def handle_starttag(self, tag, attrs):
                    attrs = dict(attrs)
                    if tag == 'a' and attrs.get('class') == 'policy-link' and 'strategies/' in attrs.get('href', ''):
                        self.policy = attrs['href'].split('strategies/')[1].split('.html')[0]
                        self.label = ''

                def handle_data(self, text):
                    if self.policy:
                        self.label += text

                def handle_endtag(self, tag):
                    if tag == 'a' and self.policy:
                        for r in registry.get(self.policy, []):
                            if r['primary']:
                                rate = str((Decimal(r['wins']) * 100 / r['games']).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)) + '%'
                                assert (rate if locale else rate.replace('.', ',')) in self.label
                        self.policy = None
            PolicyLinks().feed(document.read_text(encoding='utf-8'))


def test_recent_completed_results_preserve_counts_and_frozen_code():
    import hashlib
    dist = SITE / 'dist'
    data = json.loads((dist / 'sources/recent-research.json').read_text(encoding='utf-8'))
    assert [(s['number'], s['wins_candidate'], s['wins_control'], s['pairs']) for s in data['studies']] == [
        (110, 287, 284, 2000), (113, 289, 287, 2000), (127, 47, 51, 400), (129, 62, 57, 400)]
    for s in data['studies']:
        assert not s['adopted'] and not s['primary_positive_superiority']
        assert s['wins_candidate'] == s['both_win'] + s['only_candidate_win']
        assert s['wins_control'] == s['both_win'] + s['only_control_win']
        assert sum(s[k] for k in ('both_win', 'neither_win', 'only_candidate_win', 'only_control_win')) == s['pairs']
        assert hashlib.sha256((dist / 'sources' / s['code_file']).read_bytes()).hexdigest() == s['policy_sha256']
        assert hashlib.sha256((dist / 'sources/local92_catalog_baseline.py.txt').read_bytes()).hexdigest() == s['control_policy_sha256']
    for locale, rate in [('', '15,50%'), ('en/', '15.50%')]:
        results = (dist / locale / 'results.html').read_text(encoding='utf-8')
        assert rate in results and '62 / 400' in results
        assert 'id="recent-129"' in results
        history = (dist / locale / 'index.html').read_text(encoding='utf-8')
        assert 'strategies/research-129.html' in history and rate in history


def test_recent_strategies_have_complete_bilingual_pages_and_examples():
    dist = SITE / 'dist'
    for number in (110, 113, 127, 129):
        for locale in ('', 'en/'):
            path = dist / locale / 'strategies' / f'research-{number}.html'
            assert path.exists(), f'Missing full strategy page: {path}'
            document = path.read_text(encoding='utf-8')
            for anchor in ('player', 'example', 'evidence', 'agent'):
                assert f'id="{anchor}"' in document
            assert 'id="board-data"' in document
            assert f'../agents/research-{number}.json' in document
        agent = json.loads((dist / 'agents' / f'research-{number}.json').read_text(encoding='utf-8'))
        assert agent['example']['input_unchanged']
        assert agent['example']['legal']
        assert agent['example']['branch_active']
        assert agent['example']['differs_from_catalog']
        assert agent['example']['kind'] == 'recalculated-public-position'
        assert agent['rng_seed'] == 0
        assert not agent['adopted']
    latest = json.loads((dist / 'agents/research-129.json').read_text(encoding='utf-8'))['example']
    assert latest['diagnostics']['anchor_L'] == 8
    assert latest['diagnostics']['chosen_L'] == 7
    assert latest['diagnostics']['relaxed_anchor_certificate']['L'] == 7
    water = next(c for c in latest['original']['board']['cells'] if (c['x'],c['y']) == (12,5))
    assert water['water'] and set(water['tunnel_edges']) == {'N','S'}
    class CatalogPanels(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sections = []
            self.links = {panel:set() for panel in ('panel-ideas','panel-policies','panel-journey')}

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'section':
                self.sections.append(attrs.get('id'))
            if tag == 'a':
                for panel in self.links:
                    if panel in self.sections:
                        self.links[panel].add(attrs.get('href'))

        def handle_endtag(self, tag):
            if tag == 'section':
                self.sections.pop()

    for locale in ('', 'en/'):
        panels = CatalogPanels()
        panels.feed((dist / locale / 'index.html').read_text(encoding='utf-8'))
        for links in panels.links.values():
            assert {f'strategies/research-{n}.html' for n in (110,113,127,129)} <= links
