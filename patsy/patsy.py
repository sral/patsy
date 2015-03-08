__author__ = 'Lars Djerf <lars.djerf@gmail.com>'

import argparse
import errno
import json
import logging
import logging.handlers
import os
import pyinotify
import re
import sys

from scrobbler import Scrobbler, ScrobblerException

log = logging.getLogger(__name__)


class EventHandler(pyinotify.ProcessEvent):
    RE_START_PLAYING = re.compile("Track event: start of (.+) -- (.+)")
    tracked_file = None
    scrobbler = None

    def my_init(self, scrobbler, tracked_file):
        """Initialize event handler.

        Keyword argument(s):
        scrobbler -- Last.fm scrobbler instance
        tracked_file -- File object
        """
        tracked_file.read()  # Move to the end of the file
        self.tracked_file = tracked_file
        self.scrobbler = scrobbler

    # noinspection PyPep8Naming
    def process_IN_MODIFY(self, event):
        """Process modification event.

        Keyword argument(s):
        event -- Pyinotify event
        """
        match = re.search(self.RE_START_PLAYING, self.tracked_file.read())
        if match:
            artist, track = match.groups()
            try:
                self.scrobbler.now_playing(artist, track)
                # Ideally this should happen after the track has been
                # playing for half it's duration, or for 4 minutes (whichever
                # occurs earlier). We don't have that information at the
                # moment.
                self.scrobbler.scrobble(artist, track)
            except ScrobblerException:
                log.error("Failed to scrobble: {0} - {1}".format(
                    artist, track))


class Patsy(object):
    @staticmethod
    def setup_scrobbler(api_key, shared_secret, username, password,
                        max_retries, max_retry_delay):
        """Returns Last.fm scrobbler.

        Keyword argument(s):
        api_key -- Last.fm API key
        shared_secret -- Last.fm API shared secret
        username -- Last.fm username
        password -- Last.fm password
        max_retries -- Maximum number of retries
        max_delay -- Maximum delay between retries
        """
        scrobbler = Scrobbler(api_key, shared_secret, max_retries,
                              max_retry_delay)
        result = scrobbler.authenticate(username, password)
        if not result:
            log.error("Last.fm authentication failed")
            sys.exit(errno.EACCES)
        return scrobbler

    @staticmethod
    def setup_logger():
        log.setLevel(logging.INFO)
        handler = logging.handlers.SysLogHandler(
            address="/dev/log",
            facility=logging.handlers.SysLogHandler.LOG_DAEMON)
        handler.setFormatter(logging.Formatter(
            "%(module)s[%(process)d]: %(name)s: %(message)s"))
        log.addHandler(handler)

    @staticmethod
    def parse_arguments():
        """Parse and return command-line arguments"""

        parser = argparse.ArgumentParser(
            description="Monitor a logfile for music playback and "
                        "Last.fm-scrobble plays.")

        parser.add_argument("-l", "--logfile", metavar="FILE", required=True,
                            help="logfile to track")
        parser.add_argument("-d", "--daemon", dest="daemon", default=False,
                            action="store_true",
                            help="run as daemon")
        parser.add_argument("-c", "--config", metavar="CONFIG",
                            required=True, help="path to configuration file")
        parser.add_argument("-s", "--syslog", dest="syslog", default=False,
                            action="store_true", required=False,
                            help="enable logging to syslog")
        return parser.parse_args()

    def run(self):
        """Run Patsy"""

        args = self.parse_arguments()
        if args.syslog:
            self.setup_logger()

        try:
            with open(args.config, "r") as f:
                config = json.loads(f.read())

            api_key = config.get("last_fm_api_key")
            shared_secret = config.get("last_fm_shared_secret")
            username = config.get("last_fm_username")
            password = config.get("last_fm_password")
            max_retries = config.get("max_retries", 3)
            max_retry_delay = config.get("max_retry_delay", 3)
            scrobbler = self.setup_scrobbler(api_key, shared_secret, username,
                                             password, max_retries,
                                             max_retry_delay)
            watch_manager = pyinotify.WatchManager()
            with open(args.logfile, "r") as f:
                event_handler = EventHandler(scrobbler=scrobbler,
                                             tracked_file=f)
                notifier = pyinotify.Notifier(watch_manager, event_handler)
                watch_manager.add_watch(args.logfile, pyinotify.IN_MODIFY)
                pid_file = "/tmp/patsy.pid" if os.geteuid() else None
                notifier.loop(daemonize=args.daemon, pid_file=pid_file)
        except IOError as e:
            log.error("Failed to open file '{1}'".format(e.filename))
            sys.exit(e.errno)
        sys.exit(0)


def main_func():
    patsy = Patsy()
    patsy.run()


if __name__ == "__main__":
    p = Patsy()
    p.run()