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
bibtex.validator
"""
from logging import getLogger

from ..issues import Issue
from .model import BibTeXModel


class BibTeXValidator:
    """
    This checks for
     - duplicate entry names
     - duplicate fields
     - missing required fields *
     - unused fields *

    *) relies on the BibTeX model definition
    """

    _log = getLogger("BibTeXValidator")

    def __init__(self):
        self._model = BibTeXModel()

    def validate(self, document, file, issue_handler):
        """
        @param document: a bibtex.parser.Document object
        @param issue_handler: an object implementing IIssueHandler
        """
        entry_keys = []
        for entry in document.entries:
            # check for duplicate keys
            if entry.key in entry_keys:
                issue_handler.issue(Issue("Duplicate key <b>%s</b>" % entry.key,
                                          entry.start, entry.end, file,
                                          Issue.SEVERITY_ERROR))
            else:
                entry_keys.append(entry.key)

            field_names = []
            for field in entry.fields:
                # check for duplicate fields
                if field.name in field_names:
                    issue_handler.issue(Issue("Duplicate field <b>%s</b>" % field.name,
                                        entry.start, entry.end, file, Issue.SEVERITY_ERROR))
                else:
                    field_names.append(field.name)

            try:
                # check for missing required fields
                required_field_names = set([f.name for f in self._model.find_type(entry.type).required_fields])
                missing_field_names = required_field_names.difference(set(field_names))

                if len(missing_field_names) > 0:
                    issue_handler.issue(Issue("Possibly missing field(s): <b>%s</b>" % ",".join(missing_field_names),
                                              entry.start, entry.end, file, Issue.SEVERITY_WARNING))

                # check for unused fields
                optional_field_names = set([f.name for f in self._model.find_type(entry.type).optional_fields])
                unused_field_names = set(field_names).difference(optional_field_names.union(required_field_names))

                if len(unused_field_names) > 0:
                    issue_handler.issue(Issue("Possibly unused field(s): <b>%s</b>" % ",".join(unused_field_names),
                                              entry.start, entry.end, file, Issue.SEVERITY_WARNING))
            except KeyError:
                #self._log.debug("Type not found: %s" % entry.type)
                pass

# ex:ts=4:et:
