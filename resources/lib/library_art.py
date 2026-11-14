"""Artwork for library titles: local image files plus a Kodi database repair.

Kodi does not always take artwork URLs from ``.nfo`` files, but it always
uses image files next to the title. So posters and backgrounds are
downloaded once as ``poster.jpg`` / ``fanart.jpg`` (series) and
``<name>-poster.jpg`` / ``<name>-fanart.jpg`` (films).

Titles Kodi scanned before their artwork existed keep an empty poster.
``repair_kodi_art`` fills those in through JSON-RPC; it runs after every
library update and whenever Kodi finishes a video library scan.

Shared by the NLZiet and Videoland add-ons: it only needs a library object
with ``tv_root()``, ``movies_root()``, ``store.section(kind)`` and ``fs``.
"""

import json
import os
import urllib.parse
import urllib.request

try:
    import xbmc
except ImportError:  # pragma: no cover - outside Kodi
    xbmc = None

TIMEOUT = 15
MAX_BYTES = 15 * 1024 * 1024


def http_download(url, user_agent="Kodi"):
    """Return the image bytes at ``url`` or None."""
    if not url or not str(url).startswith(("http://", "https://")):
        return None
    request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "image/*"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            kind = response.headers.get("Content-Type", "")
            if kind and not kind.startswith("image/"):
                return None
            data = response.read(MAX_BYTES + 1)
    except Exception:
        return None
    if not data or len(data) > MAX_BYTES:
        return None
    return data


def _write_bytes(fs, path, data):
    remote = getattr(fs, "_remote", lambda _p: False)(path)
    if remote:
        import xbmcvfs
        xbmcvfs.mkdirs(path.rsplit("/", 1)[0] + "/")
        handle = xbmcvfs.File(path, "wb")
        try:
            handle.write(bytearray(data))
        finally:
            handle.close()
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".part"
    with open(temporary, "wb") as handle:
        handle.write(data)
    os.replace(temporary, path)


def _exists(fs, path):
    remote = getattr(fs, "_remote", lambda _p: False)(path)
    if remote:
        import xbmcvfs
        return bool(xbmcvfs.exists(path))
    return os.path.isfile(path)


def save_art(library, entry, folder, urls, names, downloader):
    """Download each art url once into ``folder``. Returns the saved paths."""
    saved = {}
    if downloader is None:
        return saved
    known = entry.setdefault("art_urls", {})
    for kind, url in urls.items():
        if not url or kind not in names:
            continue
        path = library.fs.join(folder, names[kind])
        if known.get(kind) == url and _exists(library.fs, path):
            saved[kind] = path
            continue
        try:
            data = downloader(url)
        except Exception:
            data = None
        if not data:
            continue
        try:
            _write_bytes(library.fs, path, data)
        except Exception:
            continue
        if known.get(kind) and known[kind] != url:
            remember_owned(entry, known[kind])
        known[kind] = url
        saved[kind] = path
    return saved


def remember_owned(entry, value):
    """Artwork the add-on itself provided earlier: it may be replaced later."""
    if value:
        history = entry.setdefault("art_history", [])
        if value not in history:
            history.append(value)
            del history[:-30]


def art_names(kind, folder):
    """File names Kodi picks up as local artwork."""
    if kind == "series":
        return {"poster": "poster.jpg", "fanart": "fanart.jpg", "clearlogo": "clearlogo.png"}
    return {"poster": folder + "-poster.jpg", "fanart": folder + "-fanart.jpg",
            "clearlogo": folder + "-clearlogo.png"}


def season_poster_name(season):
    """Kodi's local file name for a season poster."""
    season = int(season)
    return "season-specials-poster.jpg" if season == 0 else "season{:02d}-poster.jpg".format(season)


def save_season_posters(library, entry, show_dir, posters, seasons, downloader):
    """Download the poster of every season the library has, once.
    ``posters``: {"1": url, ...} (TMDb numbering); ``seasons``: our season numbers."""
    saved = dict(entry.get("season_art") or {})
    if not posters or downloader is None:
        return saved
    wanted = {str(int(s)) for s in seasons if str(s).lstrip("-").isdigit()}
    urls = {key: url for key, url in posters.items() if key in wanted and url}
    if not urls:
        return saved
    names = {"season" + key: season_poster_name(key) for key in urls}
    result = save_art(library, entry, show_dir, {"season" + key: url for key, url in urls.items()},
                      names, downloader)
    for key, path in result.items():
        saved[key[len("season"):]] = path
    entry["season_art"] = saved
    return saved


def logo_index(store):
    """{(kind, id): clearlogo path or url} for titles in the library."""
    index = {}
    for kind in ("series", "movie"):
        for item_id, entry in store.section(kind).items():
            logo = entry.get("clearlogo")
            if logo:
                index[(kind, str(item_id))] = logo
    return index


def local_art(library, kind, entry):
    """Paths (or urls) of the artwork for a library entry."""
    folder = entry.get("folder")
    if not folder:
        return {}
    art = {}
    if kind == "series":
        base = library.fs.join(library.tv_root(), folder)
    else:
        base = library.fs.join(library.movies_root(), folder)
    names = art_names(kind, folder)
    urls = entry.get("art_urls") or {}
    # Prefer the image url: when a better image arrives it has a new url, so
    # Kodi shows it at once (a rewritten poster.jpg keeps its cached old copy).
    for key in ("poster", "fanart", "clearlogo"):
        if urls.get(key):
            art[key] = urls[key]
    for key, name in names.items():
        path = library.fs.join(base, name)
        if key not in art and _exists(library.fs, path):
            art[key] = path
    if "poster" not in art and entry.get("thumb"):
        art["poster"] = entry["thumb"]
    return art


def _rpc(method, params, rpc=None):
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    if rpc is not None:
        return rpc(payload)
    if xbmc is None:
        return {}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
    except Exception:
        return {}


def _kodi_art_value(value):
    """Kodi returns art as image://<quoted url>/; give back the plain url/path."""
    value = str(value or "")
    if value.startswith("image://"):
        value = urllib.parse.unquote(value[len("image://"):].rstrip("/"))
    return value


def _owned(library, kind, entry, value):
    """True when the artwork Kodi has now came from this add-on."""
    value = _kodi_art_value(value).replace("\\", "/")
    if not value:
        return True
    candidates = set(entry.get("art_history") or [])
    candidates.update((entry.get("art_urls") or {}).values())
    candidates.update(v for v in (entry.get("poster_hint"), entry.get("fanart_hint"), entry.get("thumb")) if v)
    candidates.update((entry.get("season_art") or {}).values())
    folder = entry.get("folder")
    if folder:
        root = library.tv_root() if kind == "series" else library.movies_root()
        base = str(library.fs.join(root, folder)).replace("\\", "/")
        if value.startswith(base + "/"):
            return True
    return value in {str(c).replace("\\", "/") for c in candidates}


def _folder_of(path, is_file):
    path = str(path or "").replace("\\", "/").rstrip("/")
    if is_file:
        path = path.rsplit("/", 1)[0]
    return path.rsplit("/", 1)[-1]


def _repair_seasons(tvshow_id, season_art, rpc=None):
    """Season posters for seasons Kodi shows without one. Returns 1 if any set."""
    result = (_rpc("VideoLibrary.GetSeasons", {"tvshowid": tvshow_id, "properties": ["season", "art"]}, rpc)
              or {}).get("result") or {}
    changed = 0
    for season in result.get("seasons") or []:
        path = season_art.get(str(season.get("season")))
        if path and not (season.get("art") or {}).get("poster"):
            _rpc("VideoLibrary.SetSeasonDetails", {"seasonid": season["seasonid"], "art": {"poster": path}}, rpc)
            changed = 1
    return changed


def repair_kodi_art(library, marker="", rpc=None):
    """Give library titles without a poster or background their artwork.

    Matches Kodi's shows/films to our entries by folder name and only fills
    empty art slots, so artwork the user chose in Kodi is never replaced.
    ``marker`` is a path piece that identifies this add-on's library when
    Kodi stored the source as a special:// path. Returns the number of
    updated titles.
    """
    updated = 0
    jobs = (
        ("series", "VideoLibrary.GetTVShows", "tvshows", "tvshowid", "VideoLibrary.SetTVShowDetails", False),
        ("movie", "VideoLibrary.GetMovies", "movies", "movieid", "VideoLibrary.SetMovieDetails", True),
    )
    for kind, getter, key, id_key, setter, is_file in jobs:
        entries = {e.get("folder"): e for e in library.store.section(kind).values() if e.get("folder")}
        if not entries:
            continue
        roots = [library.tv_root() if kind == "series" else library.movies_root()]
        roots = [str(r).replace("\\", "/").rstrip("/").lower() for r in roots if r]
        result = (_rpc(getter, {"properties": ["file", "art"]}, rpc) or {}).get("result") or {}
        for item in result.get(key) or []:
            file_path = str(item.get("file") or "").replace("\\", "/")
            lowered = file_path.lower()
            if not any(root and root in lowered for root in roots) \
                    and not (marker and marker.lower() in lowered):
                continue
            entry = entries.get(_folder_of(file_path, is_file))
            if not entry:
                continue
            current = item.get("art") or {}
            # Fill empty slots, and replace artwork this add-on set earlier
            # when a better image is known. Artwork chosen in Kodi stays.
            missing = {k: v for k, v in local_art(library, kind, entry).items()
                       if _kodi_art_value(current.get(k)) != v and _owned(library, kind, entry, current.get(k))}
            if kind == "series" and entry.get("season_art"):
                updated += _repair_seasons(item[id_key], entry["season_art"], rpc)
            if not missing:
                continue
            _rpc(setter, {id_key: item[id_key], "art": missing}, rpc)
            updated += 1
    return updated


# --------------------------------------------------------------------------
# Library scans
# --------------------------------------------------------------------------
# Kodi ignores a scan request while another scan is running, so titles added
# in quick succession were never scanned. A small flag file remembers a
# request made during a scan; the service runs it as soon as Kodi is done.

def _rpc_call(method, params):
    if xbmc is None:
        return {}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params, "id": 1})))
    except Exception:
        return {}


def kodi_is_scanning():
    if xbmc is None:
        return False
    try:
        return bool(xbmc.getCondVisibility("Library.IsScanningVideo"))
    except Exception:
        return False


def request_scan(flag_path, scan=True, clean=False, is_scanning=kodi_is_scanning, rpc=_rpc_call):
    """Clean and/or scan now, or remember the request when Kodi is busy."""
    if is_scanning():
        try:
            folder = os.path.dirname(flag_path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(flag_path, "w", encoding="utf-8") as handle:
                json.dump({"scan": bool(scan), "clean": bool(clean)}, handle)
        except Exception:
            pass
        return False
    if clean:
        rpc("VideoLibrary.Clean", {"showdialogs": False})
    if scan:
        rpc("VideoLibrary.Scan", {"showdialogs": False})
    return True


def run_pending_scan(flag_path, is_scanning=kodi_is_scanning, rpc=_rpc_call):
    """Run a scan that was requested while Kodi was busy. True when one ran."""
    try:
        with open(flag_path, "r", encoding="utf-8") as handle:
            wanted = json.load(handle) or {}
    except Exception:
        return False
    if is_scanning():
        return False
    try:
        os.remove(flag_path)
    except OSError:
        pass
    return request_scan(flag_path, scan=wanted.get("scan", True), clean=wanted.get("clean", False),
                        is_scanning=lambda: False, rpc=rpc)


def kodi_counts(library, marker="", rpc=None):
    """How many of our series/films Kodi actually has: (series, films)."""
    counts = []
    for kind, getter, key, is_file in (("series", "VideoLibrary.GetTVShows", "tvshows", False),
                                       ("movie", "VideoLibrary.GetMovies", "movies", True)):
        folders = {e.get("folder") for e in library.store.section(kind).values() if e.get("folder")}
        root = str(library.tv_root() if kind == "series" else library.movies_root()).replace("\\", "/").lower()
        result = (_rpc(getter, {"properties": ["file"]}, rpc) or {}).get("result") or {}
        found = set()
        for item in result.get(key) or []:
            path = str(item.get("file") or "").replace("\\", "/")
            if (root and root.rstrip("/") in path.lower()) or (marker and marker.lower() in path.lower()):
                folder = _folder_of(path, is_file)
                if folder in folders:
                    found.add(folder)
        counts.append(len(found))
    return tuple(counts)
