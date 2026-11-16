import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resources.lib import logo_cache


class Enricher:
    tmdb_key = 'k'

    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    def logo_for(self, kind, title, year=None):
        self.asked.append((kind, title, year))
        return self.answers.get(title, '')


def test_unknown_titles_are_queued_then_filled_by_the_service(tmp_path):
    cache = logo_cache.LogoCache(str(tmp_path), now=lambda: 1000)
    assert cache.get('series', 'Flikken') is None
    assert cache.get('movie', 'Soof', 2013) is None
    cache.flush()

    service = Enricher({'Flikken': 'https://img/flikken.png'})
    assert logo_cache.LogoCache(str(tmp_path), now=lambda: 1000).process(service) == 2
    assert service.asked == [('series', 'Flikken', None), ('movie', 'Soof', 2013)]
    assert not os.path.exists(cache.queue_path)

    again = logo_cache.LogoCache(str(tmp_path), now=lambda: 2000)
    assert again.get('series', 'flikken') == 'https://img/flikken.png'
    assert again.get('movie', 'Soof', 2013) == ''  # TMDb has none: not asked again
    again.flush()
    assert not os.path.exists(again.queue_path)


def test_unreachable_tmdb_keeps_the_queue(tmp_path):
    cache = logo_cache.LogoCache(str(tmp_path), now=lambda: 1000)
    cache.get('series', 'A')
    cache.flush()

    class Offline(Enricher):
        def logo_for(self, kind, title, year=None):
            return None

    assert logo_cache.LogoCache(str(tmp_path)).process(Offline({})) == 0
    assert os.path.exists(cache.queue_path)


def test_no_key_drops_the_queue(tmp_path):
    cache = logo_cache.LogoCache(str(tmp_path))
    cache.get('series', 'A')
    cache.flush()
    no_key = Enricher({})
    no_key.tmdb_key = ''
    assert logo_cache.LogoCache(str(tmp_path)).process(no_key) == 0
    assert not os.path.exists(cache.queue_path)
