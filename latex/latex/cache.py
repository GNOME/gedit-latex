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
latex.cache

Cache for LaTeX document models for speeding up reference expanding
"""

from logging import getLogger

from .parser import LaTeXParser
from ..issues import IIssueHandler


class CacheIssueHandler(IIssueHandler):
    """
    This is used to catch the issues occuring while parsing a document
    on cache fault.
    """
    def __init__(self):
        self.issues = []

    def clear(self):
        self.issues = []

    def issue(self, issue):
        self.issues.append(issue)


class LaTeXDocumentCache(object):
    """
    This caches LaTeX document models. It used to speed up
    the LaTeXReferenceExpander.
    """

    # FIXME: we need a global character set

    # TODO: serialize the cache on shutdown

    _log = getLogger("LaTeXDocumentCache")

    class Entry(object):
        """
        An entry in the cache
        """
        _log = getLogger("LaTeXDocumentCache.Entry")

        def __init__(self, file, charset):
            self.__file = file
            self.__parser = LaTeXParser()
            self.__issue_handler = CacheIssueHandler()
            self.__mtime = 0
            self.__document = None
            self.__charset = charset

            self.synchronize()

        @property
        def modified(self):
            return (self.__file.mtime > self.__mtime)

        @property
        def document(self):
            return self.__document

        @property
        def issues(self):
            return self.__issue_handler.issues

        def synchronize(self):
            """
            Synchronize document model with file contents.

            @raise OSError: if the file is not found
            """
            # update timestamp
            self.__mtime = self.__file.mtime

            # clear previous data
            self.__issue_handler.clear()
            if self.__document != None:
                self.__document.destroy()
                self.__document = None

            # read file
            try:
                f = open(self.__file.path, "r", encoding=self.__charset)
                try:
                    content = f.read()
                finally:
                    f.close()
            except IOError:
                return

            # parse
            self.__document = self.__parser.parse(content, self.__file, self.__issue_handler)

    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        if not '_ready' in dir(self):
            self._entries = {}
            self._ready = True

    def get_document(self, file, charset, issue_handler):
        """
        Return the (hopefully) cached document model for a given file

        @param file: a File object
        @param charset: character set
        @param issue_handler: an IIssueHandler to use
        """
        try:
            # update entry if necessary
            entry = self._entries[file.uri]
            self._log.debug("Reading '%s' from cache" % file)
            if entry.modified:
                self._log.debug("File '%s' modified, synchronizing..." % file)
                entry.synchronize()
        except KeyError:
            self._log.debug("Cache fault for '%s'" % file)
            # create new entry
            entry = self.Entry(file, charset)
            self._entries[file.uri] = entry

        # pass cached issues to the issue handler
        for issue in entry.issues:
            issue_handler.issue(issue)

        return entry.document



# ex:ts=4:et:
