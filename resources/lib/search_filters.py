"""Filter search results by period and genre.

Works on plain result dicts: the year and genres are read from the common
keys both services use (``year``, ``releaseYear``, ``genres`` ...), also
inside a nested ``raw`` dict. Results without a year or genre are kept out
of a filter on that field, never guessed.
"""

import re

PERIODS = [
    ('2020', 2020, 2100),
    ('2010', 2010, 2019),
    ('2000', 2000, 2009),
    ('1990', 1990, 1999),
    ('old', 1900, 1989),
]

TEXT = {
    'nl': {'filter': 'Filteren', 'active': 'Filter: {}', 'none': 'geen', 'period': 'Periode',
           'genre': 'Genre', 'clear': 'Filters wissen', 'all': 'Alles',
           '2020': '2020 en later', '2010': '2010 - 2019', '2000': '2000 - 2009', '1990': '1990 - 1999',
           'old': 'Voor 1990', 'no_data': 'Deze resultaten bevatten geen jaar of genre om op te filteren.',
           'empty': 'Geen resultaten met dit filter.', 'kind': 'Soort', 'series': 'Series',
           'movie': 'Films', 'episode': 'Afleveringen'},
    'en': {'filter': 'Filter', 'active': 'Filter: {}', 'none': 'none', 'period': 'Period',
           'genre': 'Genre', 'clear': 'Clear filters', 'all': 'All',
           '2020': '2020 and later', '2010': '2010 - 2019', '2000': '2000 - 2009', '1990': '1990 - 1999',
           'old': 'Before 1990', 'no_data': 'These results have no year or genre to filter on.',
           'empty': 'No results with this filter.', 'kind': 'Type', 'series': 'Series',
           'movie': 'Films', 'episode': 'Episodes'},
}


def texts(language):
    return TEXT['nl' if str(language or '').lower().startswith('nl') else 'en']


def _sources(item):
    sources = [item] if isinstance(item, dict) else []
    raw = item.get('raw') if isinstance(item, dict) else None
    if isinstance(raw, dict):
        sources.append(raw)
        for key in ('content', 'program', 'metadata'):
            if isinstance(raw.get(key), dict):
                sources.append(raw[key])
    return sources


def item_year(item):
    for source in _sources(item):
        for key in ('year', 'releaseYear', 'release_year', 'productionYear', 'production_year',
                    'releaseDate', 'release_date', 'premiered', 'firstBroadcast', 'aired_date'):
            match = re.search(r'\b(19|20)\d{2}\b', str(source.get(key) or ''))
            if match:
                return int(match.group(0))
    return None


def item_genres(item):
    found = []
    for source in _sources(item):
        for key in ('genres', 'genre', 'categories', 'category', 'tags'):
            value = source.get(key)
            values = value if isinstance(value, (list, tuple)) else [value]
            for entry in values:
                if isinstance(entry, dict):
                    entry = entry.get('name') or entry.get('title') or entry.get('label')
                if isinstance(entry, str) and entry.strip() and entry.strip() not in found:
                    found.append(entry.strip())
    return found


def options(items):
    """Available (periods, genres) in these results, most common genres first."""
    years = [item_year(item) for item in items]
    periods = [key for key, start, end in PERIODS if any(y and start <= y <= end for y in years)]
    counts = {}
    for item in items:
        for genre in item_genres(item):
            counts[genre] = counts.get(genre, 0) + 1
    genres = sorted(counts, key=lambda g: (-counts[g], g.lower()))
    return periods, genres


def apply(items, period=None, genre=None):
    span = next(((start, end) for key, start, end in PERIODS if key == period), None)
    result = []
    for item in items:
        if span:
            year = item_year(item)
            if not year or not span[0] <= year <= span[1]:
                continue
        if genre and genre.casefold() not in {g.casefold() for g in item_genres(item)}:
            continue
        result.append(item)
    return result


def describe(t, period=None, genre=None, kind=None):
    parts = [t[kind]] if kind in ('series', 'movie', 'episode') else []
    if period in t:
        parts.append(t[period])
    if genre:
        parts.append(genre)
    return t['active'].format(', '.join(parts) if parts else t['none'])
