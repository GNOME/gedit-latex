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
bibtex.cache
"""

from logging import getLogger

from .parser import BibTeXParser
from ..issues import MockIssueHandler


class BibTeXDocumentCache(object):
    """
    This is used to cache BibTeX document models.

    This is only used in the context of code completion and validation for LaTeX documents
    but not when editing a BibTeX file.

    Of course, this must be implemented as a singleton class.
    """

    # TODO: serialize the cache on shutdown

    _log = getLogger("BibTeXDocumentCache")

    class Entry(object):
        """
        An entry in the cache
        """
        _log = getLogger("bibtex.cache.BibTeXDocumentCache.Entry")

        def __init__(self, file):
            self.__file = file
            self.__parser = BibTeXParser(quiet=True)
            self.__issue_handler = MockIssueHandler()
            self.__mtime = 0
            self.__document = None

            self.synchronize()

        @property
        def modified(self):
            return (self.__file.mtime > self.__mtime)

        @property
        def document(self):
            return self.__document

        def synchronize(self):
            """
            Synchronize document model with file contents.

            This may throw OSError
            """
            # update timestamp
            self.__mtime = self.__file.mtime

            # parse
            self.__document = self.__parser.parse(open(self.__file.path, "r").read(), self.__file, self.__issue_handler)

    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        if not '_ready' in dir(self):
            self._entries = {}
            self._ready = True

    def get_document(self, file):
        """
        Return the (hopefully) cached document model for a given file

        @param file: a File object
        """
        try:
            # update entry if necessary
            entry = self._entries[file.uri]
            if entry.modified:
                self._log.debug("File '%s' modified, synchronizing..." % file)
                entry.synchronize()
        except KeyError:
            self._log.debug("Cache fault for '%s'" % file)
            # create new entry
            entry = self.Entry(file)
            self._entries[file.uri] = entry

        return entry.document



# ex:ts=4:et:
