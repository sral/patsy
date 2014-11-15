__author__ = 'Lars Djerf <lars.djerf@gmail.com>'

import hashlib
import json
import requests
import time


class Scrobbler(object):
    """Wrapper for the Last.fm API."""

    API_URL = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key, shared_secret):
        self.api_key = api_key
        self.shared_secret = shared_secret
        self.session_key = ""

    def _get_signature(self, payload):
        """Returns signature/hash for payload

        Keyword argument(s):
        payload -- Payload dictionary
        """

        message = ""
        for k in sorted(payload):
            message += k + payload[k]
        message += self.shared_secret

        return hashlib.md5(message).hexdigest()

    def _post(self, payload, format="json"):
        """Sign payload and make API request.

        Keyword argument(s):
        payload -- Payload dictionary
        format: -- Response format
        """
        payload["api_sig"] = self._get_signature(payload)
        payload["format"] = format

        return requests.post(self.API_URL, data=payload)

    def authenticate(self, username, password):
        """Authenticate user.

        Keyword argument(s):
        username -- Last.fm username
        password -- Last.fm password
        """
        payload = {"method": "auth.getMobileSession",
                   "password": password,
                   "username": username,
                   "api_key": self.api_key}
        self.session_key = ""

        response = self._post(payload)
        if response.status_code == 200:
            response = json.loads(response.text)
            if not response.get("error"):
                self.session_key = response["session"]["key"]
                return True
        return False

    def now_playing(self, artist, track):
        """Update now playing.

        Keyword argument(s):
        artist -- Artist name
        track -- Song name
        """
        if not self.session_key:
            return False

        payload = {"method": "track.updateNowPlaying",
                   "artist": artist,
                   "track": track,
                   "api_key": self.api_key,
                   "sk": self.session_key}

        response = self._post(payload)
        return response.status_code == 200

    def scrobble(self, artist, track):
        """Scrobble play.

        Keyword argument(s):
        artist -- Artist name
        track -- Song name
        """
        if not self.session_key:
            return False

        payload = {"method": "track.scrobble",
                   "artist": artist,
                   "track": track,
                   "timestamp": str(int(time.time())),
                   "api_key": self.api_key,
                   "sk": self.session_key}

        response = self._post(payload)
        return response.status_code == 200
