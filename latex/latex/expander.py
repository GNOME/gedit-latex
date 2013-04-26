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
latex.expander
"""

from logging import getLogger

from ..file import File
from .cache import LaTeXDocumentCache
from .parser import Node


class LaTeXReferenceExpander(object):
    """
    This expands '\include' and '\input' commands by parsing the referenced child
    documents. The resulting trees may be attached to the parent tree.
    """

    # TODO: embed this into parser so that we don't need to walk the document again

    _log = getLogger("ReferenceExpander")

    def __init__(self):
        self._document_cache = LaTeXDocumentCache()

    def expand(self, documentNode, master_file, issue_handler, charset):
        """
        @param documentNode: the master model
        @param master_file: the File object of the master
        @param issue_handler: an IIssueHandler object
        @param charset: a string naming the character set used by Gedit
        """
        self._master_file = master_file
        self._issue_handler = issue_handler
        self._charset = charset
        self._expand(documentNode)

    def _expand(self, parentNode):
        """
        Recursively walk all nodes in the document model and check for \input or \include
        commands. Extract the filename from the command and parse the referenced file.
        Attach its model as a DOCUMENT node to the master model and hold its filename as
        the value of that DOCUMENT node, so that the Validator may differ between issue
        sources.
        """
        for node in parentNode:
            if node.type == Node.COMMAND and (node.value == "input" or node.value == "include"):
                try:
                    # build child filename (absolute/relative, with .tex/without .tex)
                    target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText

                    file = None
                    if File.is_absolute(target):
                        # absolute path
                        # look for 'x' and then for 'x.tex'
                        file = File("%s.tex" % target)
                        if not file.exists:
                            file = File(target)
                    else:
                        # path relative to the master file's directory
                        # TODO: include TeX search path!
                        # look for 'x' and then for 'x.tex'
                        file = File.create_from_relative_path("%s.tex" % target, self._master_file.dirname)
                        if not file.exists:
                            file = File.create_from_relative_path(target, self._master_file.dirname)

                    self._log.debug("Expanding %s" % file)

                    # lookup/parse child document model
                    try:
                        fragment = self._document_cache.get_document(file, self._charset, self._issue_handler)

                        node.append(fragment)
                    except IOError:
                        self._log.error("Referenced file not found: %s" % file.uri)
                except IndexError:
                    self._log.error("Malformed reference command at %s" % node.start)

            self._expand(node)

# ex:ts=4:et:
