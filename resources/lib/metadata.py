"""Fill in missing library metadata from TMDb and TVmaze.

The streaming service's own data always wins. This module only supplies
fields that are empty: plot, artwork, year, genres, rating, studio and
per-episode plot/thumbnail/title, plus TMDb/TVDB/IMDb ids so Kodi, skins and
Trakt can match titles reliably.

* TMDb (themoviedb.org) is used for series and films when the user entered a
  free TMDb API key (v3 key or v4 read access token).
* TVmaze is used for series without any key, and as a fallback.
* TVDB itself needs a paid key, so it is not queried; its id comes along
  through TMDb's and TVmaze's external ids.

Only exact (normalised) title matches are accepted, so a wrong show is never
used. Every answer, including "not found", is cached on disk.
"""

import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request

TMDB_API = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p/original"
TVMAZE_API = "https://api.tvmaze.com"
TIMEOUT = 10
CACHE_TTL = 7 * 24 * 3600
MISS_TTL = 24 * 3600
OFFLINE_RETRY = 300

_GENERIC_TITLE = re.compile(r"^\s*(episode|aflevering|afl\.?)\s*\d+\s*$", re.IGNORECASE)


def normalize_title(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("&", " and ")
    return re.sub(r"[^0-9a-z]+", " ", text).strip()


def is_missing(value):
    """True for empty values and placeholder episode titles like 'Aflevering 3'."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or bool(_GENERIC_TITLE.match(value))
    if isinstance(value, (list, tuple, dict)):
        return not value
    return False


def merge(local, extra):
    """Return ``local`` with empty fields filled from ``extra``."""
    result = dict(local or {})
    for key, value in (extra or {}).items():
        if is_missing(result.get(key)) and not is_missing(value):
            result[key] = value
    return result


def _strip_html(text):
    text = re.sub(r"<[^>]+>", "", str(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _year(value):
    match = re.match(r"^(\d{4})", str(value or ""))
    return int(match.group(1)) if match else None


class DiskCache:
    def __init__(self, path):
        self.path = path
        self.data = None

    def _load(self):
        if self.data is None:
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    self.data = json.load(handle)
                if not isinstance(self.data, dict):
                    self.data = {}
            except Exception:
                self.data = {}
        return self.data

    def get(self, key, now):
        entry = self._load().get(key)
        if not isinstance(entry, dict) or entry.get("expires", 0) < now:
            return None, False
        return entry.get("value"), True

    def put(self, key, value, ttl, now):
        self._load()[key] = {"value": value, "expires": now + ttl}

    def save(self, now=None):
        if self.data is None or not self.path:
            return
        now = time.time() if now is None else now
        data = {k: v for k, v in self.data.items() if isinstance(v, dict) and v.get("expires", 0) >= now}
        try:
            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            temporary = self.path + ".tmp"
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False)
            os.replace(temporary, self.path)
        except Exception:
            pass


def _default_http(url, headers):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


class Enricher:
    def __init__(self, cache_path, tmdb_key="", language="nl-NL", http=None, now=None,
                 user_agent="Kodi library metadata"):
        self.tmdb_key = (tmdb_key or "").strip()
        self.language = language or "nl-NL"
        self.http = http or _default_http
        self.now = now or time.time
        self.cache = DiskCache(cache_path)
        self.user_agent = user_agent
        self._offline_until = {}

    # -------------------------------------------------------------- plumbing
    def save(self):
        self.cache.save(self.now())

    def _get(self, service, url, headers, cache_key):
        cached, hit = self.cache.get(cache_key, self.now())
        if hit:
            return cached
        if self.now() < self._offline_until.get(service, 0):
            return None
        try:
            value = self.http(url, headers)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code == 404:
                self.cache.put(cache_key, None, MISS_TTL, self.now())
                return None
            # Network problem or rate limit: stop asking this service for a while.
            self._offline_until[service] = self.now() + OFFLINE_RETRY
            return None
        self.cache.put(cache_key, value, CACHE_TTL if value else MISS_TTL, self.now())
        return value

    def _tmdb(self, path, params=None):
        if not self.tmdb_key:
            return None
        params = dict(params or {})
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        if len(self.tmdb_key) > 40:  # v4 read access token
            headers["Authorization"] = "Bearer " + self.tmdb_key
        else:
            params["api_key"] = self.tmdb_key
        key_free = {k: v for k, v in params.items() if k != "api_key"}
        cache_key = "tmdb:" + path + "?" + urllib.parse.urlencode(sorted(key_free.items()))
        url = TMDB_API + path + ("?" + urllib.parse.urlencode(params) if params else "")
        return self._get("tmdb", url, headers, cache_key)

    def _tvmaze(self, path, params=None):
        query = "?" + urllib.parse.urlencode(params) if params else ""
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        return self._get("tvmaze", TVMAZE_API + path + query, headers, "tvmaze:" + path + query)

    @staticmethod
    def _image(path):
        return TMDB_IMAGE + path if path else ""

    # ---------------------------------------------------------------- series
    def show(self, title, year=None, known=None):
        """Return extra show data and ids. ``known`` holds ids found earlier."""
        known = dict(known or {})
        data = {}
        tmdb_id = known.get("tmdb")
        if not tmdb_id and self.tmdb_key:
            tmdb_id = self._tmdb_search("tv", title, year)
        if tmdb_id:
            data = merge(data, self._tmdb_show(tmdb_id))
        tvmaze_id = known.get("tvmaze")
        if not tvmaze_id:
            tvmaze_id = self._tvmaze_search(title, data.get("ids", {}).get("tvdb"))
        if tvmaze_id:
            maze = self._tvmaze_show(tvmaze_id)
            ids = dict(maze.get("ids", {}))
            ids.update({k: v for k, v in data.get("ids", {}).items() if v})
            data = merge(data, maze)
            data["ids"] = ids
        ids = data.setdefault("ids", {})
        for key, value in known.items():
            ids.setdefault(key, value)
        return data

    def _tmdb_search(self, kind, title, year=None):
        wanted = normalize_title(title)
        if not wanted:
            return None
        params = {"query": title, "language": self.language, "include_adult": "false"}
        payload = self._tmdb("/search/" + kind, params) or {}
        candidates = []
        for hit in payload.get("results") or []:
            names = (hit.get("name"), hit.get("original_name"), hit.get("title"), hit.get("original_title"))
            if wanted in {normalize_title(name) for name in names if name}:
                hit_year = _year(hit.get("first_air_date") or hit.get("release_date"))
                candidates.append((hit_year, hit.get("id")))
        if not candidates:
            return None
        if year:
            for hit_year, hit_id in candidates:
                if hit_year and abs(hit_year - int(year)) <= 1:
                    return hit_id
            if kind == "movie":
                return None  # remakes share titles; the year must match for films
        return candidates[0][1]

    def _tmdb_details(self, kind, tmdb_id):
        detail = self._tmdb("/{}/{}".format(kind, tmdb_id),
                            {"language": self.language, "append_to_response": "external_ids"}) or {}
        if detail and not detail.get("overview") and not self.language.startswith("en"):
            english = self._tmdb("/{}/{}".format(kind, tmdb_id), {"language": "en-US"}) or {}
            detail = dict(detail, overview=english.get("overview") or "")
        return detail

    def _tmdb_show(self, tmdb_id):
        detail = self._tmdb_details("tv", tmdb_id)
        if not detail:
            return {}
        external = detail.get("external_ids") or {}
        return {
            "plot": detail.get("overview") or "",
            "poster": self._image(detail.get("poster_path")),
            "fanart": self._image(detail.get("backdrop_path")),
            "premiered": detail.get("first_air_date") or "",
            "year": _year(detail.get("first_air_date")),
            "genres": [g.get("name") for g in detail.get("genres") or [] if g.get("name")],
            "studio": next((n.get("name") for n in detail.get("networks") or [] if n.get("name")), ""),
            "rating": detail.get("vote_average") or None,
            "ids": {"tmdb": str(tmdb_id), "tvdb": str(external.get("tvdb_id") or "") or None,
                    "imdb": external.get("imdb_id") or None},
        }

    def _tvmaze_search(self, title, tvdb_id=None):
        if tvdb_id:
            hit = self._tvmaze("/lookup/shows", {"thetvdb": tvdb_id})
            if isinstance(hit, dict) and hit.get("id"):
                return hit["id"]
        wanted = normalize_title(title)
        if not wanted:
            return None
        for hit in self._tvmaze("/search/shows", {"q": title}) or []:
            show = hit.get("show") or {}
            if normalize_title(show.get("name")) == wanted:
                return show.get("id")
        return None

    def _tvmaze_show(self, tvmaze_id):
        show = self._tvmaze("/shows/{}".format(tvmaze_id)) or {}
        if not show:
            return {}
        externals = show.get("externals") or {}
        image = show.get("image") or {}
        network = show.get("network") or show.get("webChannel") or {}
        return {
            "plot": _strip_html(show.get("summary")),
            "poster": image.get("original") or "",
            "premiered": show.get("premiered") or "",
            "year": _year(show.get("premiered")),
            "genres": list(show.get("genres") or []),
            "studio": network.get("name") or "",
            "rating": (show.get("rating") or {}).get("average"),
            "ids": {"tvmaze": str(tvmaze_id),
                    "tvdb": str(externals.get("thetvdb") or "") or None,
                    "imdb": externals.get("imdb") or None},
        }

    # -------------------------------------------------------------- episodes
    def episode(self, ids, season=None, number=None, airdate=None, by_number=True):
        """Extra data for one episode, matched by air date and/or number."""
        ids = ids or {}
        extra = {}
        if ids.get("tmdb") and by_number and season is not None and number is not None:
            extra = merge(extra, self._tmdb_episode(ids["tmdb"], season, number))
        if ids.get("tvmaze"):
            extra = merge(extra, self._tvmaze_episode(ids["tvmaze"], season, number, airdate, by_number))
        return extra

    def _tmdb_episode(self, tmdb_id, season, number):
        payload = self._tmdb("/tv/{}/season/{}".format(tmdb_id, season), {"language": self.language}) or {}
        for ep in payload.get("episodes") or []:
            if ep.get("episode_number") == number:
                return {"title": ep.get("name") or "", "plot": ep.get("overview") or "",
                        "thumb": self._image(ep.get("still_path")), "aired": ep.get("air_date") or ""}
        return {}

    def _tvmaze_episode(self, tvmaze_id, season, number, airdate, by_number):
        episodes = self._tvmaze("/shows/{}/episodes".format(tvmaze_id), {"specials": 1}) or []
        match = None
        if airdate:
            same_day = [ep for ep in episodes if ep.get("airdate") == airdate]
            if len(same_day) == 1:
                match = same_day[0]
        if match is None and by_number and season is not None and number is not None:
            match = next((ep for ep in episodes
                          if ep.get("season") == season and ep.get("number") == number), None)
        if not match:
            return {}
        return {"title": match.get("name") or "", "plot": _strip_html(match.get("summary")),
                "thumb": (match.get("image") or {}).get("original") or "",
                "aired": match.get("airdate") or ""}

    # ---------------------------------------------------------------- movies
    def movie(self, title, year=None, known=None):
        known = dict(known or {})
        tmdb_id = known.get("tmdb") or (self._tmdb_search("movie", title, year) if self.tmdb_key else None)
        if not tmdb_id:
            return {"ids": known} if known else {}
        detail = self._tmdb_details("movie", tmdb_id)
        if not detail:
            return {"ids": dict(known, tmdb=str(tmdb_id))}
        external = detail.get("external_ids") or {}
        return {
            "plot": detail.get("overview") or "",
            "poster": self._image(detail.get("poster_path")),
            "fanart": self._image(detail.get("backdrop_path")),
            "premiered": detail.get("release_date") or "",
            "year": _year(detail.get("release_date")),
            "genres": [g.get("name") for g in detail.get("genres") or [] if g.get("name")],
            "studio": next((c.get("name") for c in detail.get("production_companies") or [] if c.get("name")), ""),
            "rating": detail.get("vote_average") or None,
            "runtime": detail.get("runtime") or None,
            "tagline": detail.get("tagline") or "",
            "ids": dict(known, tmdb=str(tmdb_id), imdb=detail.get("imdb_id") or external.get("imdb_id") or None),
        }


def nfo_extra_lines(data, escape, kind="show"):
    """XML lines for the extra fields every nfo type shares."""
    lines = []
    for genre in data.get("genres") or []:
        lines.append("  <genre>{}</genre>".format(escape(genre)))
    if data.get("premiered"):
        lines.append("  <premiered>{}</premiered>".format(escape(data["premiered"])))
    if data.get("studio"):
        lines.append("  <studio>{}</studio>".format(escape(data["studio"])))
    if data.get("tagline"):
        lines.append("  <tagline>{}</tagline>".format(escape(data["tagline"])))
    if data.get("runtime") and kind == "movie":
        lines.append("  <runtime>{}</runtime>".format(int(data["runtime"])))
    rating = data.get("rating")
    if isinstance(rating, (int, float)) and rating > 0:
        lines.append('  <ratings><rating name="themoviedb" max="10" default="true"><value>{:.1f}</value>'
                     "</rating></ratings>".format(float(rating)))
    ids = data.get("ids") or {}
    for key in ("tmdb", "tvdb", "imdb", "tvmaze"):
        if ids.get(key):
            lines.append('  <uniqueid type="{}">{}</uniqueid>'.format(key, escape(str(ids[key]))))
    return lines
