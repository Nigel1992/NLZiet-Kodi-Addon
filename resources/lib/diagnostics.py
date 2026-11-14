"""One-screen health check for the add-on.

Shows, in plain language, whether the parts playback and the library depend
on are in order: versions, sign-in, InputStream Adaptive, Widevine, the
connection to the service, TMDb/TVmaze, and the Kodi library folders. The
same text (plus a privacy-safe excerpt of the Kodi log) is saved as a report
that can be attached to a bug report.

Shared by the NLZiet and Videoland add-ons; everything add-on specific is
passed in by the caller.
"""

import json
import os
import platform
import re
import sys
import time
import urllib.request

try:
    import xbmc
except ImportError:  # pragma: no cover - outside Kodi
    xbmc = None
try:
    import xbmcaddon
except ImportError:  # pragma: no cover
    xbmcaddon = None
try:
    import xbmcvfs
except ImportError:  # pragma: no cover
    xbmcvfs = None

OK, WARN, FAIL, INFO = 'ok', 'warn', 'fail', 'info'

TEXT = {
    'nl': {
        'title': 'Diagnose', 'ok': 'OK', 'warn': 'Let op', 'fail': 'Probleem', 'info': 'Info',
        'version': 'Versie add-on', 'kodi': 'Kodi', 'system': 'Systeem',
        'login': 'Aangemeld', 'login_yes': 'ja', 'login_no': 'nee: meld je aan via het hoofdmenu',
        'isa': 'InputStream Adaptive', 'isa_missing': 'niet geïnstalleerd of uitgeschakeld: nodig om af te spelen',
        'widevine': 'Widevine (DRM)', 'widevine_android': 'Android gebruikt de Widevine van het systeem',
        'widevine_found': 'gevonden', 'widevine_missing': 'niet gevonden: start een video, InputStream Helper installeert het',
        'net': 'Verbinding met {}', 'net_ok': 'bereikbaar ({} ms)', 'net_fail': 'niet bereikbaar ({})',
        'tmdb': 'TMDb-sleutel', 'tmdb_none': 'niet ingevuld (series werken via TVmaze, films niet)',
        'tmdb_ok': 'werkt', 'tmdb_invalid': 'wordt niet geaccepteerd', 'tmdb_offline': 'niet te testen: TMDb onbereikbaar',
        'watchlist': 'Mijn Kijklijst - {}',
        'watchlist_line': '{} titels geladen, Videoland meldt {}, getoond: {} (blok: {})',
        'lib_kodi': 'In Kodi-bibliotheek', 'lib_in_kodi': '{} van {} series, {} van {} films.',
        'lib_in_kodi_fix': 'Kies Bibliotheek > Bibliotheek nu bijwerken; dan scant Kodi de rest.',
        'lib': 'Bibliotheek', 'lib_count': '{} series, {} films; laatst bijgewerkt: {}', 'never': 'nog nooit',
        'lib_folder': 'Map {}', 'lib_source_ok': 'staat als bron in Kodi', 'lib_source_missing':
            'staat nog niet als bron in Kodi: voeg {} toe via Video\'s > Bestanden > Video\'s toevoegen '
            '(inhoud: Series of Films, scraper: Lokale informatie)',
        'report': 'Rapport opgeslagen in:', 'summary_ok': 'Alles ziet er goed uit.',
        'summary_problems': '{} punt(en) hebben aandacht nodig, zie hieronder.',
    },
    'en': {
        'title': 'Diagnostics', 'ok': 'OK', 'warn': 'Note', 'fail': 'Problem', 'info': 'Info',
        'version': 'Add-on version', 'kodi': 'Kodi', 'system': 'System',
        'login': 'Signed in', 'login_yes': 'yes', 'login_no': 'no: sign in from the main menu',
        'isa': 'InputStream Adaptive', 'isa_missing': 'not installed or disabled: needed for playback',
        'widevine': 'Widevine (DRM)', 'widevine_android': 'Android uses the system Widevine',
        'widevine_found': 'found', 'widevine_missing': 'not found: start a video and InputStream Helper installs it',
        'net': 'Connection to {}', 'net_ok': 'reachable ({} ms)', 'net_fail': 'not reachable ({})',
        'tmdb': 'TMDb key', 'tmdb_none': 'not set (series work through TVmaze, films do not)',
        'tmdb_ok': 'works', 'tmdb_invalid': 'not accepted', 'tmdb_offline': 'could not be tested: TMDb unreachable',
        'watchlist': 'My watchlist - {}',
        'watchlist_line': '{} titles loaded, Videoland reports {}, shown: {} (block: {})',
        'lib_kodi': 'In Kodi library', 'lib_in_kodi': '{} of {} series, {} of {} films.',
        'lib_in_kodi_fix': 'Choose Library > Update library now so Kodi scans the rest.',
        'lib': 'Library', 'lib_count': '{} series, {} films; last updated: {}', 'never': 'never',
        'lib_folder': 'Folder {}', 'lib_source_ok': 'is a Kodi source', 'lib_source_missing':
            'is not a Kodi source yet: add {} via Videos > Files > Add videos '
            '(content: TV shows or Movies, scraper: Local information only)',
        'report': 'Report saved to:', 'summary_ok': 'Everything looks fine.',
        'summary_problems': '{} item(s) need attention, see below.',
    },
}


def texts(language):
    return TEXT['nl' if str(language or '').lower().startswith('nl') else 'en']


def _probe(url, timeout=8):
    """Return (ok, detail). Any HTTP answer means the host is reachable."""
    started = time.time()
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Kodi diagnostics'})
        with urllib.request.urlopen(request, timeout=timeout):
            pass
    except Exception as exc:
        if getattr(exc, 'code', None):
            return True, int((time.time() - started) * 1000)
        reason = getattr(exc, 'reason', exc)
        return False, type(reason).__name__
    return True, int((time.time() - started) * 1000)


def _addon_version(addon_id):
    if xbmcaddon is None:
        return None
    try:
        return xbmcaddon.Addon(addon_id).getAddonInfo('version')
    except Exception:
        return None


def _widevine_state():
    if xbmc is not None and xbmc.getCondVisibility('System.Platform.Android'):
        return 'android'
    if xbmcvfs is None:
        return 'missing'
    cdm = xbmcvfs.translatePath('special://home/cdm')
    try:
        names = os.listdir(cdm)
    except OSError:
        return 'missing'
    return 'found' if any('widevine' in name.lower() for name in names) else 'missing'


def _kodi_sources():
    if xbmc is None:
        return []
    payload = {'jsonrpc': '2.0', 'method': 'Files.GetSources', 'params': {'media': 'video'}, 'id': 1}
    try:
        result = json.loads(xbmc.executeJSONRPC(json.dumps(payload))).get('result') or {}
    except Exception:
        return []
    return [str(source.get('file') or '') for source in result.get('sources') or []]


def _translate(path):
    if xbmcvfs is not None and str(path).startswith('special://'):
        try:
            return xbmcvfs.translatePath(path)
        except Exception:
            pass
    return path


def _is_source(folder, sources, special=None):
    wanted = [str(_translate(p)).replace('\\', '/').rstrip('/').lower() for p in (folder, special) if p]
    wanted += [str(p).replace('\\', '/').rstrip('/').lower() for p in (folder, special) if p]
    for source in sources:
        source = str(_translate(source)).replace('\\', '/').rstrip('/').lower()
        if any(w == source or w.startswith(source + '/') for w in wanted):
            return True
    return False


def run_checks(t, version, signed_in, endpoints, library=None, library_special=None,
               tmdb_status=None, probe=_probe, sources=None, widevine=None, kodi_counts=None):
    """Return a list of (status, label, detail).

    ``endpoints``: [(name, url)]; ``library``: object with ``store``,
    ``tv_root()``, ``movies_root()``; ``library_special``: the default
    special:// folders (tv, movies) as the user sees them in Kodi.
    """
    checks = [(INFO, t['version'], version or '?')]
    kodi_version = xbmc.getInfoLabel('System.BuildVersion') if xbmc is not None else ''
    checks.append((INFO, t['kodi'], kodi_version or '?'))
    checks.append((INFO, t['system'], '{} / Python {}'.format(sys.platform, platform.python_version())))
    checks.append((OK if signed_in else FAIL, t['login'], t['login_yes'] if signed_in else t['login_no']))

    isa = _addon_version('inputstream.adaptive')
    checks.append((OK, t['isa'], isa) if isa else (FAIL, t['isa'], t['isa_missing']))
    state = widevine or _widevine_state()
    checks.append({'android': (OK, t['widevine'], t['widevine_android']),
                   'found': (OK, t['widevine'], t['widevine_found'])}.get(state, (WARN, t['widevine'], t['widevine_missing'])))

    for name, url in endpoints:
        ok, detail = probe(url)
        checks.append((OK, t['net'].format(name), t['net_ok'].format(detail)) if ok
                      else (FAIL, t['net'].format(name), t['net_fail'].format(detail)))

    if tmdb_status is not None:
        status = {'missing': (INFO, t['tmdb_none']), 'ok': (OK, t['tmdb_ok']),
                  'invalid': (FAIL, t['tmdb_invalid']), 'offline': (WARN, t['tmdb_offline'])}[tmdb_status]
        checks.append((status[0], t['tmdb'], status[1]))

    if library is not None:
        store = library.store
        series, movies = len(store.section('series')), len(store.section('movie'))
        last = store.data.get('last_update') or 0
        when = time.strftime('%d-%m-%Y %H:%M', time.localtime(last)) if last else t['never']
        checks.append((INFO, t['lib'], t['lib_count'].format(series, movies, when)))
        if kodi_counts is not None:
            in_kodi = t['lib_in_kodi'].format(kodi_counts[0], series, kodi_counts[1], movies)
            complete = kodi_counts[0] >= series and kodi_counts[1] >= movies
            checks.append((OK if complete else WARN, t['lib_kodi'],
                           in_kodi if complete else in_kodi + ' ' + t['lib_in_kodi_fix']))
        source_list = _kodi_sources() if sources is None else sources
        specials = library_special or (None, None)
        in_kodi = kodi_counts or (0, 0)
        for kind, root, special, count, scanned in (('TV Shows', library.tv_root(), specials[0], series, in_kodi[0]),
                                                    ('Movies', library.movies_root(), specials[1], movies, in_kodi[1])):
            if not count:
                continue
            # Titles from this folder in Kodi's library prove it is a source,
            # however the source was added (parent folder, network path...).
            if scanned or _is_source(root, source_list, special):
                checks.append((OK, t['lib_folder'].format(kind), t['lib_source_ok']))
            else:
                checks.append((WARN, t['lib_folder'].format(kind), t['lib_source_missing'].format(special or root)))
    return checks


def render(t, checks, report_path=None):
    problems = sum(1 for status, _l, _d in checks if status in (WARN, FAIL))
    marks = {OK: '[COLOR green]{}[/COLOR]', WARN: '[COLOR orange]{}[/COLOR]',
             FAIL: '[COLOR red]{}[/COLOR]', INFO: '{}'}
    lines = [t['summary_problems'].format(problems) if problems else t['summary_ok'], '']
    for status, label, detail in checks:
        # The status word is written out, so the colour is never the only signal.
        lines.append('{}  {}: {}'.format(marks[status].format(t[status]), label, detail))
    if report_path:
        lines += ['', t['report'], report_path]
    return '\n'.join(lines)


def plain(text):
    return re.sub(r'\[/?COLOR[^\]]*\]', '', text)


def kodi_log_excerpt(markers, redact, max_lines=200):
    """The last log lines that mention this add-on, with private data removed."""
    if xbmcvfs is None:
        return []
    path = os.path.join(xbmcvfs.translatePath('special://logpath'), 'kodi.log')
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            lines = handle.readlines()
    except OSError:
        return []
    wanted = [line.rstrip('\n') for line in lines if any(m.lower() in line.lower() for m in markers)
              or ' error ' in line.lower()]
    return [redact(line) for line in wanted[-max_lines:]]


def save_report(folder, name, text, log_lines):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, '{}-diagnose-{}.txt'.format(name, time.strftime('%Y%m%d-%H%M%S')))
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(plain(text) + '\n\n--- Kodi log (privacy-safe excerpt) ---\n')
        handle.write('\n'.join(log_lines) + '\n')
    return path


def redact(text):
    """Remove credentials, tokens, cookies, email addresses and signed URL data."""
    text = str(text or '')
    text = re.sub(r'(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,}\]]+', r'\1<redacted>', text)
    text = re.sub(r'(?i)(password|access_token|refresh_token|id_token|uid|signature|cookie|set-cookie|auth_json)'
                  r'(["\'\s]*[:=]["\'\s]*)([^\s,}\]]+)', r'\1\2<redacted>', text)
    text = re.sub(r'(?i)([?&](?:token|sig|signature|code|key|api_key)=)[^&\s]+', r'\1<redacted>', text)
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '<redacted-email>', text)
    text = re.sub(r'\beyJ[A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]+){1,2}\b', '<redacted-jwt>', text)
    return text
