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
latex.actions
"""

from ..action import Action
from ..gldefs import _
from .dialogs import InsertBibTeXEntryDialog


class BibTeXMenuAction(Action):
    extensions = [".bib"]
    label = _("BibTeX")
    stock_id = None
    accelerator = None
    tooltip = None

    def activate(self, context):
        pass


class BibTeXNewEntryAction(Action):
    extensions = [".bib"]
    label = _("New BibTeX Entry…")
    stock_id = None
    accelerator = None
    tooltip = _("Create a new BibTeX entry")

    _dialog = None

    def activate(self, context):
        if not self._dialog:
            self._dialog = InsertBibTeXEntryDialog()

        source = self._dialog.run()
        if not source is None:
            context.active_editor.append(source)

# ex:ts=4:et:
