# Subtitle helpers
"""Cleanup helpers for external subtitles.

NLZiet's NPO streams publish teletext-derived WebVTT subtitles: the document
opens with the teletext page number (the well known ``888``) and colours the
spoken lines with class tags such as ``<c.yellow>``/``<c.white>``. Kodi renders
those cues literally, so viewers see a stray page number and yellow/white
teletext colours instead of the regular subtitle overlay.

:func:`clean_webvtt` strips those artefacts; :func:`prepare_subtitle_urls`
downloads and cleans the files into a small local cache so Kodi can play them
like any other subtitle file. Everything is best effort: when a download or
conversion fails the original URL is passed through untouched, so subtitle
handling can never block playback.
"""

import hashlib
import os
import re
import time
import urllib.parse
import urllib.request

CACHE_VERSION = 'v1'
DEFAULT_CACHE_MAX_AGE = 60 * 24 * 60 * 60  # 60 days

# <c.yellow>, <c.yellow.bg_blue>, </c> ... (WebVTT class tags)
_COLOR_TAG_RE = re.compile(r'</?c(?:\.[^>\s]+)?>', re.IGNORECASE)
# Teletext page number (Dutch/Belgian subtitle page) shown as its own cue.
_PAGE_NUMBER_RE = re.compile(r'^888$')
# Teletext service banner/footer that broadcasters add to the subtitle page.
_SERVICE_BANNER_RE = re.compile(r'\btt888\b|service\.npo\.nl', re.IGNORECASE)


def _is_teletext_furniture(text):
    stripped = text.strip()
    return bool(_PAGE_NUMBER_RE.match(stripped) or _SERVICE_BANNER_RE.search(stripped))


def clean_webvtt(text):
    """Remove teletext artefacts from a WebVTT document.

    Returns the cleaned document, or ``None`` when the input is not WebVTT or
    did not contain any artefact worth removing (so callers can keep the
    original file untouched).
    """
    if not text or 'WEBVTT' not in text:
        return None

    normalised = text.replace('\r\n', '\n').replace('\r', '\n')
    blocks = re.split(r'\n[ \t]*\n', normalised)
    cleaned_blocks = []
    changed = False

    for block in blocks:
        stripped = block.strip('\n')
        if not stripped.strip():
            continue
        if '-->' not in stripped:
            # Header / STYLE / REGION / NOTE block: keep as-is.
            cleaned_blocks.append(stripped.rstrip())
            continue

        lines = stripped.split('\n')
        timing = next(i for i, line in enumerate(lines) if '-->' in line)
        payload = []
        for line in lines[timing + 1:]:
            cleaned = _COLOR_TAG_RE.sub('', line)
            if cleaned != line:
                changed = True
            if _is_teletext_furniture(cleaned):
                # Teletext page number or service banner, not spoken dialogue.
                changed = True
                continue
            if not cleaned.strip():
                # Line held only markup/whitespace; drop it.
                if line.strip():
                    changed = True
                continue
            payload.append(cleaned)

        if not payload:
            # Cue consisted only of teletext artefacts.
            changed = True
            continue
        cleaned_blocks.append('\n'.join(lines[:timing + 1] + payload).rstrip())

    if not changed:
        return None
    return '\n\n'.join(cleaned_blocks) + '\n'


def prune_cache(cache_dir, max_age=DEFAULT_CACHE_MAX_AGE, log=None):
    """Best-effort removal of stale cached subtitle files."""
    if not cache_dir:
        return
    try:
        now = time.time()
        for name in os.listdir(cache_dir):
            if not name.startswith(CACHE_VERSION + '_'):
                continue
            path = os.path.join(cache_dir, name)
            try:
                if now - os.path.getmtime(path) > max_age:
                    os.remove(path)
            except OSError:
                continue
    except Exception:
        pass


def _is_webvtt_url(url):
    path = urllib.parse.urlparse(url).path.lower()
    return path.endswith('.vtt') or path.endswith('.webvtt')


def _cache_path(cache_dir, url):
    digest = hashlib.sha1(url.encode('utf-8')).hexdigest()[:20]
    return os.path.join(cache_dir, CACHE_VERSION + '_' + digest + '.vtt')


def _download(url, headers=None, timeout=20):
    request = urllib.request.Request(url, headers=dict(headers or {}))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode('utf-8', 'replace')


def prepare_subtitle_urls(urls, cache_dir=None, headers=None, log=None):
    """Return subtitle locations that are ready for playback.

    External WebVTT files that carry teletext artefacts are downloaded, cleaned
    and stored in ``cache_dir``; the local path is returned instead of the URL.
    Any other subtitle (or any failure) is returned unchanged.
    """
    prepared = []
    for url in urls or []:
        if not url:
            continue
        if not cache_dir or not _is_webvtt_url(url):
            prepared.append(url)
            continue
        try:
            os.makedirs(cache_dir, exist_ok=True)
            cached = _cache_path(cache_dir, url)
            if os.path.exists(cached) and os.path.getsize(cached) > 0:
                prepared.append(cached)
                continue
            cleaned = clean_webvtt(_download(url, headers=headers))
            if cleaned is None:
                # Nothing to clean (e.g. RTL subtitles): leave it to Kodi.
                prepared.append(url)
                continue
            with open(cached, 'w', encoding='utf-8') as handle:
                handle.write(cleaned)
            prune_cache(cache_dir, log=log)
            if log:
                log('NLZiet: cleaned teletext subtitles from {0}'.format(url))
            prepared.append(cached)
        except Exception as exc:
            if log:
                log('NLZiet: subtitle cleanup failed for {0}: {1}'.format(url, exc))
            prepared.append(url)
    return prepared
