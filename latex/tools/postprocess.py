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
tools.postprocess
"""

import logging
import re

from ..issues import Issue
from ..util import escape


class PostProcessor(object):
    """
    The contract for a post-processor
    """

    def process(self, file, stdout, stderr, condition):
        """
        @param file: the File processed by the Tool
        @param stdout: the output written to STDOUT
        @param stderr: the output written to STDERR
        @param condition: the exit condition of the Tool process
        """
        raise NotImplementedError

    @property
    def successful(self):
        """
        Return whether the Tool process was successful
        """
        raise NotImplementedError

    @property
    def issues(self):
        """
        Return a list of Issues
        """
        raise NotImplementedError

    @property
    def summary(self):
        """
        Return a short string summarizing the result of the Tool process
        """
        raise NotImplementedError


class GenericPostProcessor(PostProcessor):
    """
    This just interprets the exit condition of the process
    """

    _log = logging.getLogger(__name__ + ".GenericPostProcessor")

    name = "GenericPostProcessor"

    def __init__(self):
        self._issues = None
        self._summary = None

    def process(self, file, stdout, stderr, condition):
        self._issues = []
        self._summary = ""
        self._condition = condition

    @property
    def successful(self):
        return not bool(self._condition)

    @property
    def issues(self):
        return self._issues

    @property
    def summary(self):
        return self._summary


class LaTeXPostProcessor(PostProcessor):
    """
    This post-processor generates messages from a standard LaTeX log with
    default error format (NOT using "-file-line-error")
    """

    _log = logging.getLogger(__name__ + ".LatexPostProcessor")

    name = "LaTeXPostProcessor"

    _PATTERN = pattern = re.compile(r"(^! (?P<text>.*?)$)|(^l\.(?P<line>[0-9]+))", re.MULTILINE)

    def __init__(self):
        self._successful = False

    def process(self, file, stdout, stderr, condition):
        self._file = file
        self._successful = not bool(condition)

    @property
    def successful(self):
        return self._successful

    @property
    def summary(self):
        return self._summary

    @property
    def issues(self):
        try:
            log = open("%s.log" % self._file.shortname).read()

            # check for wrong format
            if log.find("file:line:error") > 0:
                return [Issue("The file:line:error format is not supported. Please remove that switch.", None, None, self._file, Issue.SEVERITY_ERROR)]

            # process log file and extract tuples like (message, line)
            tuples = []
            for match in self._PATTERN.finditer(log):
                if match.group("text"):
                    tuple = [match.group("text"), 0]
                elif match.group("line"):
                    tuple[1] = match.group("line")
                    tuples.append(tuple)

            # generate issues from tuples
            self._issues = []
            for tuple in tuples:
                text = tuple[0]
                line = int(tuple[1]) - 1
                self._issues.append(Issue(text, line, None, self._file, Issue.SEVERITY_ERROR, Issue.POSITION_LINE))

            return self._issues

        except IOError:
            return [Issue("No LaTeX log file found", None, None, self._file, Issue.SEVERITY_ERROR)]


class RubberPostProcessor(PostProcessor):
    """
    This is a post-processor for rubber
    """

    _log = logging.getLogger(__name__ + ".RubberPostProcessor")

    name = "RubberPostProcessor"

    _pattern = re.compile(r"(?P<file>[a-zA-Z0-9./_-]+)(:(?P<line>[0-9\-]+))?:(?P<text>.*?)$", re.MULTILINE)

    def __init__(self):
        self._issues = None
        self._summary = None
        self._successful = False

        # FIXME: circ dep
        from ..preferences import Preferences

        self._hide_box_warnings = Preferences().get("hide-box-warnings")

    @property
    def successful(self):
        return self._successful

    @property
    def issues(self):
        return self._issues

    @property
    def summary(self):
        return self._summary

    def process(self, file, stdout, stderr, condition):
        from ..file import File        # FIXME: this produces a circ dep on toplevel

        self._issues = []

        self._log.debug("process(): stdout=\"%s\", stderr=\"%s\"" % (stdout, stderr))

        self._successful = not bool(condition)

        for match in self._pattern.finditer(stderr):
            severity = Issue.SEVERITY_ERROR

            # text
            text = match.group("text")

            if "Underfull" in text or "Overfull" in text:
                if self._hide_box_warnings:
                    continue
                else:
                    severity = Issue.SEVERITY_WARNING

            # line(s)
            lineFrom, lineTo = None, None

            line = match.group("line")

            if line:
                parts = line.split("-")
                lineFrom = int(parts[0]) - 1
                if len(parts) > 1:
                    lineTo = int(parts[1]) - 1

            # filename
            filename = "%s/%s" % (file.dirname, match.group("file"))

            self._issues.append(Issue(escape(text), lineFrom, lineTo, File(filename), severity, Issue.POSITION_LINE))



# ex:ts=4:et:
