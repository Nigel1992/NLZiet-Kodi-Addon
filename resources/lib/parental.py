"""Parental control: a PIN for chosen profiles and, optionally, for live tv.

Set-up for a family: make the kids profile active, protect the adult
profiles with the PIN, and optionally lock live tv and the TV guide. Then
switching to an adult profile (or opening live tv) asks for the PIN.

The PIN is never stored in plain text: only a salted SHA-256 hash is kept in
the add-on settings. After a correct PIN the lock stays open for a while
(``UNLOCK_MINUTES``) so zapping does not ask again every time.

Note: Kodi cannot lock an add-on's settings screen itself; use Kodi's own
master lock (Settings > Profiles) to protect that as well.
"""

import hashlib
import hmac
import os
import time

UNLOCK_MINUTES = 30
UNLOCK_PROPERTY = 'nlziet.parental.unlocked_until'


def hash_pin(pin, salt):
    return hashlib.sha256((salt + ':' + str(pin)).encode('utf-8')).hexdigest()


class Parental:
    """``settings`` is the add-on object (getSetting/setSetting);
    ``window`` keeps the temporary unlock (Kodi home window properties)."""

    def __init__(self, settings, window=None, now=None):
        self.settings = settings
        self.window = window
        self.now = now or time.time

    # ---------------------------------------------------------------- the PIN
    def has_pin(self):
        return bool(self.settings.getSetting('parental_pin_hash'))

    def verify(self, pin):
        stored = self.settings.getSetting('parental_pin_hash')
        salt = self.settings.getSetting('parental_pin_salt')
        if not stored or not pin:
            return False
        return hmac.compare_digest(stored, hash_pin(pin, salt))

    def set_pin(self, pin):
        salt = os.urandom(8).hex()
        self.settings.setSetting('parental_pin_salt', salt)
        self.settings.setSetting('parental_pin_hash', hash_pin(pin, salt))

    def clear_pin(self):
        self.settings.setSetting('parental_pin_hash', '')
        self.settings.setSetting('parental_pin_salt', '')
        self.settings.setSetting('parental_protected_profiles', '')
        self.lock()

    # ------------------------------------------------------- temporary unlock
    def is_unlocked(self):
        if self.window is None:
            return False
        try:
            return float(self.window.getProperty(UNLOCK_PROPERTY) or 0) > self.now()
        except (TypeError, ValueError):
            return False

    def unlock(self):
        if self.window is not None:
            self.window.setProperty(UNLOCK_PROPERTY, str(self.now() + UNLOCK_MINUTES * 60))

    def lock(self):
        if self.window is not None:
            self.window.clearProperty(UNLOCK_PROPERTY)

    # ----------------------------------------------------------------- policy
    def protected_profiles(self):
        value = self.settings.getSetting('parental_protected_profiles') or ''
        return {part for part in value.split(',') if part}

    def is_profile_protected(self, profile_id):
        return self.has_pin() and str(profile_id) in self.protected_profiles()

    def toggle_profile(self, profile_id):
        profiles = self.protected_profiles()
        profile_id = str(profile_id)
        if profile_id in profiles:
            profiles.discard(profile_id)
        else:
            profiles.add(profile_id)
        self.settings.setSetting('parental_protected_profiles', ','.join(sorted(profiles)))
        return profile_id in profiles

    def live_locked(self):
        value = self.settings.getSetting('parental_lock_live')
        return self.has_pin() and value in ('true', '1', 'yes', True)

    def needs_pin(self, profile_id=None, live=False):
        if not self.has_pin() or self.is_unlocked():
            return False
        if live:
            return self.live_locked()
        return profile_id is not None and self.is_profile_protected(profile_id)

    def ask(self, prompt, tries=3):
        """Ask for the PIN through ``prompt()`` (returns the typed text)."""
        for _attempt in range(tries):
            pin = prompt()
            if not pin:
                return False
            if self.verify(pin):
                self.unlock()
                return True
        return False


def is_kids_profile(profile):
    """True when NLZiet marks a profile as a kids profile."""
    if not isinstance(profile, dict):
        return False
    for key in ('isKidsProfile', 'isKids', 'kids', 'isChild', 'child', 'kidsProfile'):
        if profile.get(key) is True:
            return True
    kind = str(profile.get('type') or profile.get('profileType') or '').lower()
    return 'kid' in kind or 'child' in kind or 'junior' in kind
