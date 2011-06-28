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
bibtex.completion
"""

from logging import getLogger
from gi.repository import Gdk, GdkPixbuf

from ..preferences import Preferences
from ..base.resources import find_resource
from ..base import ICompletionHandler, Proposal, Template
from ..issues import MockIssueHandler
from model import BibTeXModel
from parser import BibTeXParser


class BibTeXEntryTypeProposal(Proposal):
    """
    """
    icon = GdkPixbuf.Pixbuf.new_from_file(find_resource("icons/document.png"))

    _color = Preferences().get("light-foreground-color")

    def __init__(self, overlap, type):
        """
        @param overlap: the number of overlapping characters
        @param type: an EntryType
        """
        self._overlap = overlap
        self._type = type
        self._details = None
        self._source = None

    def _generate(self):
        """
        Generate Template and details string
        """
        template = "@%s{${Identifier}" % self._type.name
        self._details = "@%s{<span color='%s'>Identifier</span>" % (self._type.name, self._color)
        for field in self._type.required_fields:
            template += ",\n\t%s = {${%s}}" % (field.name, field.label)
            self._details += ",\n\t%s = {<span color='%s'>%s</span>}" % (field.name, self._color, field.label)
        template += "\n}"
        self._details += "\n}"
        self._source = Template(template)

    @property
    def source(self):
        if not self._source:
            self._generate()
        return self._source

    @property
    def label(self):
        return self._type.name

    @property
    def details(self):
        if not self._details:
            self._generate()
        return self._details

    @property
    def overlap(self):
        return self._overlap


class BibTeXCompletionHandler(ICompletionHandler):
    """
    This implements the BibTeX-specific code completion
    """
    _log = getLogger("BibTeXCompletionHandler")

    trigger_keys = ["@"]
    prefix_delimiters = ["@"]

    def __init__(self):
        self._model = BibTeXModel()
        self._parser = BibTeXParser()
        self._issue_handler = MockIssueHandler()

    def complete(self, prefix):
        self._log.debug("complete: '%s'" % prefix)

        proposals = []

        if len(prefix) == 1:
            # propose all entry types
            types = self._model.types
            proposals = [BibTeXEntryTypeProposal(1, type) for type in types]
        else:
            if prefix[1:].isalpha():
                type_name_prefix = prefix[1:].lower()
                overlap = len(type_name_prefix) + 1
                # prefix is @[a-zA-Z]+
                types = [type for type in self._model.types if type.name.lower().startswith(type_name_prefix)]
                proposals = [BibTeXEntryTypeProposal(overlap, type) for type in types]
            else:
                # parse prefix
#                document = self._parser.parse(prefix, None, self._issue_handler)
#
#                print document
                pass

        return proposals


