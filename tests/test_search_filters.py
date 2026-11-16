import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resources.lib import search_filters as sf

ITEMS = [
    {'title': 'Oud', 'raw': {'productionYear': 1985, 'genres': ['Drama']}},
    {'title': 'Nieuw', 'year': 2022, 'raw': {'genres': [{'name': 'Komedie'}, {'name': 'Drama'}]}},
    {'title': 'Tien', 'raw': {'releaseDate': '2014-03-01', 'genre': 'Thriller'}},
    {'title': 'Onbekend'},
]


def test_options_list_only_what_exists():
    periods, genres = sf.options(ITEMS)
    assert periods == ['2020', '2010', 'old']
    assert genres[0] == 'Drama' and set(genres) == {'Drama', 'Komedie', 'Thriller'}


def test_apply_period_and_genre_never_guess():
    assert [i['title'] for i in sf.apply(ITEMS, period='2020')] == ['Nieuw']
    assert [i['title'] for i in sf.apply(ITEMS, genre='drama')] == ['Oud', 'Nieuw']
    assert [i['title'] for i in sf.apply(ITEMS, period='old', genre='Drama')] == ['Oud']
    assert len(sf.apply(ITEMS)) == 4


def test_describe_in_both_languages():
    assert sf.describe(sf.texts('nl'), '2010', 'Drama') == 'Filter: 2010 - 2019, Drama'
    assert sf.describe(sf.texts('en')) == 'Filter: none'
