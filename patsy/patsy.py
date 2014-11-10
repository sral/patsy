__author__ = 'Lars Djerf <lars.djerf@gmail.com>'

import argparse
import errno
import json
import pyinotify
import re
import sys

from scrobbler import Scrobbler


class EventHandler(pyinotify.ProcessEvent):
    RE_START_PLAYING = re.compile("Track event: start of (.+) -- (.+)")
    tracked_file = None
    scrobbler = None

    def my_init(self, scrobbler, tracked_file):
        """Initialize event handler.

        Keyword argument(s):
        scrobbler: Last.fm scrobbler instance
        tracked_file: File object
        """
        tracked_file.read()  # Move to the end of the file
        self.tracked_file = tracked_file
        self.scrobbler = scrobbler

    def process_IN_MODIFY(self, event):
        """Process modification event.

        Keyword argument(s):
        event -- Pyinotify event
        """
        match = re.search(self.RE_START_PLAYING, self.tracked_file.read())
        if match:
            artist, track = match.groups()
            self.scrobbler.now_playing(artist, track)
            # Ideally this should happen after the track has been
            # playing for half it's duration, or for 4 minutes (whichever
            # occurs earlier). We don't have that information at the moment.
            self.scrobbler.scrobble(artist, track)


class Patsy(object):
    @staticmethod
    def setup_scrobbler(api_key, shared_secret, username, password):
        """Returns Last.fm scrobbler.

        Keyword argument(s):
        :param api_key: Last.fm API key
        :param shared_secret: Last.fm API shared secret
        :param username: Last.fm username
        :param password: Last.fm password
        """
        scrobbler = Scrobbler(api_key=api_key, shared_secret=shared_secret)
        result = scrobbler.authenticate(username, password)
        if not result:
            print "Last.fm authentication failed."
            sys.exit(errno.EACCES)
        return scrobbler

    @staticmethod
    def parse_arguments():
        parser = argparse.ArgumentParser(
            description="Monitor a logfile for music playback and "
                        "Last.fm-scrobble plays.")

        parser.add_argument("-l", "--logfile", metavar="FILE", required=True,
                            help="logfile to track")
        parser.add_argument("-d", "--daemon", dest="daemon", default=False,
                            action="store_true",
                            help="run as daemon")
        parser.add_argument("-c", "--config", metavar="CONFIG",
                            required=True, help="Path to configuration file")
        return parser.parse_args()

    def run(self):
        """Run Patsy"""

        args = self.parse_arguments()
        config = None

        try:
            with open(args.config, "r") as f:
                config = json.loads(f.read())

            api_key = config.get("last_fm_api_key")
            shared_secret = config.get("last_fm_shared_secret")
            username = config.get("last_fm_username")
            password = config.get("last_fm_password")
            scrobbler = self.setup_scrobbler(api_key, shared_secret, username,
                                             password)
            watch_manager = pyinotify.WatchManager()
            with open(args.logfile, "r") as f:
                event_handler = EventHandler(scrobbler=scrobbler,
                                             tracked_file=f)
                notifier = pyinotify.Notifier(watch_manager, event_handler)
                watch_manager.add_watch(args.logfile, pyinotify.IN_MODIFY)
                notifier.loop(daemonize=args.daemon,
                              pid_file='/tmp/pyinotify.pid')
        except IOError as e:
            print "Failed to open '{0}': {1}".format(e.filename, e.strerror)
            sys.exit(e.errno)
        sys.exit(0)


def main_func():
    patsy = Patsy()
    patsy.run()


if __name__ == "__main__":
    p = Patsy()
    p.run()