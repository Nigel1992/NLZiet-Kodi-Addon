import socket
import urllib.error

from resources.lib import errors


def http_error(code):
    return urllib.error.HTTPError('https://x.invalid', code, 'err', {}, None)


def test_classify_http_and_network_errors():
    assert errors.classify(http_error(401)) == 'auth'
    assert errors.classify(http_error(403)) == 'forbidden'
    assert errors.classify(http_error(404)) == 'not_found'
    assert errors.classify(http_error(429)) == 'busy'
    assert errors.classify(http_error(503)) == 'server'
    assert errors.classify(urllib.error.URLError(socket.gaierror('dns'))) == 'offline'
    assert errors.classify(socket.timeout('slow')) == 'timeout'
    assert errors.classify(ValueError('bug')) == 'unknown'


def test_wrapped_errors_use_their_cause():
    try:
        try:
            raise http_error(404)
        except urllib.error.HTTPError as inner:
            raise RuntimeError('lookup failed') from inner
    except RuntimeError as outer:
        assert errors.classify(outer) == 'not_found'


def test_messages_in_dutch_and_english():
    assert 'NLZiet' in errors.user_message(http_error(401), 'NLZiet', 'nl')
    assert errors.user_message(http_error(401), 'NLZiet', 'nl').startswith('Je sessie')
    assert errors.user_message(http_error(401), 'NLZiet', 'en').startswith('Your NLZiet session')
