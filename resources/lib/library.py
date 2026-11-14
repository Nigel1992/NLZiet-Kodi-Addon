"""Kodi library integration for NLZiet.

Series and movies the user adds are written as ``.strm`` + ``.nfo`` files so
Kodi's video library (and skin widgets) can show them. Added titles are
remembered in ``library.json`` in the addon profile, so a background update
can add new episodes and remove episodes that are no longer available.

Episode numbers are assigned once and stored per episode id. That keeps file
names stable between updates, so Kodi keeps watched status and resume points
even when older episodes expire or NLZiet changes its own numbering.
"""

import json
import os
import re
import shutil
import time
import urllib.parse
from xml.sax.saxutils import escape

from . import library_art, metadata

try:
    import xbmc
except ImportError:  # pragma: no cover - only outside Kodi
    xbmc = None

try:
    import xbmcvfs
except ImportError:  # pragma: no cover - only outside Kodi
    xbmcvfs = None


ADDON_ID = 'plugin.video.nlziet'
DEFAULT_TV_PATH = 'special://profile/addon_data/{}/library/TV Shows'.format(ADDON_ID)
DEFAULT_MOVIES_PATH = 'special://profile/addon_data/{}/library/Movies'.format(ADDON_ID)
# Default used by versions up to 1.6.4. Files found there are moved once into
# the add-on's own data folder (see Library.migrate_legacy_folder).
LEGACY_ROOT = '/storage/emulated/0/KodiNLZietLibrary'
LEGACY_TV_PATH = LEGACY_ROOT + '/TV Shows'

STORE_VERSION = 1
UNDATED = '9999-12-31'


def _log(message, level=None):
    if xbmc is None:
        return
    try:
        xbmc.log('NLZiet library: {}'.format(message), xbmc.LOGINFO if level is None else level)
    except Exception:
        pass


def translate_path(path):
    if not path:
        return path
    if xbmcvfs is not None and str(path).startswith('special://'):
        try:
            return xbmcvfs.translatePath(path)
        except Exception:
            pass
    return path


def safe_filename(value):
    value = re.sub(r'[\\/:*?"<>|]+', ' ', str(value or '')).strip()
    value = re.sub(r'\s+', ' ', value).strip(' .')
    return value or 'NLZiet'


def _date_only(value):
    if not value:
        return None
    try:
        text = str(value)
        match = re.match(r'^(\d{4}-\d{2}-\d{2})', text)
        if match:
            return match.group(1)
        if text.isdigit() and len(text) >= 10:
            return time.strftime('%Y-%m-%d', time.gmtime(int(text[:10])))
    except Exception:
        pass
    return None


def _int_or_none(value):
    try:
        if value is None or isinstance(value, bool):
            return None
        match = re.search(r'\d+', str(value))
        return int(match.group(0)) if match else None
    except Exception:
        return None


def episode_airdate(ep):
    raw = ep.get('raw') if isinstance(ep.get('raw'), dict) else {}
    for value in (
        ep.get('aired_date'), raw.get('firstBroadcast'), raw.get('broadcastAt'),
        raw.get('broadcastDate'), ep.get('release_date'), ep.get('available_from'),
    ):
        date_value = _date_only(value)
        if date_value:
            return date_value
    return None


def _image(item, *keys):
    if not isinstance(item, dict):
        return None
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.startswith(('http://', 'https://')):
            return value
        if isinstance(value, dict):
            nested = _image(value, 'portraitUrl', 'posterUrl', 'landscapeUrl', 'url')
            if nested:
                return nested
    return None


