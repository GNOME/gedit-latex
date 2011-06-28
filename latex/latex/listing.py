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
latex.listing
"""

from xml.sax import ContentHandler, parse


class Language(object):
    def __init__(self, name):
        self.name = name
        self.dialects = []


class Dialect(object):
    def __init__(self, name, default):
        self.name = name
        self.default = default


class LanguagesParser(ContentHandler):
    """
    This parses the listing.xml file containing the available languages for listings
    """
    def __init__(self):
        self._languages = None
        self._language = None

    def startElement(self, name, attributes):
        if name == "language":
            l = Language(attributes["name"])
            self._languages.append(l)
            self._language = l
        elif name == "dialect":
            default = False
            try:
                if attributes["default"] == "true":
                    default = True
            except KeyError:
                pass

            self._language.dialects.append(Dialect(attributes["name"], default))
        elif name == "no-dialect":
            self._language.dialects.append(Dialect(None, True))

    def parse(self, languages, filename):
        """
        Parse XML

        "languages" must be a list
        """
        self._languages = languages
        parse(filename, self)


# ex:ts=4:et:
