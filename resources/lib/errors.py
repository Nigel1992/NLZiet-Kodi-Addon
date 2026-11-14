"""Turn unexpected errors into short, clear messages for the user.

The full technical details always go to the Kodi log; the user sees one
sentence that says what happened and what to do next.
"""

import socket
import ssl
import traceback
import urllib.error

MESSAGES = {
    'nl': {
        'offline': 'Geen verbinding met {service}. Controleer je internet en probeer het opnieuw.',
        'timeout': '{service} reageert niet op tijd. Probeer het zo opnieuw.',
        'auth': 'Je sessie bij {service} is verlopen. Log opnieuw in via het hoofdmenu.',
        'forbidden': 'Dit valt niet onder je {service}-abonnement of is in jouw land niet beschikbaar.',
        'not_found': 'Dit is niet (meer) beschikbaar bij {service}.',
        'busy': 'Te veel verzoeken naar {service}. Wacht even en probeer het opnieuw.',
        'server': '{service} heeft op dit moment een storing. Probeer het later opnieuw.',
        'unknown': 'Er ging iets mis. Maak via Instellingen een diagnoserapport als het blijft gebeuren.',
    },
    'en': {
        'offline': 'No connection to {service}. Check your internet connection and try again.',
        'timeout': '{service} did not respond in time. Please try again shortly.',
        'auth': 'Your {service} session has expired. Please sign in again from the main menu.',
        'forbidden': 'This is not part of your {service} subscription or not available in your country.',
        'not_found': 'This is no longer available on {service}.',
        'busy': 'Too many requests to {service}. Please wait a moment and try again.',
        'server': '{service} is having problems right now. Please try again later.',
        'unknown': 'Something went wrong. Create a diagnostics report from the settings if it keeps happening.',
    },
}


def _http_status(exc):
    for candidate in (exc, getattr(exc, '__cause__', None), getattr(exc, '__context__', None)):
        code = getattr(candidate, 'code', None) or getattr(candidate, 'status', None)
        if code is None:
            response = getattr(candidate, 'response', None)
            code = getattr(response, 'status_code', None)
        if isinstance(code, int):
            return code
    return None


def classify(exc):
    """Return a message key for an exception."""
    status = _http_status(exc)
    if status in (401, 498):
        return 'auth'
    if status in (403, 451):
        return 'forbidden'
    if status in (404, 410):
        return 'not_found'
    if status == 429:
        return 'busy'
    if isinstance(status, int) and status >= 500:
        return 'server'
    chain = [exc, getattr(exc, '__cause__', None), getattr(exc, '__context__', None)]
    reason = getattr(exc, 'reason', None)
    if reason is not None:
        chain.append(reason)
    for item in chain:
        if isinstance(item, (socket.timeout, TimeoutError)):
            return 'timeout'
        if isinstance(item, (urllib.error.URLError, ConnectionError, socket.gaierror, ssl.SSLError, OSError)) \
                and not isinstance(item, (FileNotFoundError, PermissionError)):
            return 'offline'
        name = type(item).__name__ if item is not None else ''
        if name in ('ConnectionError', 'ConnectTimeout', 'ReadTimeout', 'Timeout'):
            return 'timeout' if 'Timeout' in name else 'offline'
    return 'unknown'


def user_message(exc, service, language='nl'):
    table = MESSAGES['nl' if str(language or '').lower().startswith('nl') else 'en']
    return table[classify(exc)].format(service=service)


def log_text(exc):
    return ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
