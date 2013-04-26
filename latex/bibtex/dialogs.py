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
latex.dialogs
"""

from gi.repository import Gtk

from ..util import GladeInterface
from ..resources import Resources
from .model import BibTeXModel


class InsertBibTeXEntryDialog(GladeInterface):

    _dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("insert_bibtex_entry.ui")

    def run(self):
        dialog = self._getDialog()

        result = None

        if dialog.run() == 1:

            s = "@%s{%s,\n" % (self._activeType.name, self._entryIdent.get_text())

            # fields
            f = []
            for entry, field in self._mapping.items():
                value = entry.get_text()
                if len(value):
                    if field == "title":
                        f.append("\t%s = {{%s}}" % (field, value))
                    else:
                        f.append("\t%s = {%s}" % (field, value))
            s += ",\n".join(f)

            # abstract
            #buf = self._view_abstract.get_buffer()
            #abs = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
            #if len(abs):
            #    s += ",\n\tabstract = {%s}" % abs

            s += "\n}"

            result = s

        dialog.hide()

        return result

    def _getDialog(self):
        if not self._dialog:
            self._dialog = self.find_widget("dialogInsertBibtexEntry")

            # get BibTeX model
            self._model = BibTeXModel()

            # setup types combobox

            self._activeType = None
            self._mapping = {}        # this maps Gtk.Entry objects to field names
            self._fieldCache = {}    # this is used to restore field values after the type has changed

            self._storeTypes = Gtk.ListStore(str)
            for t in self._model.types:
                self._storeTypes.append([t.name])

            comboTypes = self.find_widget("comboTypes")
            comboTypes.set_model(self._storeTypes)
            cell = Gtk.CellRendererText()
            comboTypes.pack_start(cell, True)
            comboTypes.add_attribute(cell, "text", 0)

            self._boxRequired = self.find_widget("boxRequired")
            self._boxOptional = self.find_widget("boxOptional")

            self._entryIdent = self.find_widget("entryIdent")

            self._buttonOk = self.find_widget("buttonOk")

            self.connect_signals({"on_comboTypes_changed": self._comboTypesChanged,
                                "on_entryIdent_changed": self._identChanged})

            comboTypes.set_active(0)

        return self._dialog

    def _identChanged(self, entry):
        enable = bool(len(entry.get_text()))
        self._buttonOk.set_sensitive(enable)

    def _comboTypesChanged(self, combo):
        i = combo.get_active()
        self._activeType = self._model.types[i]

        # cache values

        for entry, fieldName in self._mapping.items():
            text = entry.get_text()
            if len(text):
                self._fieldCache[fieldName] = entry.get_text()

        # reset mapping

        self._mapping = {}

        # required fields

        tbl_required = Gtk.Table()
        tbl_required.set_border_width(5)
        tbl_required.set_row_spacings(5)
        tbl_required.set_col_spacings(5)
        i = 0

        for field in self._activeType.required_fields:
            label = Gtk.Label(label=field.label + ":")
            label.set_alignment(0, .5)

            entry = Gtk.Entry()

            tbl_required.attach(label, 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            tbl_required.attach(entry, 1, 2, i, i + 1)

            self._mapping[entry] = field.name

            # try to restore field value
            try:
                entry.set_text(self._fieldCache[field.name])
            except KeyError:
                pass

            i += 1

        for child in self._boxRequired.get_children():
            child.destroy()

        tbl_required.show_all()
        self._boxRequired.pack_start(tbl_required, False, False, 0)

        # optional fields

        tbl_optional = Gtk.Table()
        tbl_optional.set_border_width(5)
        tbl_optional.set_row_spacings(5)
        tbl_optional.set_col_spacings(5)
        i = 0

        for field in self._activeType.optional_fields:
            label = Gtk.Label(label=field.label + ":")
            label.set_alignment(0, .5)

            entry = Gtk.Entry()

            tbl_optional.attach(label, 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            tbl_optional.attach(entry, 1, 2, i, i + 1)

            self._mapping[entry] = field.name

            # try to restore field value
            try:
                entry.set_text(self._fieldCache[field.name])
            except KeyError:
                pass

            i += 1

        for child in self._boxOptional.get_children():
            child.destroy()

        tbl_optional.show_all()
        self._boxOptional.pack_start(tbl_optional, False, False, 0)

# ex:ts=4:et:
