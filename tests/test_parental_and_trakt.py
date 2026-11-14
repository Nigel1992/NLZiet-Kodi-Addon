import json

from resources.lib import parental, trakt_status


class Settings:
    def __init__(self, **values):
        self.values = dict(values)

    def getSetting(self, key):
        return self.values.get(key, '')

    def setSetting(self, key, value):
        self.values[key] = value


class Window:
    def __init__(self):
        self.props = {}

    def getProperty(self, key):
        return self.props.get(key, '')

    def setProperty(self, key, value):
        self.props[key] = value

    def clearProperty(self, key):
        self.props.pop(key, None)


def test_pin_is_hashed_and_profiles_need_it():
    settings, clock = Settings(), [1000.0]
    guard = parental.Parental(settings, Window(), now=lambda: clock[0])
    assert not guard.needs_pin(profile_id='adult')
    guard.set_pin('1234')
    assert '1234' not in json.dumps(settings.values)
    assert guard.verify('1234') and not guard.verify('0000')
    assert guard.toggle_profile('adult') is True
    assert guard.needs_pin(profile_id='adult') and not guard.needs_pin(profile_id='kids')


def test_correct_pin_unlocks_for_a_while_and_wrong_pin_fails():
    settings, clock = Settings(), [1000.0]
    guard = parental.Parental(settings, Window(), now=lambda: clock[0])
    guard.set_pin('2468')
    guard.toggle_profile('adult')
    assert guard.ask(iter(['1111', '2222', '3333']).__next__) is False
    assert guard.ask(iter(['1111', '2468']).__next__) is True
    assert not guard.needs_pin(profile_id='adult')
    clock[0] += parental.UNLOCK_MINUTES * 60 + 1
    assert guard.needs_pin(profile_id='adult')


def test_live_lock_only_with_setting_and_pin():
    settings = Settings(parental_lock_live='true')
    guard = parental.Parental(settings, Window())
    assert not guard.needs_pin(live=True)
    guard.set_pin('9999')
    assert guard.needs_pin(live=True)
    guard.clear_pin()
    assert not guard.needs_pin(live=True) and guard.protected_profiles() == set()


def test_kids_profile_detection():
    assert parental.is_kids_profile({'isKidsProfile': True})
    assert parental.is_kids_profile({'type': 'KIDS'})
    assert not parental.is_kids_profile({'type': 'adult', 'kids': False})


def test_trakt_index_matches_movies_and_episodes(tmp_path):
    movies = [{'movie': {'title': 'Soof', 'year': 2013}}]
    shows = [{'show': {'title': 'Wie is de Mol?'}, 'seasons': [{'number': 24, 'episodes': [{'number': 3, 'plays': 1}]}]}]
    calls = []

    def http(url, headers):
        calls.append((url, headers['Authorization']))
        return movies if url.endswith('/movies') else shows

    cache = str(tmp_path / 'trakt.json')
    index = trakt_status.load_index(cache, 'tok', 'client', http=http, now=100)
    assert index.watched({'media_type': 'movie', 'title': 'soof', 'year': '2013'})
    assert not index.watched({'media_type': 'movie', 'title': 'Soof', 'year': '1990'})
    assert index.watched({'media_type': 'episode', 'showtitle': 'Wie is de Mol', 'season': '24', 'episode': '3'})
    assert not index.watched({'media_type': 'episode', 'showtitle': 'Wie is de Mol', 'season': '24', 'episode': '4'})
    assert calls[0][1] == 'Bearer tok'
    again = trakt_status.load_index(cache, '', '', http=None, now=200)  # from the cache, no token needed
    assert again.watched({'media_type': 'movie', 'title': 'Soof'})
    assert trakt_status.load_index(cache, '', '', now=100 + trakt_status.CACHE_TTL + 1) is None


def test_trakt_token_from_script_trakt_settings():
    assert trakt_status.access_token(Settings(authorization=json.dumps({'access_token': 'abc'}))) == 'abc'
    assert trakt_status.access_token(Settings()) == ''
