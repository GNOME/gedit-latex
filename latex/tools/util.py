# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2010 Michael Zeising
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public Licence as published by the Free Software
# Foundation; either version 2 of the Licence, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public Licence for more
# details.
#
# You should have received a copy of the GNU General Public Licence along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA  02110-1301, USA

"""
tools.util
"""

import logging
import os
import signal
import subprocess
import fcntl

from gi.repository import GObject

LOG = logging.getLogger(__name__)

class Process(object):
    """
    This runs a command in a child process and polls the output
    """

    # intervall of polling stdout of the child process
    __POLL_INTERVAL = 250

    def execute(self, command):
        LOG.debug("execute: %s" % command)

        # run child process
        self.__process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

        # unblock pipes
        fcntl.fcntl(self.__process.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(self.__process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)

        # monitor process and pipes
        self.__handlers = [ GObject.timeout_add(self.__POLL_INTERVAL, self.__on_stdout),
                            GObject.timeout_add(self.__POLL_INTERVAL, self.__on_stderr),
                            GObject.child_watch_add(self.__process.pid, self.__on_exit) ]

    def abort(self):
        """
        Abort the running process
        """
        if self.__process:
            for handler in self.__handlers:
                GObject.source_remove(handler)

            try:
                os.kill(self.__process.pid, signal.SIGTERM)

                self._on_abort()
            except OSError as e:
                LOG.error("Failed to abort process: %s" % e)

    def __on_stdout(self):
        try:
            s = self.__process.stdout.read()
            if s != None:
                self._on_stdout(s.decode())
        except IOError:
            pass
        return True

    def __on_stderr(self):
        try:
            s = self.__process.stderr.read()
            if s != None:
                self._on_stderr(s.decode())
        except IOError:
            pass
        return True

    def __on_exit(self, pid, condition):
        for handler in self.__handlers:
            GObject.source_remove(handler)

        # read remaining output
        self.__on_stdout()
        self.__on_stderr()

        self._on_exit(condition)

    def _on_stdout(self, text):
        """
        To be overridden
        """

    def _on_stderr(self, text):
        """
        To be overridden
        """

    def _on_abort(self):
        """
        To be overridden
        """

    def _on_exit(self, condition):
        """
        To be overridden
        """


# ex:ts=4:et:
