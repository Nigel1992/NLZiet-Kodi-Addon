"""
NLZiet API wrapper — form login + cookie handling.

This implements the form-based login flow observed in the HAR you provided:
- GET the login page, extract the anti-forgery token (`__RequestVerificationToken`)
- POST the credentials (EmailAddress / Password / button) together with the token
- Persist cookies in the addon's profile so subsequent API calls use the authenticated session

Notes:
- This implements the browser form login shown in the HAR. It does NOT (yet) perform
  the OAuth PKCE code->token exchange; for that I need the HAR entries for the
  authorize/callback and token endpoints (or the connect/token request/response).
"""
import re
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import xbmcvfs
import xbmcaddon
import xbmc
import traceback


class NLZietAPI:
    def __init__(self, username=None, password=None, base_url=None):
        self.addon = xbmcaddon.Addon()
        self.username = username or self.addon.getSetting('username')
        self.password = password or self.addon.getSetting('password')
        self.base_url = base_url or self.addon.getSetting('api_base_url') or 'https://api.nlziet.nl'
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'

        addon_id = self.addon.getAddonInfo('id')
        cookie_dir = xbmcvfs.translatePath('special://profile/addon_data/{}'.format(addon_id))
        try:
            os.makedirs(cookie_dir, exist_ok=True)
        except Exception:
            pass

        # persistent debug log for HTTP requests/responses
        self.debug_file = os.path.join(cookie_dir, 'nlziet_http_debug.txt')

        self.cookie_file = os.path.join(cookie_dir, 'cookies.lwp')
        self.stream_cookie_file = os.path.join(cookie_dir, 'stream_cookies')
        self.profile_file = os.path.join(cookie_dir, 'profile.json')
        self.token_file = os.path.join(cookie_dir, 'tokens.json')
        # Local My List storage (fallback when server-side My List is unavailable)
        self.mylist_file = os.path.join(cookie_dir, 'mylist.json')

        self.cookie_jar = http.cookiejar.LWPCookieJar()
        try:
            if os.path.exists(self.cookie_file):
                self.cookie_jar.load(self.cookie_file, ignore_discard=True, ignore_expires=True)
        except Exception:
            pass

        # If we have an older JSON cookie dump (stream_cookies), import into LWPCookieJar
        try:
            if (not os.path.exists(self.cookie_file) or len(self.cookie_jar) == 0) and os.path.exists(self.stream_cookie_file):
                with open(self.stream_cookie_file, 'r', encoding='utf-8') as f:
                    sc = json.load(f)
                for name, value in sc.items():
                    try:
                        c = http.cookiejar.Cookie(
                            version=0,
                            name=name,
                            value=value,
                            port=None,
                            port_specified=False,
                            domain='.nlziet.nl',
                            domain_specified=True,
                            domain_initial_dot=True,
                            path='/',
                            path_specified=True,
                            secure=True,
                            expires=None,
                            discard=False,
                            comment=None,
                            comment_url=None,
                            rest={'HttpOnly': True},
                            rfc2109=False,
                        )
                        self.cookie_jar.set_cookie(c)
                    except Exception:
                        pass
                try:
                    self.cookie_jar.save(self.cookie_file, ignore_discard=True, ignore_expires=True)
                except Exception:
                    pass
        except Exception:
            pass

        # load previously saved tokens if present (tokens.json preferred, fallback to profile.json)
        self.tokens = {}
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    self.tokens = json.load(f)
            else:
                if os.path.exists(self.profile_file):
                    with open(self.profile_file, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                    access = profile.get('access_token')
                    refresh = profile.get('refresh_token') or profile.get('refresh_token')
                    if access:
                        exp = self._get_jwt_exp(access)
                        if exp:
                            expires_at = int(exp)
                        else:
                            try:
                                issue = int(profile.get('access_token_age', 0))
                                expires_at = issue + 3600
                            except Exception:
                                expires_at = int(time.time()) + 3600
                        self.tokens = {'access_token': access, 'refresh_token': refresh, 'expires_at': expires_at}
        except Exception:
            self.tokens = {}

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPRedirectHandler(),
        )
        self.opener.addheaders = [('User-Agent', self.user_agent)]

        # current access token (kept in memory for quick access)
        self.token = self.tokens.get('access_token')
        # If no access token but persistent NLZiet cookies exist, mark
        # this session as a cookie-based session so callers can detect
        # an authenticated cookie session after a Kodi restart.
        if not self.token:
            try:
                for c in self.cookie_jar:
                    dom = getattr(c, 'domain', '') or ''
                    if 'nlziet' in dom.lower():
                        self.token = 'cookie-session'
                        break
            except Exception:
                pass

    def _append_debug(self, text):
        try:
            # Only write HTTP debug logs when the debug toggle is enabled
            try:
                dbg_val = self.addon.getSetting('debug_http')
            except Exception:
                dbg_val = None
            if not str(dbg_val or '').lower() in ('true', '1', 'yes'):
                return

            d = os.path.dirname(self.debug_file)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(self.debug_file, 'a', encoding='utf-8') as f:
                f.write(text + '\n')
        except Exception:
            pass

    def _open_with_opener(self, opener, req_or_url, timeout=20):
        import io
        import datetime
        import urllib.request
        import urllib.error

        # normalize to Request
        if isinstance(req_or_url, str):
            req = urllib.request.Request(req_or_url)
        else:
            req = req_or_url

        method = getattr(req, 'method', None) or ('POST' if getattr(req, 'data', None) else 'GET')
        try:
            url = req.get_full_url()
        except Exception:
            try:
                url = req.full_url
            except Exception:
                url = str(req)

        try:
            req_headers = dict(req.header_items())
        except Exception:
            req_headers = {}

        req_data = None
        if getattr(req, 'data', None):
            try:
                if isinstance(req.data, (bytes, bytearray)):
                    req_data = req.data.decode('utf-8', errors='ignore')
                else:
                    req_data = str(req.data)
            except Exception:
                req_data = '<non-decodable>'

        self._append_debug(f"--- HTTP {method} {datetime.datetime.utcnow().isoformat()} ---")
        self._append_debug(f"URL: {url}")
        if req_headers:
            try:
                self._append_debug(f"Headers: {req_headers}")
            except Exception:
                pass
        if req_data:
            try:
                snippet = req_data if len(req_data) <= 4000 else req_data[:4000] + '...'
                self._append_debug(f"Data: {snippet}")
            except Exception:
                pass

        try:
            r = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as he:
            status = getattr(he, 'code', None)
            try:
                resp_headers = dict(he.headers) if he.headers else {}
            except Exception:
                resp_headers = {}
            try:
                body_bytes = he.read() or b''
            except Exception:
                body_bytes = b''
            try:
                body_text = body_bytes.decode('utf-8', errors='replace')
            except Exception:
                body_text = '<binary>'

            self._append_debug(f"Status: {status}")
            self._append_debug(f"Response headers: {resp_headers}")
            if body_text:
                try:
                    self._append_debug(f"Response body: {body_text}")
                except Exception:
                    pass
            self._append_debug("--- END ---")
            raise
        else:
            try:
                resp_bytes = r.read() or b''
            except Exception:
                resp_bytes = b''

            try:
                resp_status = r.getcode()
            except Exception:
                resp_status = None

            try:
                resp_headers = dict(r.getheaders())
            except Exception:
                try:
                    resp_headers = dict(r.info())
                except Exception:
                    resp_headers = {}

            try:
                resp_text = resp_bytes.decode('utf-8', errors='replace')
            except Exception:
                resp_text = '<binary>'

            self._append_debug(f"Status: {resp_status}")
            self._append_debug(f"Response headers: {resp_headers}")
            if resp_text:
                try:
                    snippet = resp_text if len(resp_text) <= 4000 else resp_text[:4000] + '...'
                    self._append_debug(f"Response body: {snippet}")
                except Exception:
                    pass
            self._append_debug("--- END ---")

            class _RespWrapper(io.BytesIO):
                def __init__(self, data, status, headers, url):
                    super().__init__(data)
                    self._status = status
                    self._headers = headers or {}
                    self._url = url

                def getcode(self):
                    return self._status

                def geturl(self):
                    return self._url

                def info(self):
                    class InfoObj:
                        def __init__(self, headers):
                            self._h = headers

                        def get(self, k, default=None):
                            return self._h.get(k, default)

                        def items(self):
                            return list(self._h.items())

                    return InfoObj(self._headers)

                def getheaders(self):
                    return list(self._headers.items())

                def getheader(self, name, default=None):
                    return self._headers.get(name, default)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    try:
                        self.close()
                    except Exception:
                        pass

            return _RespWrapper(resp_bytes, resp_status, resp_headers, url)

    def get_movies(self, limit=999):
        """Fetch recommended movies using the endpoint observed in the HAR."""
        try:
            url = f"{self.base_url}/v9/recommend/withcontext?contextName=recommendMovies&limit={limit}"
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            # If we have a cookie-session but no tokens yet, try to obtain tokens
            if not token and getattr(self, 'token', None) == 'cookie-session':
                try:
                    tokens = self.perform_pkce_authorize_and_exchange()
                    if tokens and tokens.get('access_token'):
                        token = tokens.get('access_token')
                except Exception:
                    token = None

            if token:
                headers['Authorization'] = 'Bearer ' + token

            # include active profile id when present (mirror other endpoints)
            try:
                if os.path.exists(self.profile_file):
                    with open(self.profile_file, 'r', encoding='utf-8') as pf_f:
                        pfj = json.load(pf_f)
                    profile_id = pfj.get('profile_id') or pfj.get('profile') or pfj.get('id')
                    if profile_id:
                        headers['X-Profile-Id'] = str(profile_id)
            except Exception:
                pass

            # debug: record headers being sent for troubleshooting
            try:
                self._append_debug(f"Search headers: {headers}")
            except Exception:
                pass
            # include active profile id in handshake when known
            try:
                if os.path.exists(self.profile_file):
                    with open(self.profile_file, 'r', encoding='utf-8') as pf_f:
                        pfj = json.load(pf_f)
                    profile_id = pfj.get('profile_id') or pfj.get('profile') or pfj.get('id')
                    if profile_id:
                        headers['X-Profile-Id'] = str(profile_id)
            except Exception:
                pass
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)
            results = []
            items = data.get('data') or data.get('results') or data.get('items') or []
            for item in items:
                src = item.get('item') if isinstance(item, dict) and item.get('item') else item.get('content') if isinstance(item, dict) and item.get('content') else item
                if not isinstance(src, dict):
                    continue
                content_id = src.get('id') or src.get('contentId') or src.get('content_id')
                title = src.get('title') or src.get('name') or (item.get('analytics') or {}).get('assetName')
                # prefer explicit posterUrl, fall back to image dict
                thumb = src.get('posterUrl') or (src.get('image') or {}).get('portraitUrl') or (src.get('image') or {}).get('landscapeUrl')
                typ = src.get('type') or (item.get('content') or {}).get('type')
                # include available description/subtitle when present so UI can show it without extra requests
                desc = src.get('description') or src.get('plot') or src.get('summary') or ''
                subtitle = src.get('subtitle') or src.get('subtitleText') or ''
                # detect expiration/availability timestamps when present
                expires_at = None
                for key in ('availableTo', 'available_to', 'availableUntil', 'available_until', 'endDate', 'end_date', 'expiresAt', 'expires_at', 'expiration', 'validUntil', 'valid_until', 'availableToDate', 'available_to_date'):
                    if isinstance(src, dict) and key in src and src.get(key):
                        parsed = self._parse_timestamp(src.get(key))
                        if parsed:
                            expires_at = parsed
                            break
                if not expires_at:
                    availability = src.get('availability') or src.get('availabilities') or src.get('availabilityRange') or src.get('availableRanges')
                    if availability:
                        if isinstance(availability, dict):
                            for k in ('endDate', 'to', 'availableTo', 'end'):
                                v = availability.get(k)
                                if v:
                                    parsed = self._parse_timestamp(v)
                                    if parsed:
                                        expires_at = parsed
                                        break
                        elif isinstance(availability, (list, tuple)):
                            for a in availability:
                                if isinstance(a, dict):
                                    v = a.get('endDate') or a.get('to') or a.get('availableTo') or a.get('end')
                                    if v:
                                        parsed = self._parse_timestamp(v)
                                        if parsed:
                                            expires_at = parsed
                                            break
                if not expires_at:
                    for k, v in src.items():
                        try:
                            if k and isinstance(k, str) and k.lower().endswith(('date', 'until', 'at')):
                                parsed = self._parse_timestamp(v)
                                if parsed:
                                    expires_at = parsed
                                    break
                        except Exception:
                            continue
                expires_in = None
                if expires_at:
                    now = int(time.time())
                    secs = expires_at - now
                    if secs <= 0:
                        expires_in = 'Expired'
                    else:
                        days = secs // 86400
                        if days >= 1:
                            expires_in = f'Expires in {days}d'
                        else:
                            hours = secs // 3600
                            if hours >= 1:
                                expires_in = f'Expires in {hours}h'
                            else:
                                minutes = max(1, secs // 60)
                                expires_in = f'Expires in {minutes}m'
                results.append({'id': content_id, 'title': title, 'thumb': thumb, 'type': typ, 'description': desc, 'subtitle': subtitle, 'posterUrl': thumb, 'expires_at': expires_at, 'expires_in': expires_in})
            return results
        except Exception as e:
            xbmc.log(f"NLZiet get_movies error: {e}", xbmc.LOGERROR)
            return []


    def get_videos(self, limit=999):
        """Fetch recommended videos (TV shows) using the recommend/withContext endpoint.

        Mirrors `get_movies` but requests `contextName=recommendVideos`.
        """
        try:
            url = f"{self.base_url}/v9/recommend/withcontext?contextName=recommendVideos&limit={limit}"
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            try:
                if os.path.exists(self.profile_file):
                    with open(self.profile_file, 'r', encoding='utf-8') as pf_f:
                        pfj = json.load(pf_f)
                    profile_id = pfj.get('profile_id') or pfj.get('profile') or pfj.get('id')
                    if profile_id:
                        headers['X-Profile-Id'] = str(profile_id)
            except Exception:
                pass

            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            items = data.get('data') or data.get('results') or data.get('items') or []
            results = []
            for item in items:
                src = item.get('item') if isinstance(item, dict) and item.get('item') else item.get('content') if isinstance(item, dict) and item.get('content') else item
                if not isinstance(src, dict):
                    continue
                content_id = src.get('id') or src.get('contentId') or src.get('content_id')
                title = src.get('title') or src.get('name') or (item.get('analytics') or {}).get('assetName')
                thumb = src.get('posterUrl') or (src.get('image') or {}).get('portraitUrl') or (src.get('image') or {}).get('landscapeUrl')
                desc = src.get('description') or src.get('plot') or src.get('summary') or ''
                subtitle = src.get('subtitle') or src.get('subtitleText') or ''
                results.append({'id': content_id, 'title': title, 'thumb': thumb, 'description': desc, 'subtitle': subtitle})
            return results
        except Exception as e:
            xbmc.log(f"NLZiet get_videos error: {e}", xbmc.LOGERROR)
            return []


    def get_documentaries(self, limit=999, offset=0):
        """Fetch recommended Documentary programs using the filtered recommend endpoint.

        Uses: /v9/recommend/filtered?category=Programs&genre=Documentary&limit={limit}&offset={offset}
        """
        try:
            url = f"{self.base_url}/v9/recommend/filtered?category=Programs&genre=Documentary&limit={limit}&offset={offset}"
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            try:
                if os.path.exists(self.profile_file):
                    with open(self.profile_file, 'r', encoding='utf-8') as pf_f:
                        pfj = json.load(pf_f)
                    profile_id = pfj.get('profile_id') or pfj.get('profile') or pfj.get('id')
                    if profile_id:
                        headers['X-Profile-Id'] = str(profile_id)
            except Exception:
                pass

            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            items = data.get('data') or data.get('results') or data.get('items') or []
            results = []
            for item in items:
                src = item.get('item') if isinstance(item, dict) and item.get('item') else item.get('content') if isinstance(item, dict) and item.get('content') else item
                if not isinstance(src, dict):
                    continue
                content_id = src.get('id') or src.get('contentId') or src.get('content_id')
                title = src.get('title') or src.get('name') or (item.get('analytics') or {}).get('assetName')
                thumb = src.get('posterUrl') or (src.get('image') or {}).get('portraitUrl') or (src.get('image') or {}).get('landscapeUrl')
                desc = src.get('description') or src.get('plot') or src.get('summary') or ''
                subtitle = src.get('subtitle') or src.get('subtitleText') or ''
                results.append({'id': content_id, 'title': title, 'thumb': thumb, 'description': desc, 'subtitle': subtitle})
            return results
        except Exception as e:
            xbmc.log(f"NLZiet get_documentaries error: {e}", xbmc.LOGERROR)
            return []


    def get_customer_summary(self):
        """Retrieve account summary from the customer API using bearer token."""
        try:
            token = self.get_access_token()
            # If we have a cookie-session but no token yet, try to perform PKCE authorize+exchange
            if not token and getattr(self, 'token', None) == 'cookie-session':
                try:
                    tokens = self.perform_pkce_authorize_and_exchange()
                    if tokens and tokens.get('access_token'):
                        token = tokens.get('access_token')
                except Exception:
                    token = None

            if not token:
                return {}

            url = 'https://api.customer.nlziet.nl/customer/summary'
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'Authorization': 'Bearer ' + token,
            }
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)
            return data or {}
        except Exception as e:
            xbmc.log(f"NLZiet get_customer_summary error: {e}", xbmc.LOGERROR)
            return {}


    def get_content_detail(self, content_id):
        """Fetch content detail including description/plot for a given content id."""
        if not content_id:
            return {}
        try:
            url = urllib.parse.urljoin(self.base_url, f'/v9/content/detail/{content_id}')
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            # Debug: record the constructed episodes URL and headers
            try:
                self._append_debug(f"get_series_episodes request URL: {url}")
                self._append_debug(f"get_series_episodes headers: {headers}")
            except Exception:
                pass
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)
            items = data.get('data') or []
            if not items:
                return {}
            first = items[0]
            content = first.get('content') if isinstance(first, dict) and first.get('content') else first
            desc = ''
            try:
                desc = content.get('description') or content.get('plot') or ''
            except Exception:
                desc = ''
            thumb = None
            try:
                img = content.get('image') or {}
                thumb = content.get('posterUrl') or img.get('portraitUrl') or img.get('landscapeUrl') or None
            except Exception:
                thumb = None
            title = content.get('title') or first.get('title') or ''
            # detect expiry for detailed content when available
            expires_at = None
            for key in ('availableTo', 'available_to', 'availableUntil', 'available_until', 'endDate', 'end_date', 'expiresAt', 'expires_at', 'expiration', 'validUntil', 'valid_until', 'availableToDate', 'available_to_date'):
                if isinstance(content, dict) and key in content and content.get(key):
                    parsed = self._parse_timestamp(content.get(key))
                    if parsed:
                        expires_at = parsed
                        break
            if not expires_at:
                availability = content.get('availability') or content.get('availabilities') or content.get('availabilityRange')
                if availability:
                    if isinstance(availability, dict):
                        for k in ('endDate', 'to', 'availableTo', 'end'):
                            v = availability.get(k)
                            if v:
                                parsed = self._parse_timestamp(v)
                                if parsed:
                                    expires_at = parsed
                                    break
                    elif isinstance(availability, (list, tuple)):
                        for a in availability:
                            if isinstance(a, dict):
                                v = a.get('endDate') or a.get('to') or a.get('availableTo') or a.get('end')
                                if v:
                                    parsed = self._parse_timestamp(v)
                                    if parsed:
                                        expires_at = parsed
                                        break
            expires_in = None
            if expires_at:
                now = int(time.time())
                secs = expires_at - now
                if secs <= 0:
                    expires_in = 'Expired'
                else:
                    days = secs // 86400
                    if days >= 1:
                        expires_in = f'Expires in {days}d'
                    else:
                        hours = secs // 3600
                        if hours >= 1:
                            expires_in = f'Expires in {hours}h'
                        else:
                            minutes = max(1, secs // 60)
                            expires_in = f'Expires in {minutes}m'
            return {'id': content_id, 'title': title, 'description': desc, 'thumb': thumb, 'raw': content, 'expires_at': expires_at, 'expires_in': expires_in}
        except Exception:
            return {}


    def save_cookies(self):
        try:
            self.cookie_jar.save(self.cookie_file, ignore_discard=True, ignore_expires=True)
        except Exception:
            pass

    def save_tokens(self):
        try:
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(self.tokens, f)
        except Exception:
            pass

    # --- My List: local persistence fallback ---------------------------------
    def _save_my_list(self, items):
        try:
            # ensure directory exists
            d = os.path.dirname(self.mylist_file)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(self.mylist_file, 'w', encoding='utf-8') as f:
                json.dump(items or [], f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            try:
                self._append_debug(f"Failed to save mylist: {traceback.format_exc()}")
            except Exception:
                pass
            return False

    def get_my_list(self):
        """Return the locally-stored My List (list of item dicts).

        This implementation uses a local JSON file as a fallback so the
        add/remove My List UI works even when a server-side My List
        endpoint is not implemented or accessible.
        """
        try:
            if os.path.exists(self.mylist_file):
                with open(self.mylist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f) or []
                if isinstance(data, list):
                    return data
                # support older formats where items nested under a key
                if isinstance(data, dict) and 'items' in data and isinstance(data['items'], list):
                    return data['items']
        except Exception:
            try:
                self._append_debug(f"Failed to load mylist: {traceback.format_exc()}")
            except Exception:
                pass
        return []

    def is_in_my_list(self, content_id):
        try:
            if not content_id:
                return False
            items = self.get_my_list() or []
            for it in items:
                try:
                    if str(it.get('id')) == str(content_id):
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def add_to_my_list(self, item):
        """Add a normalized item to the local My List. Returns True on success."""
        try:
            if not item or not isinstance(item, dict):
                return False
            cid = item.get('id') or item.get('contentId') or item.get('content_id')
            if not cid:
                return False
            items = self.get_my_list() or []
            # already present?
            for it in items:
                try:
                    if str(it.get('id')) == str(cid):
                        return True
                except Exception:
                    continue

            normalized = {
                'id': cid,
                'title': item.get('title') or item.get('name') or '',
                'type': item.get('type') or item.get('contentType') or '',
                'posterUrl': item.get('posterUrl') or item.get('thumb') or item.get('poster') or None,
                'raw': item,
            }
            items.append(normalized)
            return self._save_my_list(items)
        except Exception:
            try:
                self._append_debug(f"add_to_my_list exception: {traceback.format_exc()}")
            except Exception:
                pass
            return False

    def remove_from_my_list(self, content_id):
        """Remove an item from local My List by id. Returns True if removed."""
        try:
            if not content_id:
                return False
            items = self.get_my_list() or []
            new_items = [it for it in items if str(it.get('id')) != str(content_id)]
            if len(new_items) == len(items):
                # nothing removed
                return False
            return self._save_my_list(new_items)
        except Exception:
            try:
                self._append_debug(f"remove_from_my_list exception: {traceback.format_exc()}")
            except Exception:
                pass
            return False

    # --- End My List --------------------------------------------------------

    def exchange_code_for_tokens(self, code, code_verifier, redirect_uri='https://app.nlziet.nl/callback'):
        url = 'https://id.nlziet.nl/connect/token'
        post = {
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code': code,
            'code_verifier': code_verifier,
            'client_id': 'triple-web',
        }
        data = urllib.parse.urlencode(post).encode('utf-8')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'User-Agent': self.user_agent,
            'Origin': 'https://app.nlziet.nl',
            'Referer': 'https://app.nlziet.nl/',
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        with self._open_with_opener(self.opener, req, timeout=20) as r:
            resp = json.load(r)

        now = int(time.time())
        expires_in = int(resp.get('expires_in', 0) or 0)
        # capture potential fallback profile id returned by the token endpoint
        fallback_profile = resp.get('fallbackProfileId') or resp.get('fallback_profile_id') or resp.get('fallbackProfile')
        self.tokens = {
            'access_token': resp.get('access_token'),
            'refresh_token': resp.get('refresh_token'),
            'id_token': resp.get('id_token'),
            'token_type': resp.get('token_type'),
            'scope': resp.get('scope'),
            'expires_at': now + expires_in,
        }
        if fallback_profile:
            self.tokens['fallback_profile_id'] = fallback_profile
        self.save_tokens()
        self.token = self.tokens.get('access_token')
        return self.tokens

    def refresh_tokens(self):
        if not self.tokens.get('refresh_token'):
            return None
        url = 'https://id.nlziet.nl/connect/token'
        post = {
            'grant_type': 'refresh_token',
            'refresh_token': self.tokens.get('refresh_token'),
            'client_id': 'triple-web',
        }
        data = urllib.parse.urlencode(post).encode('utf-8')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'User-Agent': self.user_agent,
            'Origin': 'https://app.nlziet.nl',
            'Referer': 'https://app.nlziet.nl/',
        }
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                resp = json.load(r)
        except Exception:
            return None

        now = int(time.time())
        expires_in = int(resp.get('expires_in', 0) or 0)
        self.tokens.update({
            'access_token': resp.get('access_token'),
            'refresh_token': resp.get('refresh_token', self.tokens.get('refresh_token')),
            'id_token': resp.get('id_token'),
            'token_type': resp.get('token_type'),
            'scope': resp.get('scope'),
            'expires_at': now + expires_in,
        })
        self.save_tokens()
        self.token = self.tokens.get('access_token')
        return self.tokens

    def get_access_token(self):
        if self.tokens.get('access_token') and self.tokens.get('expires_at') and self.tokens['expires_at'] > int(time.time()) + 30:
            return self.tokens['access_token']
        refreshed = self.refresh_tokens()
        if refreshed and refreshed.get('access_token'):
            # If a profile was previously active, attempt to obtain a profile-scoped token
            profile_id = refreshed.get('profile_id') or self.tokens.get('profile_id')
            if not profile_id:
                try:
                    if os.path.exists(self.profile_file):
                        with open(self.profile_file, 'r', encoding='utf-8') as pf:
                            pfj = json.load(pf)
                        profile_id = pfj.get('profile_id') or pfj.get('profile') or pfj.get('id')
                except Exception:
                    profile_id = None

            if profile_id:
                try:
                    prof_tokens = self.select_profile(profile_id)
                    if prof_tokens and prof_tokens.get('access_token'):
                        return prof_tokens.get('access_token')
                except Exception:
                    pass

            return refreshed.get('access_token')
        return None

    def perform_pkce_authorize_and_exchange(self, redirect_uri='https://app.nlziet.nl/callback'):
        """Perform an authorize (PKCE) request using the addon's cookie session and exchange the returned code for tokens.

        This generates a code_verifier/code_challenge pair, calls the authorize endpoint with the current cookies,
        extracts the authorization code from the redirect and performs the token exchange.
        Returns the token dict on success or None on failure.
        """
        try:
            import base64, hashlib, secrets
            # generate PKCE pair (43-character verifier per RFC 7636 minimum)
            code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii')
            code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')
            state = secrets.token_hex(16)

            params = {
                'client_id': 'triple-web',
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': 'openid api',
                'state': state,
                'code_challenge': code_challenge,
                'code_challenge_method': 'S256'
            }
            qs = urllib.parse.urlencode(params, safe='')
            auth_url = 'https://id.nlziet.nl/connect/authorize/callback' + '?' + qs

            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener_no = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar), NoRedirect())
            opener_no.addheaders = [('User-Agent', self.user_agent)]
            req = urllib.request.Request(auth_url, headers={'User-Agent': self.user_agent, 'Accept': 'text/html'})

            code_val = None
            try:
                resp = self._open_with_opener(opener_no, req, timeout=20)
                loc = resp.getheader('Location')
                if loc:
                    parsed = urllib.parse.urlparse(loc)
                    qs2 = urllib.parse.parse_qs(parsed.query)
                    if 'code' in qs2:
                        code_val = qs2['code'][0]
            except urllib.error.HTTPError as e:
                loc = e.headers.get('Location')
                if loc:
                    parsed = urllib.parse.urlparse(loc)
                    qs2 = urllib.parse.parse_qs(parsed.query)
                    if 'code' in qs2:
                        code_val = qs2['code'][0]

            if not code_val:
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar), urllib.request.HTTPRedirectHandler())
                opener.addheaders = [('User-Agent', self.user_agent)]
                try:
                    resp2 = self._open_with_opener(opener, req, timeout=20)
                    final = resp2.geturl()
                    parsed = urllib.parse.urlparse(final)
                    qs2 = urllib.parse.parse_qs(parsed.query)
                    if 'code' in qs2:
                        code_val = qs2['code'][0]
                except Exception:
                    return None

            if not code_val:
                return None

            # exchange: obtain initial tokens
            tokens = self.exchange_code_for_tokens(code_val, code_verifier, redirect_uri=redirect_uri)
            if tokens:
                # attempt to select a profile (profile-grant) to obtain a profile-scoped token
                try:
                    stored_profile_id = None
                    if os.path.exists(self.profile_file):
                        with open(self.profile_file, 'r', encoding='utf-8') as f:
                            pf = json.load(f)
                        stored_profile_id = pf.get('profile_id') or pf.get('profile') or None
                except Exception:
                    stored_profile_id = None
                prof_tokens = None
                try:
                    prof_tokens = self.select_profile(stored_profile_id)
                    if prof_tokens:
                        return prof_tokens
                except Exception:
                    prof_tokens = None

                # fallback: if profile switch failed, try the fallbackProfileId returned
                # by the initial token response (if present)
                if not prof_tokens:
                    fb = tokens.get('fallback_profile_id') or self.tokens.get('fallback_profile_id')
                    if fb:
                        try:
                            prof_tokens = self.select_profile(fb)
                            if prof_tokens:
                                return prof_tokens
                        except Exception:
                            pass
            return tokens
        except Exception:
            return None

    def _get_csrf_token(self, html):
        m = re.search(r'name=["\']__RequestVerificationToken["\'][^>]*value=["\']([^"\']+)["\']', html)
        return m.group(1) if m else None

    def _get_jwt_exp(self, token):
        try:
            import base64
            parts = token.split('.')
            if len(parts) < 2:
                return None
            payload = parts[1]
            rem = len(payload) % 4
            if rem:
                payload += '=' * (4 - rem)
            decoded = base64.urlsafe_b64decode(payload.encode('ascii'))
            data = json.loads(decoded.decode('utf-8'))
            if 'exp' in data:
                return int(data['exp'])
        except Exception:
            return None
    def _parse_timestamp(self, value):
        """Parse various timestamp/date formats to epoch seconds (int) or None."""
        import datetime, re
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                v = int(value)
                if v > 10**12:
                    v = v // 1000
                if v > 10**9:
                    return v
        except Exception:
            pass
        if isinstance(value, str):
            s = value.strip()
            if re.fullmatch(r"\d+", s):
                try:
                    v = int(s)
                    if v > 10**12:
                        v = v // 1000
                    if v > 10**9:
                        return v
                except Exception:
                    pass
            try:
                if s.endswith('Z'):
                    s2 = s[:-1] + '+00:00'
                else:
                    s2 = s
                dt = datetime.datetime.fromisoformat(s2)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                return int(dt.timestamp())
            except Exception:
                pass
            fmts = [
                '%Y-%m-%dT%H:%M:%S.%f%z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
            ]
            for fmt in fmts:
                try:
                    dt = datetime.datetime.strptime(s, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                    return int(dt.timestamp())
                except Exception:
                    pass
        return None

    def get_profiles(self):
        """Return list of profiles for the current account (requires an access token)."""
        try:
            token = self.get_access_token()
            if not token:
                return []
            url = urllib.parse.urljoin(self.base_url, '/v7/profile')
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
                'Authorization': 'Bearer ' + token,
            }
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)
            return data or []
        except Exception:
            return []

    def select_profile(self, profile_id=None):
        """Perform an authorized profile-grant to obtain a profile-scoped access token."""
        try:
            # 1. Haal eerst het MASTER token op (we hebben dit nodig voor autorisatie)
            master_token = self.get_access_token()
            if not master_token:
                xbmc.log("NLZiet: No master token available for profile switch", xbmc.LOGERROR)
                return None

            profiles = self.get_profiles()
            chosen = None
            if profile_id:
                for p in profiles:
                    if p.get('id') == profile_id or p.get('profileId') == profile_id:
                        chosen = p
                        break
            
            if not chosen and profiles:
                chosen = profiles[0]
            
            if not chosen:
                return None
                
            pid = chosen.get('id') or chosen.get('profileId')

            # 2. De CRUCIALE fix: Voeg de master_token toe aan de headers
            url = 'https://id.nlziet.nl/connect/token'
            post = {
                'grant_type': 'profile',
                'profile': pid,
                'client_id': 'triple-web',
                'scope': 'openid api',
            }
            data = urllib.parse.urlencode(post).encode('utf-8')
            # Include only the required headers for the profile-grant: master token and UA
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer ' + master_token,
                'User-Agent': self.user_agent,
            }
            
            req = urllib.request.Request(url, data=data, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                resp = json.load(r)

            now = int(time.time())
            expires_in = int(resp.get('expires_in', 0) or 0)
            self.tokens.update({
                'access_token': resp.get('access_token'),
                'refresh_token': resp.get('refresh_token', self.tokens.get('refresh_token')),
                'expires_at': now + expires_in,
            })
            # remember which profile we switched to so other flows can reuse it
            try:
                self.tokens['profile_id'] = pid
            except Exception:
                pass

            self.save_tokens()
            self.token = self.tokens.get('access_token')
            
            # Sla het gekozen profiel op voor de volgende keer
            try:
                with open(self.profile_file, 'w', encoding='utf-8') as f:
                    json.dump({'profile_id': pid}, f)
            except: pass

            return self.tokens
        except Exception as e:
            xbmc.log(f"NLZiet: Profile switch failed: {e}", xbmc.LOGERROR)
            return None

    def login(self, return_url=None):
        """Perform form login against id.nlziet.nl and persist cookies.

        return_url: optional ReturnUrl value to include in the POST (if present in the login page,
                    the form's hidden ReturnUrl will be preferred).
        Returns True on success (heuristic), False otherwise.
        """
        if not self.username or not self.password:
            raise ValueError('Missing username or password')

        login_url = 'https://id.nlziet.nl/Account/Login'
        if return_url:
            login_url = login_url + '?' + urllib.parse.urlencode({'ReturnUrl': return_url})

        try:
            resp = self._open_with_opener(self.opener, login_url, timeout=15)
            html = resp.read().decode('utf-8', errors='ignore')

            token = self._get_csrf_token(html)
            m = re.search(r'name=["\']ReturnUrl["\'][^>]*value=["\']([^"\']+)["\']', html)
            form_return = urllib.parse.unquote(m.group(1)) if m else return_url

            post_data = {
                'EmailAddress': self.username,
                'Password': self.password,
                'button': 'login',
            }
            if form_return:
                post_data['ReturnUrl'] = form_return
            if token:
                post_data['__RequestVerificationToken'] = token

            data_bytes = urllib.parse.urlencode(post_data).encode('utf-8')
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': login_url,
                'Origin': 'https://id.nlziet.nl',
                'User-Agent': self.user_agent,
            }
            req = urllib.request.Request(login_url, data=data_bytes, headers=headers)
            resp2 = self._open_with_opener(self.opener, req, timeout=15)
            final_url = resp2.geturl()
            body = resp2.read().decode('utf-8', errors='ignore')

            # Heuristics: redirected away from login page, or page contains logout text
            success = False
            if final_url and 'login' not in final_url.lower():
                success = True
            if not success and re.search(r'logout|sign out|uitloggen', body, re.I):
                success = True

            self.save_cookies()
            if success:
                self.token = 'cookie-session'
                return True
            return False
        except Exception:
            return False

    def search(self, query, content_type='all'):
        if not query:
            return []
        try:
            # map incoming content_type to API contentType params (allow repeated keys)
            ct = (content_type or 'all').lower()
            if ct in ('episodes', 'episode', 'ep'):
                api_content_types = ['Episode']
            elif ct in ('movies', 'movie'):
                api_content_types = ['Movie']
            elif ct in ('series', 'tvshow', 'tv', 'show'):
                api_content_types = ['Series']
            else:
                api_content_types = ['Movie', 'Series']

            params = [
                ('searchTerm', query),
                ('limit', '999'),
                ('offset', '0'),
            ]
            for v in api_content_types:
                params.append(('contentType', v))

            url = urllib.parse.urljoin(self.base_url, '/v9/search') + '?' + urllib.parse.urlencode(params, doseq=True)
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            # If we have a cookie-session but no tokens yet, try to obtain tokens
            if not token and getattr(self, 'token', None) == 'cookie-session':
                try:
                    tokens = self.perform_pkce_authorize_and_exchange()
                    if tokens and tokens.get('access_token'):
                        token = tokens.get('access_token')
                except Exception:
                    token = None

            if token:
                headers['Authorization'] = 'Bearer ' + token

            # include active profile id when present
            try:
                if os.path.exists(self.profile_file):
                    with open(self.profile_file, 'r', encoding='utf-8') as pf_f:
                        pfj = json.load(pf_f)
                    profile_id = pfj.get('profile_id') or pfj.get('profile') or pfj.get('id')
                    if profile_id:
                        headers['X-Profile-Id'] = str(profile_id)
            except Exception:
                pass

            # debug: record headers being sent for troubleshooting
            try:
                self._append_debug(f"Search headers: {headers}")
            except Exception:
                pass

            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)
                results = []
                items = data.get('data') or data.get('results') or data.get('items') or []
                for item in items:
                    # item may contain 'item' or 'content' objects
                    src = item.get('item') if isinstance(item, dict) and item.get('item') else item.get('content') if isinstance(item, dict) and item.get('content') else item
                    if not isinstance(src, dict):
                        continue
                    content_id = src.get('id') or src.get('contentId') or src.get('content_id')
                    title = src.get('title') or src.get('name') or (item.get('analytics') or {}).get('assetName')
                    thumb = src.get('posterUrl') or (src.get('image') or {}).get('portraitUrl') or (src.get('image') or {}).get('landscapeUrl')
                    typ = src.get('type') or (item.get('content') or {}).get('type')
                    desc = src.get('description') or src.get('plot') or src.get('summary') or ''
                    subtitle = src.get('subtitle') or src.get('subtitleText') or ''
                    # detect expiration similar to get_movies
                    expires_at = None
                    for key in ('availableTo', 'available_to', 'availableUntil', 'available_until', 'endDate', 'end_date', 'expiresAt', 'expires_at', 'expiration', 'validUntil', 'valid_until', 'availableToDate', 'available_to_date'):
                        if isinstance(src, dict) and key in src and src.get(key):
                            parsed = self._parse_timestamp(src.get(key))
                            if parsed:
                                expires_at = parsed
                                break
                    if not expires_at:
                        availability = src.get('availability') or src.get('availabilities') or src.get('availabilityRange') or src.get('availableRanges')
                        if availability:
                            if isinstance(availability, dict):
                                for k in ('endDate', 'to', 'availableTo', 'end'):
                                    v = availability.get(k)
                                    if v:
                                        parsed = self._parse_timestamp(v)
                                        if parsed:
                                            expires_at = parsed
                                            break
                            elif isinstance(availability, (list, tuple)):
                                for a in availability:
                                    if isinstance(a, dict):
                                        v = a.get('endDate') or a.get('to') or a.get('availableTo') or a.get('end')
                                        if v:
                                            parsed = self._parse_timestamp(v)
                                            if parsed:
                                                expires_at = parsed
                                                break
                    expires_in = None
                    if expires_at:
                        now = int(time.time())
                        secs = expires_at - now
                        if secs <= 0:
                            expires_in = 'Expired'
                        else:
                            days = secs // 86400
                            if days >= 1:
                                expires_in = f'Expires in {days}d'
                            else:
                                hours = secs // 3600
                                if hours >= 1:
                                    expires_in = f'Expires in {hours}h'
                                else:
                                    minutes = max(1, secs // 60)
                                    expires_in = f'Expires in {minutes}m'
                    results.append({'id': content_id, 'title': title, 'thumb': thumb, 'type': typ, 'description': desc, 'subtitle': subtitle, 'posterUrl': thumb, 'expires_at': expires_at, 'expires_in': expires_in})
                return results
        except Exception as e:
            try:
                xbmc.log(f"NLZiet search error for query={query}: {e}", xbmc.LOGERROR)
            except Exception:
                pass
            try:
                import traceback
                self._append_debug(f"Search exception for query={query}: {traceback.format_exc()}")
            except Exception:
                pass
            return []

    def get_stream_info(self, content_id, context='OnDemand', playerName='BitmovinWeb', sourceType='Dash', preferLowLatency='false'):
        if not content_id:
            raise ValueError('content_id required')
        try:
            # Use the webapp's handshake endpoint to obtain manifest and DRM info
            # For Live contexts the handshake API expects a `channel` parameter
            # and `offsetType=Live` with a referer that contains `channel=...`.
            if str(context).lower() == 'live':
                params = {
                    'channel': content_id,
                    'playerName': playerName,
                    'context': 'Live',
                    'drmType': 'Widevine',
                    'sourceType': sourceType,
                    'consent': '',
                    'offsetType': 'Live',
                    'referer': f'https://app.nlziet.nl/play?context=Live&channel={content_id}',
                    'playerName': playerName,
                    'preferLowLatency': preferLowLatency,
                }
            else:
                params = {
                    'id': content_id,
                    'playerName': playerName,
                    'context': context,
                    'drmType': 'Widevine',
                    'sourceType': sourceType,
                    'consent': '',
                    'offsetType': 'Resume',
                    'referer': f'https://app.nlziet.nl/play?context={context}&id={content_id}',
                    'preferLowLatency': preferLowLatency,
                }
            url = urllib.parse.urljoin(self.base_url, '/v9/stream/handshake') + '?' + urllib.parse.urlencode(params)
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            # Include active profile id in handshake when known (use tokens first)
            try:
                profile_id = self.tokens.get('profile_id')
                if profile_id:
                    headers['X-Profile-Id'] = str(profile_id)
            except Exception:
                pass
            req = urllib.request.Request(url, headers=headers)
            xbmc.log(f"NLZiet get_stream_info request: {url} headers={headers}", xbmc.LOGDEBUG)
            try:
                with self._open_with_opener(self.opener, req, timeout=20) as r:
                    data = json.load(r)
            except urllib.error.HTTPError as he:
                # If unauthorized, try to obtain tokens via PKCE using the saved cookie session
                if he.code == 401:
                    xbmc.log(f"NLZiet handshake 401 for id={content_id}, attempting PKCE authorize+exchange", xbmc.LOGWARNING)
                    tokens = self.perform_pkce_authorize_and_exchange()
                    if tokens:
                        # rebuild Authorization header and retry once
                        token = self.get_access_token()
                        if token:
                            headers['Authorization'] = 'Bearer ' + token
                            req = urllib.request.Request(url, headers=headers)
                            with self._open_with_opener(self.opener, req, timeout=20) as r:
                                data = json.load(r)
                        else:
                            xbmc.log("NLZiet: token exchange succeeded but no access_token available", xbmc.LOGERROR)
                            raise
                    else:
                        xbmc.log("NLZiet: PKCE authorize+exchange failed (401)", xbmc.LOGERROR)
                        raise
                else:
                    raise

            try:
                xbmc.log("NLZiet handshake response: %s" % (json.dumps(data)[:1000]), xbmc.LOGDEBUG)
            except Exception:
                pass

            # Robustly extract a manifest URL from the handshake response.
            # Some handshakes use different keys or nest the URL inside objects/arrays.
            manifest = None
            for k in ('manifestUrl', 'manifest', 'manifestURL', 'mediaManifestUrl', 'playbackUrl', 'playbackURL', 'streamUrl', 'stream_url', 'mediaUrl', 'url', 'dashUrl', 'mpdUrl'):
                v = data.get(k)
                if v:
                    manifest = v
                    break

            # inspect common nested containers if direct keys didn't match
            if not manifest:
                for container in ('item', 'stream', 'playback', 'media', 'data', 'result', 'response'):
                    part = data.get(container)
                    if isinstance(part, dict):
                        for k in ('manifestUrl', 'manifest', 'manifestURL', 'mediaManifestUrl', 'playbackUrl', 'playbackURL', 'streamUrl', 'stream_url', 'mediaUrl', 'url', 'dashUrl', 'mpdUrl'):
                            v = part.get(k)
                            if v:
                                manifest = v
                                break
                        if manifest:
                            break
                    elif isinstance(part, list):
                        for entry in part:
                            if isinstance(entry, dict):
                                for k in ('manifestUrl', 'manifest', 'manifestURL', 'mediaManifestUrl', 'playbackUrl', 'playbackURL', 'streamUrl', 'stream_url', 'mediaUrl', 'url', 'dashUrl', 'mpdUrl'):
                                    v = entry.get(k)
                                    if v:
                                        manifest = v
                                        break
                                if manifest:
                                    break
                        if manifest:
                            break

            # As a last resort, recursively collect any http(s) URLs and pick the
            # most likely candidate (prefer .mpd / manifest / Policy= tokens).
            if not manifest:
                urls = []
                def collect_urls(obj):
                    if isinstance(obj, str):
                        if obj.startswith('http'):
                            urls.append(obj)
                    elif isinstance(obj, dict):
                        for vv in obj.values():
                            collect_urls(vv)
                    elif isinstance(obj, list):
                        for vv in obj:
                            collect_urls(vv)
                collect_urls(data)
                for u in urls:
                    try:
                        if '.mpd' in u or 'manifest' in u or 'Policy=' in u:
                            manifest = u
                            break
                    except Exception:
                        continue
                if not manifest and urls:
                    manifest = urls[0]
            drm = data.get('drm') or {}
            license_url = drm.get('licenseUrl') or drm.get('license_url')
            license_headers = drm.get('headers') or {}

            # collect subtitles exposed by the handshake (many items use OutOfBand VTT)
            try:
                raw_subs = data.get('subtitles') or data.get('item', {}).get('subtitles') or []
            except Exception:
                raw_subs = []
            subtitles = []
            try:
                if isinstance(raw_subs, (list, tuple)):
                    for s in raw_subs:
                        if isinstance(s, dict):
                            url = s.get('url') or s.get('uri') or s.get('file')
                            lang = s.get('lang') or s.get('language') or s.get('key')
                            name = s.get('name') or s.get('label') or None
                            auto = bool(s.get('isAutoSelected') or s.get('default') or s.get('auto') )
                            if url:
                                subtitles.append({'url': url, 'lang': lang, 'name': name, 'auto': auto})
                elif isinstance(raw_subs, dict):
                    # sometimes object with language keys
                    for k, v in raw_subs.items():
                        if isinstance(v, dict):
                            url = v.get('url') or v.get('uri') or v.get('file')
                            lang = v.get('lang') or k
                            name = v.get('name') or None
                            auto = bool(v.get('isAutoSelected') or v.get('default') or v.get('auto'))
                            if url:
                                subtitles.append({'url': url, 'lang': lang, 'name': name, 'auto': auto})
            except Exception:
                subtitles = []

            # Normalize license_headers into a simple dict[str, str] so playback
            # code can reliably build the 4-pipe license_key. Handle common
            # shapes returned by different APIs: dict, list of dicts, or
            # header-string.
            try:
                if isinstance(license_headers, list):
                    nh = {}
                    for h in license_headers:
                        if isinstance(h, dict):
                            name = h.get('name') or h.get('key') or h.get('header')
                            if not name:
                                # fallback: take first key/value pair
                                value = None
                                for k, v in h.items():
                                    name = k
                                    value = v
                                    break
                                if name:
                                    nh[str(name)] = '' if value is None else str(value)
                            else:
                                val = h.get('value') or h.get('val') or ''
                                nh[str(name)] = '' if val is None else str(val)
                        elif isinstance(h, str):
                            if ':' in h:
                                k, v = h.split(':', 1)
                                nh[k.strip()] = v.strip()
                            elif '=' in h:
                                k, v = h.split('=', 1)
                                nh[k.strip()] = v.strip()
                    license_headers = nh
                elif isinstance(license_headers, dict):
                    nh = {}
                    for k, v in license_headers.items():
                        if isinstance(v, list):
                            nh[str(k)] = ','.join(str(x) for x in v)
                        elif isinstance(v, dict):
                            nh[str(k)] = '' if v is None else str(v.get('value') or v.get('val') or json.dumps(v))
                        else:
                            nh[str(k)] = '' if v is None else str(v)
                    license_headers = nh
                elif isinstance(license_headers, str):
                    nh = {}
                    parts = [p for p in re.split(r'[\r\n;&]', license_headers) if p.strip()]
                    for p in parts:
                        if ':' in p:
                            k, v = p.split(':', 1)
                            nh[k.strip()] = v.strip()
                        elif '=' in p:
                            k, v = p.split('=', 1)
                            nh[k.strip()] = v.strip()
                    license_headers = nh
                else:
                    license_headers = {}
            except Exception:
                # best-effort: keep dict form if possible, else empty dict
                if not isinstance(license_headers, dict):
                    license_headers = {}

            is_drm = bool(drm and (license_url or license_headers))

            # attempt to detect DRM security level (L1/L3) from handshake fields
            drm_security = None
            possible_keys = ['securityLevel', 'security_level', 'securitylevel', 'requiredSecurity', 'protectionLevel', 'protection_level', 'security']
            for k in possible_keys:
                if k in drm:
                    val = drm.get(k)
                    if isinstance(val, str):
                        drm_security = val
                        break
                    if isinstance(val, dict):
                        if 'level' in val:
                            drm_security = val.get('level')
                            break
                        if 'security' in val:
                            drm_security = val.get('security')
                            break

            # also check top-level response fields if not found inside drm
            if not drm_security:
                for k in possible_keys:
                    if k in data:
                        v = data.get(k)
                        if isinstance(v, str):
                            drm_security = v
                            break
                        if isinstance(v, dict):
                            drm_security = v.get('level') or v.get('security')
                            if drm_security:
                                break

            # normalize to patterns like 'L1' or 'L3' when possible
            if isinstance(drm_security, str):
                m = re.search(r'(L[1-3])', drm_security, re.I)
                if m:
                    drm_security = m.group(1).upper()

            # Ensure the license request headers contain the same User-Agent and
            # the profile-scoped access token so the license proxy sees the
            # session-consistent identity.
            try:
                profile_token = self.get_access_token()
                if isinstance(license_headers, dict):
                    license_headers['User-Agent'] = self.user_agent
                    # If the handshake already supplies an Nlziet-License token,
                    # prefer it and avoid adding an Authorization header which
                    # differs from the browser/live behavior observed in the HAR.
                    lh_keys = set(k.lower() for k in license_headers.keys())
                    if profile_token and not any(k in lh_keys for k in ('nlziet-license', 'nlziet_license', 'nlzietlicense')):
                        license_headers['Authorization'] = 'Bearer ' + profile_token
            except Exception:
                pass

            return {
                'manifest': manifest,
                'is_drm': is_drm,
                'license_url': license_url,
                'license_headers': license_headers,
                'drm_security': drm_security,
                'drm_raw': drm,
                'subtitles': subtitles,
                'handshake': data,
            }
        except Exception as e:
            xbmc.log(f"NLZiet get_stream_info error for id={content_id}: {e}", xbmc.LOGERROR)
            xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
            return {
                'manifest': None,
                'is_drm': False,
                'license_url': None,
                'license_headers': {},
            }

    def get_channels(self):
        """Return the EPG channel list from /v9/epg/channels as a list of dicts.

        Each item contains at least `id`, `title`, `thumb`, `is_favorite` and
        `is_live_only` when available.
        """
        try:
            url = urllib.parse.urljoin(self.base_url, '/v9/epg/channels')
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)
            items = data.get('channels') or data.get('data') or []
            results = []
            for it in items:
                content = it.get('content') if isinstance(it, dict) and it.get('content') else it
                cid = None
                title = None
                thumb = None
                is_fav = False
                is_live = False
                try:
                    cid = content.get('id') or content.get('contentId') or content.get('content_id')
                    title = content.get('title') or content.get('name')
                    logo = content.get('logo') or {}
                    thumb = logo.get('normalUrl') or logo.get('flatUrl') or logo.get('darkUrl')
                    is_live = bool(content.get('isLiveOnly') or content.get('is_live_only'))
                except Exception:
                    pass
                try:
                    is_fav = bool(it.get('isFavorite') or it.get('is_favourite') or False)
                except Exception:
                    is_fav = False
                results.append({'id': cid, 'title': title, 'thumb': thumb, 'is_favorite': is_fav, 'is_live_only': is_live})
            return results
        except Exception as e:
            xbmc.log(f"NLZiet get_channels error: {e}", xbmc.LOGERROR)
            return []

    def get_current_programs(self, channel_ids=None, date=None):
        """Fetch EPG program locations for the given channels and return a mapping
        of channel_id -> current program info (title, description, start, end).

        - `channel_ids` may be a list of channel ids or a single id. If omitted,
          the endpoint will be called without channel filters.
        - `date` should be a string in YYYY-MM-DD format; if omitted today's
          date (local) is used.
        """
        try:
            import datetime

            if not date:
                date = datetime.date.today().isoformat()

            params = [('date', date)]
            if channel_ids:
                if isinstance(channel_ids, (list, tuple)):
                    for c in channel_ids:
                        if c:
                            params.append(('channel', str(c)))
                else:
                    params.append(('channel', str(channel_ids)))

            qs = urllib.parse.urlencode(params, doseq=True)
            url = urllib.parse.urljoin(self.base_url, '/v9/epg/programlocations') + '?' + qs

            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token

            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            # Identify list container in response
            items = None
            if isinstance(data, dict):
                for key in ('programLocations', 'programs', 'items', 'data', 'results'):
                    if key in data and isinstance(data.get(key), (list, tuple)):
                        items = data.get(key)
                        break
                if items is None:
                    # fallback: collect any lists found at top-level
                    collected = []
                    for v in data.values():
                        if isinstance(v, list):
                            collected.extend(v)
                    items = collected
            elif isinstance(data, list):
                items = data
            else:
                items = []

            epg_map = {}
            now_ts = int(time.time())

            for it in items:
                if not isinstance(it, dict):
                    continue

                # Attempt to determine channel id for this item
                channel = None
                for ck in ('channel', 'channelId', 'channel_id', 'channelCode', 'id'):
                    if ck in it and it.get(ck):
                        channel = it.get(ck)
                        break
                if not channel:
                    # try nested containers
                    for container in ('content', 'program', 'channelInfo'):
                        part = it.get(container)
                        if isinstance(part, dict):
                            for ck in ('channel', 'channelId', 'id', 'code'):
                                if ck in part and part.get(ck):
                                    channel = part.get(ck)
                                    break
                            if channel:
                                break

                # program object may be nested or the item itself
                program = None
                for pkey in ('program', 'programme', 'programItem', 'programLocation', 'item'):
                    if pkey in it and it.get(pkey):
                        program = it.get(pkey)
                        break
                if not program:
                    program = it

                # extract human fields
                title = program.get('title') or program.get('name') or program.get('programmeTitle') or ''
                desc = program.get('description') or program.get('summary') or program.get('shortDescription') or ''

                # parse start/end timestamps using existing helper
                start_ts = None
                end_ts = None
                for k in ('startTime', 'start', 'start_time', 'scheduledStart', 'startDateTime', 'from'):
                    if program.get(k):
                        parsed = self._parse_timestamp(program.get(k))
                        if parsed:
                            start_ts = parsed
                            break
                for k in ('endTime', 'end', 'end_time', 'scheduledEnd', 'endDateTime', 'to'):
                    if program.get(k):
                        parsed = self._parse_timestamp(program.get(k))
                        if parsed:
                            end_ts = parsed
                            break

                # fallback to item-level fields
                if not start_ts:
                    for k in ('startTime', 'start', 'from'):
                        if it.get(k):
                            parsed = self._parse_timestamp(it.get(k))
                            if parsed:
                                start_ts = parsed
                                break
                if not end_ts:
                    for k in ('endTime', 'end', 'to'):
                        if it.get(k):
                            parsed = self._parse_timestamp(it.get(k))
                            if parsed:
                                end_ts = parsed
                                break

                in_now = False
                if start_ts and end_ts:
                    if start_ts <= now_ts <= end_ts:
                        in_now = True
                else:
                    if program.get('isRunningNow') or program.get('isNow') or program.get('running'):
                        in_now = True

                if channel:
                    key = str(channel)
                    existing = epg_map.get(key)
                    # prefer entries that are running now; otherwise prefer later start
                    if existing:
                        if in_now and not existing.get('in_now'):
                            epg_map[key] = {'title': title, 'desc': desc, 'start': start_ts, 'end': end_ts, 'raw': program, 'in_now': in_now}
                        else:
                            try:
                                if start_ts and existing.get('start') and start_ts > existing.get('start'):
                                    epg_map[key] = {'title': title, 'desc': desc, 'start': start_ts, 'end': end_ts, 'raw': program, 'in_now': in_now}
                            except Exception:
                                pass
                    else:
                        epg_map[key] = {'title': title, 'desc': desc, 'start': start_ts, 'end': end_ts, 'raw': program, 'in_now': in_now}

            return epg_map
        except Exception as e:
            xbmc.log(f"NLZiet get_current_programs error: {e}", xbmc.LOGERROR)
            xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
            return {}

    def get_series_list(self, limit=999, offset=0):
        """Return a flat list of series using the recommend/filtered Series endpoint.

        Each item mirrors the shape used by get_movies/search: dict with
        `id`, `title`, `thumb`, `description`, `subtitle` when available.
        """
        try:
            url = urllib.parse.urljoin(self.base_url, f'/v9/recommend/filtered?category=Series&limit={limit}&offset={offset}')
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
                'nlziet-devicecapabilities': 'LowLatency,FutureItems,favoriteChannels,MyList,placementTile',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            try:
                if os.path.exists(self.profile_file):
                    with open(self.profile_file, 'r', encoding='utf-8') as pf_f:
                        pfj = json.load(pf_f)
                    profile_id = pfj.get('profile_id') or pfj.get('profile') or pfj.get('id')
                    if profile_id:
                        headers['X-Profile-Id'] = str(profile_id)
            except Exception:
                pass

            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            items = data.get('data') or data.get('results') or data.get('items') or []

            # Try to obtain seasons metadata from the episodes response itself
            # (some endpoints include `content.seasons`) so we can map global
            # episode numbers (Afl. N) to a particular season when episode
            # counts are provided.
            seasons_list = []
            try:
                content_container = data.get('content') if isinstance(data, dict) else None
                cs = None
                if isinstance(content_container, dict):
                    cs = content_container.get('seasons') or content_container.get('seasonList') or content_container.get('season_list')
                if not cs and isinstance(data.get('seasons'), list):
                    cs = data.get('seasons')
                if isinstance(cs, list) and cs:
                    for s in cs:
                        try:
                            sid = s.get('id') or s.get('seasonId') or s.get('season_id') or s.get('season') or ''
                            title_s = s.get('title') or s.get('name') or s.get('label') or (f"Season {sid}" if sid else '')
                            ep_count = s.get('episodeCount') or s.get('episode_count') or None
                            if ep_count is not None:
                                try:
                                    ep_count = int(ep_count)
                                except Exception:
                                    ep_count = None
                            seasons_list.append({'id': sid or title_s, 'title': title_s, 'episode_count': ep_count, 'start': None, 'end': None})
                        except Exception:
                            continue
                    # compute cumulative ranges for seasons that include episode counts
                    running = 0
                    for s in seasons_list:
                        if s.get('episode_count'):
                            s['start'] = running + 1
                            s['end'] = running + s['episode_count']
                            running = s['end']
            except Exception:
                seasons_list = []

            # If no seasons found in the episodes response, try to fetch the
            # series detail once to obtain a seasons list we can use for
            # mapping Afl. style global episode numbers to per-season numbering.
            if not seasons_list:
                try:
                    detail = self.get_series_detail(series_id) or {}
                    sd = detail.get('seasons') or []
                    if isinstance(sd, list) and sd:
                        running = 0
                        for s in sd:
                            try:
                                sid = s.get('id') or s.get('seasonId') or s.get('season_id') or s.get('season') or ''
                                title_s = s.get('title') or s.get('name') or s.get('label') or (f"Season {sid}" if sid else '')
                                ep_count = s.get('episode_count') or s.get('episodeCount') or None
                                if ep_count is not None:
                                    try:
                                        ep_count = int(ep_count)
                                    except Exception:
                                        ep_count = None
                                seasons_list.append({'id': sid or title_s, 'title': title_s, 'episode_count': ep_count, 'start': None, 'end': None})
                            except Exception:
                                continue
                        running = 0
                        for s in seasons_list:
                            if s.get('episode_count'):
                                s['start'] = running + 1
                                s['end'] = running + s['episode_count']
                                running = s['end']
                except Exception:
                    pass

            results = []
            for item in items:
                src = item.get('item') if isinstance(item, dict) and item.get('item') else item.get('content') if isinstance(item, dict) and item.get('content') else item
                if not isinstance(src, dict):
                    continue
                content_id = src.get('id') or src.get('contentId') or src.get('content_id')
                title = src.get('title') or src.get('name') or (item.get('analytics') or {}).get('assetName')
                thumb = src.get('posterUrl') or (src.get('image') or {}).get('portraitUrl') or (src.get('image') or {}).get('landscapeUrl')
                desc = src.get('description') or src.get('plot') or src.get('summary') or ''
                subtitle = src.get('subtitle') or src.get('subtitleText') or ''
                results.append({'id': content_id, 'title': title, 'thumb': thumb, 'description': desc, 'subtitle': subtitle})
            return results
        except Exception as e:
            xbmc.log(f"NLZiet get_series_list error: {e}", xbmc.LOGERROR)
            return []

    def get_placement_rows(self, placement_id='explore-series'):
        """Fetch placement rows (UI collections) such as the explore-series placement.

        Returns the placement JSON `components` list when available.
        """
        try:
            url = urllib.parse.urljoin(self.base_url, f'/v9/placement/rows/{placement_id}')
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            # components often appear under `components` or `rows`
            comps = data.get('components') or data.get('rows') or data.get('data') or []
            return comps
        except Exception as e:
            xbmc.log(f"NLZiet get_placement_rows error: {e}", xbmc.LOGERROR)
            return []

    def get_items_from_url(self, url):
        """Fetch an arbitrary recommend/filtered/items URL returned in placement rows.

        Returns a flat list of item content dicts (unified to the `src` content shape).
        """
        if not url:
            return []
        try:
            # Accept relative URLs too; coerce recommend endpoints to request more items.
            full = url if url.startswith('http') else urllib.parse.urljoin(self.base_url, url)
            try:
                parsed = urllib.parse.urlparse(full)
                path = parsed.path or ''
                # Only adjust known recommend endpoints and only when a limit
                # query parameter is explicitly present to avoid altering
                # unrelated URLs or nested/encoded queries.
                if 'recommend/withcontext' in path or 'recommend/filtered' in path:
                    qs = urllib.parse.parse_qs(parsed.query)
                    if 'limit' in qs:
                        try:
                            cur = int(qs.get('limit', ['0'])[0])
                        except Exception:
                            cur = 0
                        if cur < 999:
                            qs['limit'] = ['999']
                            new_q = urllib.parse.urlencode(qs, doseq=True)
                            parsed = parsed._replace(query=new_q)
                            full = urllib.parse.urlunparse(parsed)
            except Exception:
                pass
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            req = urllib.request.Request(full, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            items = data.get('data') or data.get('results') or data.get('items') or []
            results = []
            for item in items:
                src = item.get('item') if isinstance(item, dict) and item.get('item') else item.get('content') if isinstance(item, dict) and item.get('content') else item
                if not isinstance(src, dict):
                    continue
                results.append(src)
            return results
        except Exception as e:
            xbmc.log(f"NLZiet get_items_from_url error for {url}: {e}", xbmc.LOGERROR)
            return []

    def get_series_detail(self, series_id):
        """Fetch series detail (seasons + metadata) using the series detail endpoint.

        Returns a dict with at least `id`, `title`, `description`, `thumb`, and
        `seasons` (list of {id, title, episodes_url}).
        """
        if not series_id:
            return {}
        try:
            url = urllib.parse.urljoin(self.base_url, f'/v8/series/{series_id}')
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            # Attempt to extract title/description/thumb
            title = data.get('title') or data.get('name') or ''
            desc = data.get('description') or data.get('plot') or ''
            thumb = None
            try:
                img = data.get('posterUrl') or (data.get('image') or {})
                if isinstance(img, dict):
                    thumb = img.get('portraitUrl') or img.get('landscapeUrl') or img.get('posterUrl')
                elif isinstance(img, str):
                    thumb = img
            except Exception:
                thumb = None

            # If the API embeds an explicit `content.seasons` list prefer that
            # structure: each entry typically contains a title and episodeCount.
            try:
                content_container = data.get('content') if isinstance(data, dict) else None
                if isinstance(content_container, dict):
                    cs = content_container.get('seasons') or content_container.get('seasonList') or None
                    if isinstance(cs, list) and cs:
                        seasons = []
                        for s in cs:
                            try:
                                sid = s.get('id') or s.get('seasonId') or s.get('season_id') or s.get('season') or ''
                                title_s = s.get('title') or s.get('name') or s.get('label') or (f"Season {sid}" if sid else '')
                                ep_count = s.get('episodeCount') or s.get('episode_count') or None
                                episodes_url = s.get('episodesUrl') or s.get('episodes_url') or s.get('itemsUrl') or s.get('url') or None
                                seasons.append({'id': sid or title_s, 'title': title_s, 'episodes_url': episodes_url, 'episode_count': ep_count})
                            except Exception:
                                continue
                        if seasons:
                            return {'id': series_id, 'title': title, 'description': desc, 'thumb': thumb, 'seasons': seasons, 'raw': data}
            except Exception:
                pass
            seasons = []
            comps = data.get('components') or data.get('sections') or []
            if isinstance(comps, dict):
                comps = [comps]
            try:
                for comp in comps:
                    if not isinstance(comp, dict):
                        continue
                    if comp.get('type') == 'Sections' and isinstance(comp.get('items'), list):
                        for itm in comp.get('items'):
                            sid = None
                            season_title = itm.get('title') or itm.get('id') or ''
                            iid = itm.get('id') or ''
                            if isinstance(iid, str) and iid.startswith('season-'):
                                sid = iid.split('season-', 1)[1]
                            # search for components that contain an episodes url
                            episodes_url = None
                            for c2 in (itm.get('components') or []):
                                if not isinstance(c2, dict):
                                    continue
                                url_candidate = c2.get('url') or c2.get('itemsUrl') or c2.get('link', {}).get('href') if isinstance(c2.get('link', {}), dict) else None
                                if url_candidate and 'episodes' in str(url_candidate) and 'seasonId' in str(url_candidate):
                                    episodes_url = url_candidate
                                    # attempt to extract seasonId from url
                                    try:
                                        parsed = urllib.parse.urlparse(url_candidate)
                                        q = urllib.parse.parse_qs(parsed.query)
                                        season_ids = q.get('seasonId') or q.get('seasonid') or q.get('season')
                                        if season_ids:
                                            sid = season_ids[0]
                                    except Exception:
                                        pass
                                    break
                            if not sid:
                                # try to extract seasonId from any internal analytics or parameters
                                params = itm.get('analytics') or itm.get('parameters') or {}
                                if isinstance(params, dict):
                                    sid = params.get('seasonId') or params.get('season')
                            if sid:
                                seasons.append({'id': sid, 'title': season_title, 'episodes_url': episodes_url})
            except Exception:
                pass

            # If no explicit seasons discovered in the detail payload, attempt
            # to derive seasons by fetching episodes and grouping them by
            # season id/number. This mirrors the app behavior when the detail
            # endpoint provides a flat episode list instead of explicit season
            # sections.
            if not seasons:
                try:
                    eps = self.get_series_episodes(series_id, limit=1000, offset=0) or []
                    by_sid = {}
                    for ep in eps:
                        sid = ep.get('season_id') or ep.get('season') or ep.get('seasonNumber') or ep.get('season_number') or ''
                        # normalize to string key
                        key = str(sid) if sid is not None else ''
                        if key == 'None':
                            key = ''
                        if key == '':
                            key = '1'
                        if key not in by_sid:
                            # try to determine a human-friendly season number
                            snum = None
                            try:
                                snum = int(ep.get('season_number') or ep.get('seasonNumber') or (key if str(key).isdigit() else None))
                            except Exception:
                                snum = None
                            by_sid[key] = {'id': key, 'title': f"Season {snum}" if snum else f"Season {key}", 'episodes_url': None, 'season_number': snum}
                    if by_sid:
                        seasons = list(by_sid.values())
                        try:
                            seasons.sort(key=lambda x: (x.get('season_number') is None, x.get('season_number') or int(x.get('id') if str(x.get('id')).isdigit() else 0)))
                        except Exception:
                            pass
                except Exception:
                    pass

            return {'id': series_id, 'title': title, 'description': desc, 'thumb': thumb, 'seasons': seasons, 'raw': data}
        except Exception as e:
            xbmc.log(f"NLZiet get_series_detail error for id={series_id}: {e}", xbmc.LOGERROR)
            return {}

    def get_series_episodes(self, series_id, season_id=None, limit=400, offset=0):
        """Return episodes for a series/season using /v9/series/{id}/episodes."""
        if not series_id:
            return []
        try:
            params = {'limit': str(limit), 'offset': str(offset)}
            if season_id:
                params['seasonId'] = season_id
            qs = urllib.parse.urlencode(params)
            url = urllib.parse.urljoin(self.base_url, f'/v9/series/{series_id}/episodes') + '?' + qs
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://app.nlziet.nl/',
                'Origin': 'https://app.nlziet.nl',
                'nlziet-appname': 'WebApp',
                'nlziet-appversion': '6.0.3',
            }
            token = self.get_access_token()
            if token:
                headers['Authorization'] = 'Bearer ' + token
            req = urllib.request.Request(url, headers=headers)
            with self._open_with_opener(self.opener, req, timeout=20) as r:
                data = json.load(r)

            items = data.get('data') or data.get('results') or data.get('items') or []
            results = []
            for item in items:
                src = item.get('item') if isinstance(item, dict) and item.get('item') else item.get('content') if isinstance(item, dict) and item.get('content') else item
                if not isinstance(src, dict):
                    continue
                content_id = src.get('id') or src.get('contentId') or src.get('content_id')
                title = src.get('title') or src.get('name') or ''
                thumb = src.get('posterUrl') or (src.get('image') or {}).get('portraitUrl') or (src.get('image') or {}).get('landscapeUrl') or src.get('thumbnail') or src.get('thumb')
                desc = src.get('description') or src.get('plot') or src.get('summary') or ''
                subtitle = src.get('subtitle') or src.get('subtitleText') or ''
                duration = src.get('durationInSeconds') or src.get('duration') or None

                # Try to extract season/episode metadata from common fields and
                # fallbacks in item parameters/analytics.
                season_id = src.get('seasonId') or src.get('season_id') or src.get('season') or None
                season_number = src.get('seasonNumber') or src.get('season_number') or None
                episode_number = src.get('episodeNumber') or src.get('episode') or src.get('number') or src.get('episodeIndex') or None
                # fallback to analytics/parameters that sometimes include season/episode
                try:
                    params = (item.get('analytics') or item.get('parameters') or src.get('parameters') or {})
                    if isinstance(params, dict):
                        season_id = season_id or params.get('seasonId') or params.get('season') or params.get('season_id')
                        season_number = season_number or params.get('seasonNumber') or params.get('season_number')
                        episode_number = episode_number or params.get('episodeNumber') or params.get('episode') or params.get('number')
                except Exception:
                    pass

                # Release/availability timestamps
                release_date = src.get('availableFrom') or src.get('releaseDate') or src.get('publishedAt') or None
                available_from = src.get('availableFrom') or src.get('startAt') or None
                available_to = src.get('availableTo') or src.get('endAt') or None
                # Prefer pre-formatted episode numbering when present in the
                # payload (the official app exposes `formattedEpisodeNumbering`).
                formatted = None
                try:
                    # common top-level key
                    if isinstance(src, dict):
                        formatted = src.get('formattedEpisodeNumbering') or src.get('formatted_episode_numbering')
                    # inspect common nested containers
                    if not formatted:
                        for container in ('play', 'playback', 'item', 'seriesPlayEntity', 'video', 'data', 'asset'):
                            part = src.get(container) if isinstance(src, dict) else None
                            if isinstance(part, dict):
                                formatted = part.get('formattedEpisodeNumbering') or part.get('formatted_episode_numbering')
                                if formatted:
                                    break
                except Exception:
                    formatted = None

                # If the episode `subtitle` contains the canonical "S{season}:A{episode}"
                # pattern (e.g. 'S1:A1') parse and prefer those numbers.
                try:
                    if not formatted and subtitle and isinstance(subtitle, str):
                        m = re.search(r"S(\d+):A(\d+)", subtitle, re.I)
                        if m:
                            try:
                                s_val = int(m.group(1))
                                e_val = int(m.group(2))
                                season_number = season_number or s_val
                                episode_number = episode_number or e_val
                                # use a normalized formatted string like S01E01
                                formatted = f"S{ s_val:02d }E{ e_val:02d }"
                                # try to find human-friendly season title
                                season_title = None
                                try:
                                    for si, s in enumerate(seasons_list):
                                        snum = None
                                        sid = s.get('id')
                                        if sid and str(sid).isdigit():
                                            try:
                                                snum = int(sid)
                                            except Exception:
                                                snum = None
                                        if snum is None:
                                            m2 = re.search(r"(\d+)", str(s.get('title') or ''))
                                            if m2:
                                                try:
                                                    snum = int(m2.group(1))
                                                except Exception:
                                                    snum = None
                                        if snum == s_val:
                                            season_title = s.get('title')
                                            break
                                except Exception:
                                    season_title = None
                            except Exception:
                                pass
                except Exception:
                    pass

                # Handle Dutch "Afl. 7229" soap/daily format: treat as global
                # episode number. If we have seasons with episode counts we can
                # map the global number to a season and local episode number.
                try:
                    if not formatted and subtitle and isinstance(subtitle, str):
                        m = re.search(r"\bAfl\.?\s*(\d+)\b", subtitle, re.I)
                        if m:
                            try:
                                ep_global = int(m.group(1))
                            except Exception:
                                ep_global = None
                            if ep_global:
                                mapped = False
                                try:
                                    for idx, s in enumerate(seasons_list):
                                        if s.get('start') and s.get('end') and s['start'] <= ep_global <= s['end']:
                                            # determine season number if possible
                                            season_num = None
                                            sid = s.get('id')
                                            if sid and str(sid).isdigit():
                                                try:
                                                    season_num = int(sid)
                                                except Exception:
                                                    season_num = None
                                            if season_num is None:
                                                m2 = re.search(r"(\d+)", str(s.get('title') or ''))
                                                if m2:
                                                    try:
                                                        season_num = int(m2.group(1))
                                                    except Exception:
                                                        season_num = None
                                            local_ep = ep_global - s['start'] + 1
                                            season_number = season_number or season_num or (idx + 1)
                                            episode_number = episode_number or local_ep
                                            formatted = f"S{ season_number:02d }E{ local_ep:02d }"
                                            season_title = s.get('title')
                                            mapped = True
                                            break
                                except Exception:
                                    mapped = False
                                if not mapped:
                                    # fallback: present as a global episode
                                    episode_number = episode_number or ep_global
                                    formatted = f"Episode {ep_global}"
                except Exception:
                    pass

                results.append({
                    'id': content_id,
                    'title': title,
                    'thumb': thumb,
                    'description': desc,
                    'subtitle': subtitle,
                    'duration': duration,
                    'season_id': season_id,
                    'season_number': season_number,
                    'season_title': locals().get('season_title', None),
                    'episode_number': episode_number,
                    'formatted_episode_numbering': formatted,
                    'release_date': release_date,
                    'available_from': available_from,
                    'available_to': available_to,
                    'raw': src,
                })
            return results
        except Exception as e:
            xbmc.log(f"NLZiet get_series_episodes error for series={series_id} season={season_id}: {e}", xbmc.LOGERROR)
            return []
