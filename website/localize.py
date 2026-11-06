"""Translate complete static documents, failing the build on missing text."""
import json
import re
import html
from html.parser import HTMLParser
from pathlib import Path

CYRILLIC = re.compile('[А-Яа-яЁё]')


class EnglishPage(HTMLParser):
    def __init__(self, messages, path):
        super().__init__(convert_charrefs=False)
        self.messages = messages
        self.path = path
        self.output = []
        self.language_link = False

    def translate(self, value):
        text = value.strip()
        if not CYRILLIC.search(text):
            return value
        if text in self.messages:
            translated = self.messages[text]
        elif text.endswith(' · Bandido: Alcatraz'):
            translated = self.translate(text.removesuffix(' · Bandido: Alcatraz')) + ' · Bandido: Alcatraz'
        else:
            raise ValueError('Missing English translation: ' + text)
        return value[:len(value) - len(value.lstrip())] + translated + value[len(value.rstrip()):]

    def handle_decl(self, value):
        self.output.append('<!' + value + '>')

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        switch = values.get('id') == 'language-switch'
        for key, value in attrs:
            if value and key in ('aria-label', 'alt', 'content', 'title'):
                values[key] = self.translate(value)
        if tag == 'html':
            values['lang'] = 'en'
        if switch:
            prefix = '../' * len(Path(self.path).parts)
            values.update(href=prefix + self.path, hreflang='ru', lang='ru',
                          **{'data-language': 'ru', 'aria-label': 'Switch to Russian'})
            self.language_link = True
        else:
            for key in ('src', 'href'):
                if key not in values:
                    continue
                url = values.get(key, '')
                parts = url.split('/')
                if any(folder in parts for folder in ('assets', 'sources', 'agents', 'downloads')) or values.get('rel') == 'alternate':
                    values[key] = '../' + url
        attributes = ''.join(' ' + key + ('' if value is None else '="' + html.escape(value, quote=True) + '"') for key, value in values.items())
        self.output.append('<' + tag + attributes + '>')

    def handle_endtag(self, tag):
        if tag == 'a':
            self.language_link = False
        self.output.append('</' + tag + '>')

    def handle_data(self, value):
        self.output.append('Русский' if self.language_link else self.translate(value))

    def handle_entityref(self, name):
        self.output.append('&' + name + ';')

    def handle_charref(self, name):
        self.output.append('&#' + name + ';')

    def handle_comment(self, value):
        self.output.append('<!--' + value + '-->')


def english_page(document, path):
    messages = json.loads((Path(__file__).parent / 'locales/en.json').read_text(encoding='utf-8'))
    parser = EnglishPage(messages, path)
    parser.feed(document)
    return ''.join(parser.output)


class Inventory(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.messages = set()

    def handle_data(self, value):
        if CYRILLIC.search(value):
            self.messages.add(value.strip())

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and key in ('aria-label', 'alt', 'content', 'title') and CYRILLIC.search(value):
                self.messages.add(value)


if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    inventory = Inventory()
    for page in (here / 'dist').rglob('*.html'):
        if 'en' not in page.relative_to(here / 'dist').parts:
            inventory.feed(page.read_text(encoding='utf-8'))
    (here / 'translation-inventory.json').write_text(json.dumps(dict.fromkeys(sorted(inventory.messages), ''), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(inventory.messages)} translation messages')
