__author__ = 'Lars Djerf <lars.djerf@gmail.com>'

import argparse
import errno
import os
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
        scrobbler.authenticate(username, password)
        return scrobbler

    def run(self):
        """Run Patsy"""

        parser = argparse.ArgumentParser(
            description="Monitor a logfile for music playback and "
                        "Last.fm-scrobble plays.")
        parser.add_argument("-u", "--username", metavar="USERNAME",
                            required=True, help="Last.fm username")
        parser.add_argument("-p", "--password", metavar="PASSWORD",
                            required=True, help="Last.fm password")
        parser.add_argument("-a", "--api-key", metavar="API_KEY",
                            required=True, help="Last.fm API key")
        parser.add_argument("-s", "--shared-secret", metavar="SHARED_SECRET",
                            required=True, help="Last.fm API shared secret")
        parser.add_argument("-l", "--logfile", metavar="FILE", required=True,
                            help="logfile to track")
        parser.add_argument("-d", "--daemon", dest="daemon", default=False,
                            action="store_true",
                            help="run as daemon")
        args = parser.parse_args()

        if not os.path.exists(args.logfile):
            print "No such file: {0}".format(args.logfile)
            sys.exit(errno.ENOENT)

        scrobbler = self.setup_scrobbler(args.api_key, args.shared_secret,
                                         args.username, args.password)
        watch_manager = pyinotify.WatchManager()
        with open(args.logfile, "r") as tracked_file:
            event_handler = EventHandler(scrobbler=scrobbler,
                                         tracked_file=tracked_file)
            notifier = pyinotify.Notifier(watch_manager, event_handler)
            watch_manager.add_watch(args.logfile, pyinotify.IN_MODIFY)
            notifier.loop(daemonize=args.daemon, pid_file='/tmp/pyinotify.pid')
        sys.exit(0)


def main_func():
    patsy = Patsy()
    patsy.run()

if __name__ == "__main__":
    p = Patsy()
    p.run()