class LocalFS:
    """Small file helper: plain ``os`` for local paths, ``xbmcvfs`` for
    network paths such as ``smb://`` or ``nfs://``."""

    @staticmethod
    def _remote(path):
        return '://' in str(path) and xbmcvfs is not None

    def join(self, *parts):
        if self._remote(parts[0]):
            return '/'.join([str(parts[0]).rstrip('/')] + [str(p).strip('/') for p in parts[1:]])
        return os.path.join(*parts)

    def exists(self, path):
        if self._remote(path):
            return bool(xbmcvfs.exists(path))
        return os.path.exists(path)

    def read(self, path):
        try:
            if self._remote(path):
                f = xbmcvfs.File(path)
                try:
                    return f.read()
                finally:
                    f.close()
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

    def write(self, path, text):
        """Write ``text``; skip when unchanged so Kodi does not rescan."""
        if self.read(path) == text:
            return False
        folder = path.rsplit('/', 1)[0] if self._remote(path) else os.path.dirname(path)
        if self._remote(path):
            xbmcvfs.mkdirs(folder + '/')
            f = xbmcvfs.File(path, 'w')
            try:
                f.write(text)
            finally:
                f.close()
        else:
            os.makedirs(folder, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
        return True

    def delete(self, path):
        try:
            if self._remote(path):
                return bool(xbmcvfs.delete(path))
            os.remove(path)
            return True
        except Exception:
            return False

    def walk_files(self, folder):
        """Yield file paths under ``folder`` (recursive)."""
        if self._remote(folder):
            dirs, files = xbmcvfs.listdir(folder.rstrip('/') + '/')
            for name in files:
                yield self.join(folder, name)
            for name in dirs:
                for path in self.walk_files(self.join(folder, name)):
                    yield path
            return
        if not os.path.isdir(folder):
            return
        for root, _dirs, files in os.walk(folder):
            for name in files:
                yield os.path.join(root, name)

    def remove_empty_dirs(self, folder):
        if self._remote(folder):
            dirs, files = xbmcvfs.listdir(folder.rstrip('/') + '/')
            for name in dirs:
                self.remove_empty_dirs(self.join(folder, name))
            dirs, files = xbmcvfs.listdir(folder.rstrip('/') + '/')
            if not dirs and not files:
                xbmcvfs.rmdir(folder.rstrip('/') + '/')
            return
        if not os.path.isdir(folder):
            return
        for root, dirs, files in os.walk(folder, topdown=False):
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                except OSError:
                    pass

    def remove_tree(self, folder):
        for path in list(self.walk_files(folder)):
            self.delete(path)
        self.remove_empty_dirs(folder)


class LibraryStore:
    """Remembers which series and movies are in the library."""

    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _empty(self):
        return {'version': STORE_VERSION, 'series': {}, 'movies': {}, 'last_update': 0}

    def _load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return self._empty()
        except Exception:
            return self._empty()
        base = self._empty()
        base.update(data)
        for key in ('series', 'movies'):
            if not isinstance(base.get(key), dict):
                base[key] = {}
        return base

    def save(self):
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    def section(self, kind):
        return self.data['series' if kind == 'series' else 'movies']

    def get(self, kind, item_id):
        return self.section(kind).get(str(item_id))

    def has(self, kind, item_id):
        return str(item_id) in self.section(kind)


class Library:
    def __init__(self, api, addon, episode_fetcher, store=None, fs=None, now=None, enricher=None,
                 downloader=None, art_picker=None):
        """``art_picker(item)`` returns ``(poster_url, fanart_url)`` for an API item;
        ``downloader(url)`` returns image bytes (None: keep artwork as URLs)."""
        self.enricher = enricher
        self.downloader = downloader
        self.art_picker = art_picker
        self.api = api
        self.addon = addon
        self.episode_fetcher = episode_fetcher
        self.fs = fs or LocalFS()
        self.now = now or time.time
        if store is None:
            profile = translate_path(addon.getAddonInfo('profile')) or ''
            store = LibraryStore(os.path.join(profile, 'library.json'))
        self.store = store

    # ------------------------------------------------------------------ paths
    def _setting(self, key):
        try:
            return (self.addon.getSetting(key) or '').strip()
        except Exception:
            return ''

    def tv_root(self):
        value = self._setting('library_path')
        if not value or value.rstrip('/') == LEGACY_TV_PATH:
            value = DEFAULT_TV_PATH
        return translate_path(value)

    def migrate_legacy_folder(self, legacy_root=LEGACY_ROOT):
        """Move series exported by 1.6.x out of KodiNLZietLibrary into the
        add-on's own folder. Returns the number of moved show folders."""
        if self._setting('library_path').rstrip('/') == LEGACY_TV_PATH:
            try:
                self.addon.setSetting('library_path', DEFAULT_TV_PATH)
            except Exception:
                pass
        source = os.path.join(legacy_root, 'TV Shows')
        if not os.path.isdir(source):
            return 0
        target = self.tv_root()
        if '://' in str(target) or os.path.normcase(os.path.abspath(target)) == os.path.normcase(os.path.abspath(source)):
            return 0
        moved = 0
        for name in sorted(os.listdir(source)):
            src = os.path.join(source, name)
            dst = os.path.join(target, name)
            try:
                if os.path.isdir(src):
                    self._merge_move(src, dst)
                    moved += 1
                else:
                    os.makedirs(target, exist_ok=True)
                    shutil.move(src, dst)
            except Exception as exc:
                _log('could not move {}: {}'.format(src, exc))
        for folder in (source, legacy_root):
            try:
                if os.path.isdir(folder) and not os.listdir(folder):
                    os.rmdir(folder)
            except OSError:
                pass
        if moved:
            _log('moved {} series from {} to {}'.format(moved, source, target))
        return moved

    @staticmethod
    def _merge_move(src, dst):
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            return
        for root, _dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            out = os.path.join(dst, rel) if rel != '.' else dst
            os.makedirs(out, exist_ok=True)
            for name in files:
                target = os.path.join(out, name)
                if os.path.exists(target):
                    os.remove(os.path.join(root, name))  # the new folder wins
                else:
                    shutil.move(os.path.join(root, name), target)
        shutil.rmtree(src, ignore_errors=True)

    def movies_root(self):
        return translate_path(self._setting('library_movies_path') or DEFAULT_MOVIES_PATH)

    def plugin_url(self, query):
        addon_id = ADDON_ID
        try:
            addon_id = self.addon.getAddonInfo('id') or ADDON_ID
        except Exception:
            pass
        return 'plugin://{}/?{}'.format(addon_id, urllib.parse.urlencode(query))

    # ------------------------------------------------------------------ state
    def is_in_library(self, kind, item_id):
        return bool(item_id) and self.store.has(kind, item_id)

    def items(self, kind):
        """Return ``[(id, entry)]`` sorted by title."""
        section = self.store.section(kind)
        return sorted(section.items(), key=lambda kv: str(kv[1].get('title') or '').lower())

    # ----------------------------------------------------------------- series
    def add_series(self, series_id, title=None, poster=None, fanart=None):
        """Add (or refresh) a series. ``poster``/``fanart`` come from the list
        item the user picked and are used when the detail page has none."""
        self._remember_hints('series', series_id, poster, fanart)
        return self._sync_series(str(series_id), title=title, is_update=False)

    def _remember_hints(self, kind, item_id, poster, fanart):
        if not (poster or fanart):
            return
        section = self.store.section(kind)
        entry = section.setdefault(str(item_id), {}) if str(item_id) in section else None
        hints = {'poster_hint': poster or '', 'fanart_hint': fanart or ''}
        if entry is not None:
            entry.update({k: v for k, v in hints.items() if v})
        else:
            self._pending_hints = getattr(self, '_pending_hints', {})
            self._pending_hints[(kind, str(item_id))] = hints

    def _hints(self, kind, item_id, entry):
        pending = getattr(self, '_pending_hints', {}).pop((kind, str(item_id)), {})
        for key, value in pending.items():
            if value:
                entry[key] = value
        return entry.get('poster_hint') or '', entry.get('fanart_hint') or ''

    def _pick_art(self, item):
        if self.art_picker is not None:
            try:
                poster, fanart = self.art_picker(item or {})
                return poster or '', fanart or ''
            except Exception:
                pass
        return '', ''

    def _numbering_mode(self, episodes):
        numbered = [ep for ep in episodes if _int_or_none(ep.get('season_number')) is not None
                    and _int_or_none(ep.get('episode_number')) is not None]
        return 'api' if episodes and len(numbered) == len(episodes) else 'date'

    def _assign_numbers(self, entry, episodes):
        """Give every episode a stable (season, episode) pair."""
        mapping = entry.setdefault('episodes', {})
        mode = entry.get('numbering') or self._numbering_mode(episodes)
        entry['numbering'] = mode
        taken = {(v[0], v[1]) for v in mapping.values() if isinstance(v, (list, tuple)) and len(v) == 2}

        def next_free(season, wanted=None):
            if wanted is not None and wanted > 0 and (season, wanted) not in taken:
                return wanted
            used = [e for (s, e) in taken if s == season]
            number = (max(used) if used else 0) + 1
            while (season, number) in taken:
                number += 1
            return number

        dated = []
        for ep in episodes:
            airdate = episode_airdate(ep) or UNDATED
            dated.append((airdate, str(ep.get('title') or ep.get('subtitle') or ''), ep))
        dated.sort(key=lambda item: (item[0], item[1]))

        result = []
        for airdate, _title, ep in dated:
            ep_id = str(ep.get('id') or '')
            if not ep_id:
                continue
            existing = mapping.get(ep_id)
            if isinstance(existing, (list, tuple)) and len(existing) == 2:
                result.append((ep, int(existing[0]), int(existing[1]), airdate))
                continue
            api_season = _int_or_none(ep.get('season_number'))
            api_episode = _int_or_none(ep.get('episode_number'))
            if mode == 'api' and api_season is not None:
                season = api_season
                number = next_free(season, api_episode)
            elif airdate != UNDATED:
                season = int(airdate[:4])
                number = next_free(season)
            else:
                season = api_season if api_season is not None else 1
                number = next_free(season, api_episode)
            taken.add((season, number))
            mapping[ep_id] = [season, number]
            result.append((ep, season, number, airdate))
        return result

    def _show_folder(self, entry, title):
        folder = entry.get('folder')
        if not folder:
            folder = safe_filename(title)
            entry['folder'] = folder
        return self.fs.join(self.tv_root(), folder)

    def _sync_series(self, series_id, title=None, is_update=False):
        result = {'kind': 'series', 'id': series_id, 'added': 0, 'removed': 0, 'total': 0, 'ok': False}
        section = self.store.section('series')
        entry = dict(section.get(series_id) or {})
        detail = self.api.get_series_detail(series_id) or {}
        series_title = detail.get('title') or entry.get('title') or title or series_id
        episodes = [ep for ep in (self.episode_fetcher(self.api, series_id, detail) or []) if ep.get('id')]
        if not episodes:
            # Never delete files because of a failed or empty API answer.
            result['reason'] = 'no_episodes'
            if is_update and series_id in section:
                entry['last_checked'] = int(self.now())
                section[series_id] = entry
            return result

        entry['title'] = series_title
        entry.setdefault('added', int(self.now()))
        hint_poster, hint_fanart = self._hints('series', series_id, entry)
        picked_poster, picked_fanart = self._pick_art(detail.get('raw') or detail)
        thumb = (picked_poster or detail.get('thumb') or hint_poster
                 or _image(detail.get('raw') or {}, 'posterUrl', 'image'))
        show_data = {
            'plot': detail.get('description') or '',
            'poster': thumb or '',
            'fanart': (picked_fanart or hint_fanart
                       or _image(detail.get('raw') or {}, 'backdropUrl', 'landscapeUrl', 'heroUrl') or ''),
        }
        show_data = self._enrich_show(entry, series_title, show_data)
        if show_data.get('poster'):
            entry['thumb'] = show_data['poster']
        show_dir = self._show_folder(entry, series_title)

        self.fs.write(self.fs.join(show_dir, 'tvshow.nfo'), self._tvshow_nfo(series_id, series_title, show_data))
        _saved = library_art.save_art(self, entry, show_dir,
                                      {k: show_data.get(k) for k in ('poster', 'fanart', 'clearlogo')},
                                      library_art.art_names('series', entry['folder']), self.downloader)
        entry['clearlogo'] = _saved.get('clearlogo') or show_data.get('clearlogo') or ''

        wanted = set()
        seasons_used = set()
        for ep, season, number, airdate in self._assign_numbers(entry, episodes):
            seasons_used.add(season)
            ep_title = ep.get('subtitle') or ep.get('title') or 'Episode {}'.format(number)
            base = '{} S{:02d}E{:02d}'.format(safe_filename(entry['folder']), season, number)
            season_dir = self.fs.join(show_dir, 'Season {}'.format(season))
            strm_path = self.fs.join(season_dir, base + '.strm')
            nfo_path = self.fs.join(season_dir, base + '.nfo')
            wanted.add(os.path.normcase(strm_path))
            wanted.add(os.path.normcase(nfo_path))
            query = {
                'mode': 'play',
                'id': ep.get('id'),
                'media_type': 'episode',
                'title': ep_title,
                'showtitle': series_title,
                'season': str(season),
                'episode': str(number),
            }
            if self.fs.write(strm_path, self.plugin_url(query) + '\n'):
                result['added'] += 1
            ep_data = {
                'title': ep_title,
                'plot': ep.get('description') or '',
                'thumb': ep.get('thumb') or _image(ep, 'posterUrl', 'image') or '',
                'aired': '' if airdate == UNDATED else airdate,
            }
            ep_data = self._enrich_episode(entry, ep_data, season, number)
            self.fs.write(nfo_path, self._episode_nfo(ep, ep_data, series_title, season, number))

        # Remove episodes that are no longer offered (and old export files).
        for path in list(self.fs.walk_files(show_dir)):
            name = os.path.basename(path).lower()
            if name == 'tvshow.nfo' or not name.endswith(('.strm', '.nfo')):
                continue
            if os.path.normcase(path) not in wanted:
                if self.fs.delete(path) and name.endswith('.strm'):
                    result['removed'] += 1
        self.fs.remove_empty_dirs(show_dir)

        library_art.save_season_posters(self, entry, show_dir, show_data.get('season_posters'),
                                        seasons_used, self.downloader)
        self._save_metadata()
        entry['updated'] = int(self.now())
        entry['last_checked'] = int(self.now())
        entry['episode_count'] = len(episodes)
        section[series_id] = entry
        result.update({'ok': True, 'total': len(episodes), 'title': series_title})
        return result

    # --------------------------------------------------------------- metadata
    def _enrich_show(self, entry, title, local):
        if self.enricher is None:
            return local
        try:
            extra = self.enricher.show(title, known=entry.get('ids'))
        except Exception as exc:
            _log('metadata lookup failed for {}: {}'.format(title, exc))
            return local
        ids = {k: str(v) for k, v in (extra.get('ids') or {}).items() if v}
        if ids:
            entry['ids'] = ids
        return metadata.merge(local, extra)

    def _enrich_episode(self, entry, local, season, number):
        if self.enricher is None or not entry.get('ids'):
            return local
        try:
            extra = self.enricher.episode(entry['ids'], season, number, local.get('aired') or None,
                                          by_number=entry.get('numbering') == 'api')
        except Exception:
            return local
        return metadata.merge(local, extra)

    def _save_metadata(self):
        if self.enricher is not None:
            try:
                self.enricher.save()
            except Exception:
                pass

    def _tvshow_nfo(self, series_id, title, data):
        parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<tvshow>',
                 '  <title>{}</title>'.format(escape(title)),
                 '  <plot>{}</plot>'.format(escape(data.get('plot') or '')),
                 '  <uniqueid type="nlziet" default="true">{}</uniqueid>'.format(escape(str(series_id)))]
        if data.get('year'):
            parts.append('  <year>{}</year>'.format(data['year']))
        if data.get('poster'):
            parts.append('  <thumb aspect="poster">{}</thumb>'.format(escape(data['poster'])))
        if data.get('fanart'):
            parts.append('  <fanart><thumb>{}</thumb></fanart>'.format(escape(data['fanart'])))
        parts += metadata.nfo_extra_lines(data, escape)
        parts.append('</tvshow>')
        return '\n'.join(parts) + '\n'

    def _episode_nfo(self, ep, data, series_title, season, number):
        parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<episodedetails>',
                 '  <title>{}</title>'.format(escape(data.get('title') or 'Episode {}'.format(number))),
                 '  <showtitle>{}</showtitle>'.format(escape(series_title)),
                 '  <season>{}</season>'.format(season),
                 '  <episode>{}</episode>'.format(number),
                 '  <aired>{}</aired>'.format(escape(data.get('aired') or '')),
                 '  <plot>{}</plot>'.format(escape(data.get('plot') or '')),
                 '  <uniqueid type="nlziet" default="true">{}</uniqueid>'.format(escape(str(ep.get('id'))))]
        duration = _int_or_none(ep.get('duration'))
        if duration:
            minutes = duration // 60 if duration > 600 else duration
            parts.append('  <runtime>{}</runtime>'.format(minutes))
        if data.get('thumb'):
            parts.append('  <thumb>{}</thumb>'.format(escape(data['thumb'])))
        parts.append('</episodedetails>')
        return '\n'.join(parts) + '\n'

    # ----------------------------------------------------------------- movies
    def add_movie(self, movie_id, title=None, item=None, poster=None, fanart=None):
        self._remember_hints('movie', movie_id, poster, fanart)
        return self._sync_movie(str(movie_id), title=title, item=item, is_update=False)

    def _sync_movie(self, movie_id, title=None, item=None, is_update=False):
        result = {'kind': 'movie', 'id': movie_id, 'added': 0, 'removed': 0, 'total': 0, 'ok': False}
        section = self.store.section('movie')
        entry = dict(section.get(movie_id) or {})
        detail = {}
        try:
            detail = self.api.get_content_detail(movie_id) or {}
        except Exception as exc:
            _log('movie detail failed for {}: {}'.format(movie_id, exc))
        item = item or {}
        movie_title = detail.get('title') or entry.get('title') or title or item.get('title')
        if not movie_title:
            result['reason'] = 'no_detail'
            return result

        expires_at = detail.get('expires_at') or item.get('expires_at')
        if is_update and expires_at and _int_or_none(expires_at) and _int_or_none(expires_at) < self.now():
            removed = self.remove('movie', movie_id, save=False)
            result.update({'removed': 1 if removed else 0, 'ok': True, 'reason': 'expired'})
            return result

        raw = detail.get('raw') if isinstance(detail.get('raw'), dict) else {}
        year = _int_or_none(item.get('year') or entry.get('year') or raw.get('year')
                            or raw.get('releaseYear') or raw.get('productionYear'))
        if year and not 1900 <= year <= 2100:
            year = None
        hint_poster, hint_fanart = self._hints('movie', movie_id, entry)
        picked_poster, picked_fanart = self._pick_art(raw or detail)
        movie_data = {
            'plot': detail.get('description') or item.get('description') or '',
            'poster': (picked_poster or detail.get('thumb') or item.get('thumb') or item.get('posterUrl')
                       or hint_poster or ''),
            'fanart': picked_fanart or hint_fanart or '',
            'year': year,
        }
        if self.enricher is not None:
            try:
                extra = self.enricher.movie(movie_title, year, known=entry.get('ids'))
                ids = {k: str(v) for k, v in (extra.get('ids') or {}).items() if v}
                if ids:
                    entry['ids'] = ids
                movie_data = metadata.merge(movie_data, extra)
            except Exception as exc:
                _log('metadata lookup failed for {}: {}'.format(movie_title, exc))
            self._save_metadata()
        year = _int_or_none(movie_data.get('year'))
        if not entry.get('folder'):
            entry['folder'] = safe_filename('{} ({})'.format(movie_title, year) if year else movie_title)
        movie_dir = self.fs.join(self.movies_root(), entry['folder'])
        base = self.fs.join(movie_dir, entry['folder'])
        query = {'mode': 'play', 'id': movie_id, 'media_type': 'movie', 'title': movie_title}
        if year:
            query['year'] = str(year)
        if self.fs.write(base + '.strm', self.plugin_url(query) + '\n'):
            result['added'] = 1
        thumb = movie_data.get('poster')
        self.fs.write(base + '.nfo', self._movie_nfo(movie_id, movie_title, movie_data, year))
        _saved = library_art.save_art(self, entry, movie_dir,
                                      {k: movie_data.get(k) for k in ('poster', 'fanart', 'clearlogo')},
                                      library_art.art_names('movie', entry['folder']), self.downloader)
        entry['clearlogo'] = _saved.get('clearlogo') or movie_data.get('clearlogo') or ''

        entry.update({'title': movie_title, 'updated': int(self.now()), 'last_checked': int(self.now())})
        entry.setdefault('added', int(self.now()))
        if year:
            entry['year'] = year
        if thumb:
            entry['thumb'] = thumb
        section[movie_id] = entry
        result.update({'ok': True, 'total': 1, 'title': movie_title})
        return result

    def _movie_nfo(self, movie_id, title, data, year):
        parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<movie>',
                 '  <title>{}</title>'.format(escape(title)),
                 '  <plot>{}</plot>'.format(escape(data.get('plot') or '')),
                 '  <uniqueid type="nlziet" default="true">{}</uniqueid>'.format(escape(str(movie_id)))]
        if year:
            parts.append('  <year>{}</year>'.format(year))
        if data.get('poster'):
            parts.append('  <thumb aspect="poster">{}</thumb>'.format(escape(data['poster'])))
        if data.get('fanart'):
            parts.append('  <fanart><thumb>{}</thumb></fanart>'.format(escape(data['fanart'])))
        parts += metadata.nfo_extra_lines(data, escape, kind='movie')
        parts.append('</movie>')
        return '\n'.join(parts) + '\n'

    # ----------------------------------------------------------------- common
    def remove(self, kind, item_id, save=True):
        kind = 'series' if kind == 'series' else 'movie'
        section = self.store.section(kind)
        entry = section.pop(str(item_id), None)
        if entry is None:
            return False
        folder = entry.get('folder')
        if folder:
            root = self.tv_root() if kind == 'series' else self.movies_root()
            self.fs.remove_tree(self.fs.join(root, folder))
        if save:
            self.store.save()
        return True

    def update_all(self, progress=None):
        """Refresh every series and movie. Returns totals."""
        totals = {'added': 0, 'removed': 0, 'failed': 0, 'checked': 0}
        jobs = [('series', sid) for sid, _ in self.items('series')] + \
               [('movie', mid) for mid, _ in self.items('movie')]
        for index, (kind, item_id) in enumerate(jobs):
            if progress is not None:
                try:
                    if progress(index, len(jobs), kind, item_id) is False:
                        break
                except Exception:
                    pass
            try:
                if kind == 'series':
                    res = self._sync_series(item_id, is_update=True)
                else:
                    res = self._sync_movie(item_id, is_update=True)
            except Exception as exc:
                _log('update failed for {} {}: {}'.format(kind, item_id, exc),
                     getattr(xbmc, 'LOGWARNING', None) if xbmc else None)
                totals['failed'] += 1
                continue
            totals['checked'] += 1
            totals['added'] += res.get('added', 0)
            totals['removed'] += res.get('removed', 0)
            if not res.get('ok'):
                totals['failed'] += 1
        self.store.data['last_update'] = int(self.now())
        self.store.save()
        return totals

    def update_due(self, hours):
        try:
            hours = float(hours)
        except (TypeError, ValueError):
            return False
        if hours <= 0:
            return False
        last = self.store.data.get('last_update') or 0
        return (self.now() - last) >= hours * 3600


def scan_flag_path():
    return os.path.join(translate_path("special://profile/addon_data/plugin.video.nlziet") or "", "scan_pending.json")


def run_library_jobs(scan=True, clean=False):
    """Ask Kodi to clean and/or scan the video library without dialogs. When
    Kodi is already scanning, the request waits until that scan is done."""
    library_art.request_scan(scan_flag_path(), scan=scan, clean=clean)
