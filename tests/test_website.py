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
        assert hashlib.sha256((ROOT / data['source']).read_bytes()).hexdigest() == data['source_sha256']
    assert (dist / 'agents/v7.json').exists()


def test_downloaded_reproduction_runs_without_repository(tmp_path):
    from zipfile import ZipFile
    for archive_name, script in [('strategy-source.zip', 'replay.py'),
                                 ('bandido-example-reproduction.zip', 'verify_example.py')]:
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
    assert len(russian_pages) == 27


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
