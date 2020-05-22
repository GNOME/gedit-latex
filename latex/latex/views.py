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
latex.views

LaTeX-specific views
"""

import logging
import xml.etree.ElementTree as ElementTree

from gi.repository import Gtk, GdkPixbuf
from os.path import basename

from ..preferences import Preferences
from ..panelview import PanelView
from ..file import File
from ..resources import Resources
from ..snippetmanager import SnippetManager
from ..outline import OutlineOffsetMap, BaseOutlineView
from .outline import OutlineNode
from ..gldefs import _

LOG = logging.getLogger(__name__)

class SymbolCollection(object):
    """
    A collection of symbols read from an XML file
    """

    class Group(object):
        def __init__(self, label):
            """
            @param label: a label for this Group
            """
            self.label = label
            self.symbols = []


    class Symbol(object):
        def __init__(self, snippet, icon):
            """
            @param snippet: a snippet to insert
            @param icon: an icon filename
            """
            self.snippet = snippet
            self.icon = icon


    def __init__(self):
        filename = Resources().get_data_file("symbols.xml")

        self.groups = []

        symbols_el = ElementTree.parse(filename).getroot()
        for group_el in symbols_el.findall("group"):
            group = self.Group(group_el.get("label"))
            for symbol_el in group_el.findall("symbol"):
                symbol = self.Symbol(symbol_el.text.strip(), Resources().get_icon("%s" % symbol_el.get("icon")))
                group.symbols.append(symbol)
            self.groups.append(group)


class LaTeXSymbolMapView(PanelView):
    """
    """

    def __init__(self, context, editor):
        PanelView.__init__(self, context)
        self._preferences = Preferences()

        self.set_orientation(Gtk.Orientation.VERTICAL)

        self._grid = Gtk.Grid()
        self._grid.set_orientation(Gtk.Orientation.VERTICAL)

        self._load_collection(SymbolCollection())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_shadow_type(Gtk.ShadowType.NONE)
        scrolled.add_with_viewport(self._grid)
        scrolled.set_vexpand(True)

        self.add(scrolled)
        self.show_all()

    def get_label(self):
        return _("Symbols")

    def get_icon(self):
        return Gtk.Image.new_from_stock(Gtk.STOCK_INDEX,Gtk.IconSize.MENU)

    def _load_collection(self, collection):
        self._expanded_groups = set(self._preferences.get("expanded-symbol-groups").split(","))

        for group in collection.groups:
            self._add_group(group)

    def _add_group(self, group):
        model = Gtk.ListStore(GdkPixbuf.Pixbuf, str)        # icon, snippet

        for symbol in group.symbols:
            try:
                model.append([GdkPixbuf.Pixbuf.new_from_file(symbol.icon), symbol.snippet])
            except:
                LOG.error("Could not add symbol group %s to model" % symbol, exc_info=True)

        view = Gtk.IconView(model=model)
        view.set_pixbuf_column(0)
        view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        view.connect("item-activated", self._on_symbol_activated)
        view.connect("focus-out-event", self._on_focus_out_event)
        view.set_spacing(0)
        view.set_column_spacing(0)
        view.set_row_spacing(0)
        view.set_columns(4)
        view.set_text_column(-1)
        view.set_tooltip_column(1)
        view.set_hexpand(True)
        view.set_halign(Gtk.Align.FILL)

        expander = Gtk.Expander(label=group.label)
        expander.set_hexpand(True)
        expander.set_halign(Gtk.Align.FILL)
        expander.add(view)
        if group.label in self._expanded_groups:
            expander.set_expanded(True)
        expander.connect("notify::expanded", self._on_group_expanded, group.label)

        self._grid.add(expander)

    def _on_group_expanded(self, expander, paramSpec, group_label):
        """
        The Expander for a symbol group has been expanded
        """
        if expander.get_expanded():
            self._expanded_groups.add(group_label)
        else:
            self._expanded_groups.remove(group_label)

        self._preferences.set("expanded-symbol-groups", ",".join(self._expanded_groups))

    def _on_symbol_activated(self, icon_view, path):
        """
        A symbol has been activated

        @param icon_view: the Gtk.IconView
        @param path: the Gtk.TreePath to the item
        """
        snippet = icon_view.get_model()[path][1]
        SnippetManager().insert_at_cursor(self._context.active_editor, snippet)

    def _on_focus_out_event(self, icon_view, event):
        icon_view.unselect_all()


class LaTeXOutlineView(BaseOutlineView):
    """
    A View showing an outline of the edited LaTeX document
    """

    def __init__(self, context, editor):
        BaseOutlineView.__init__(self, context, editor)
        self._handlers = {}

        self._offset_map = OutlineOffsetMap()

        # additional toolbar buttons
        btn_graphics = Gtk.ToggleToolButton()
        btn_graphics.set_icon_widget(Gtk.Image.new_from_file(Resources().get_icon("tree_includegraphics.png")))
        btn_graphics.set_tooltip_text(_("Show graphics"))
        self._toolbar.insert(btn_graphics, -1)

        btn_tables = Gtk.ToggleToolButton()
        btn_tables.set_icon_widget(Gtk.Image.new_from_file(Resources().get_icon("tree_table.png")))
        btn_tables.set_tooltip_text(_("Show tables"))
        self._toolbar.insert(btn_tables, -1)

        btn_graphics.set_active(Preferences().get("outline-show-graphics"))
        btn_tables.set_active(Preferences().get("outline-show-tables"))

        self._handlers[btn_graphics] = btn_graphics.connect("toggled", self._on_graphics_toggled)
        self._handlers[btn_tables] = btn_tables.connect("toggled", self._on_tables_toggled)

        self.show_all()

    def set_outline(self, outline):
        """
        Load a new outline model
        """
        LOG.debug("LatexOutline: set outline")

        self._save_state()

        self._offset_map = OutlineOffsetMap()
        OutlineConverter().convert(self._store, outline, self._offset_map, self._editor.edited_file)

        self._restore_state()

    def _on_node_activated(self, node):
        """
        An outline node has been double-clicked on

        @param node: an instance of latex.outline.OutlineNode
        """
        if node.type == OutlineNode.GRAPHICS:
            # use 'gio open' to open the graphics file

            target = node.value

            if not target:
                return

            # the way we use a mixture of File objects and filenames is not optimal...
            if File.is_absolute(target):
                filename = target
            else:
                filename = File.create_from_relative_path(target, node.file.dirname).path

            # an image may be specified without the extension
            potential_extensions = ["", ".eps", ".pdf", ".jpg", ".jpeg", ".gif", ".png"]

            found = False
            for ext in potential_extensions:
                f = File(filename + ext)
                if f.exists:
                    found = True
                    break

            if not found:
                LOG.error("LatexOutline: File not found: %s" % filename)
                return

            Gtk.show_uri(None, f.uri, Gtk.get_current_event_time())

        else:
            # select/open/activate the referenced file
            if node.file == self._editor.edited_file:
                self._editor.select(node.start, node.end)
            else:
                self._context.activate_editor(node.file)

    def _on_tables_toggled(self, toggle_button):
        value = toggle_button.get_active()
#        Settings().set("LatexOutlineTables", value)
#        self.trigger("tablesToggled", value)
        Preferences().set("outline-show-tables", value)

    def _on_graphics_toggled(self, toggle_button):
        value = toggle_button.get_active()
#        Settings().set("LatexOutlineGraphics", value)
#        self.trigger("graphicsToggled", value)
        Preferences().set("outline-show-graphics", value)


class OutlineConverter(object):
    """
    This creates a Gtk.TreeStore object from a LaTeX outline model
    """

    def __init__(self):
        self._preferences = Preferences()
        self._ICON_LABEL = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("label.png"))
        self._ICON_TABLE = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_table.png"))
        self._ICON_GRAPHICS = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_includegraphics.png"))

        self._LEVEL_ICONS = { 1 : GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_part.png")),
                    2 : GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_chapter.png")),
                    3 : GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_section.png")),
                    4 : GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_subsection.png")),
                    5 : GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_subsubsection.png")),
                    6 : GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_paragraph.png")),
                    7 : GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("tree_paragraph.png")) }

    def convert(self, tree_store, outline, offset_map, file):
        """
        Convert an Outline object to a Gtk.TreeStore and update an OutlineOffsetMap

        @param tree_store: Gtk.TreeStore
        @param outline: latex.outline.Outline
        @param offset_map: outline.OutlineOffsetMap
        @param file: the edited File (to identify foreign outline nodes)
        """
        self._offsetMap = offset_map
        self._treeStore = tree_store
        self._treeStore.clear()
        self._file = file

        self._append(None, outline.rootNode)

    def _append(self, parent, node):
        """
        Recursively append an outline node to the TreeStore

        @param parent: a Gtk.TreeIter or None
        @param node: an OutlineNode
        """
        value = node.value

        color = self._preferences.get("light-foreground-color")

        if node.file and node.file != self._file:
            value = "%s <span color='%s'>%s</span>" % (value, color, node.file.shortbasename)

        if node.type == OutlineNode.STRUCTURE:
            icon = self._LEVEL_ICONS[node.level]
            parent = self._treeStore.append(parent, [value, icon, node])
        elif node.type == OutlineNode.LABEL:
            parent = self._treeStore.append(parent, [value, self._ICON_LABEL, node])
        elif node.type == OutlineNode.TABLE:
            parent = self._treeStore.append(parent, [value, self._ICON_TABLE, node])
        elif node.type == OutlineNode.GRAPHICS:
            label = basename(node.value)

            if node.file and node.file != self._file:
                label = "%s <span color='%s'>%s</span>" % (label, color, node.file.shortbasename)

            parent = self._treeStore.append(parent, [label, self._ICON_GRAPHICS, node])

        # store path in offset map for all non-foreign nodes
        # check for parent to ignore root node
        if parent and not node.foreign:
            path = self._treeStore.get_path(parent)
            self._offsetMap.put(node.start, path)

        for child in node:
            self._append(parent, child)

# ex:ts=4:et:
