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
outline

Classes used for creating an outline view of LaTeX and BibTeX files
"""

import logging

from gi.repository import Gtk, GdkPixbuf

from .panelview import PanelView
from .preferences import Preferences
from .resources import Resources
from .gldefs import _

LOG = logging.getLogger(__name__)

class BaseOutlineView(PanelView):
    """
    Base class for the BibTeX and LaTeX outline views
    """

    def __init__(self, context, editor):
        PanelView.__init__(self, context)
        self._editor = editor

        self.set_orientation(Gtk.Orientation.VERTICAL)

        self._preferences = Preferences()

        grid = Gtk.Grid()
        grid.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(grid)

        # toolbar

        btn_follow = Gtk.ToggleToolButton.new_from_stock(Gtk.STOCK_CONNECT)
        btn_follow.set_tooltip_text(_("Follow Editor"))
        btn_follow.set_active(self._preferences.get("outline-connect-to-editor"))
        btn_follow.connect("toggled", self._on_follow_toggled)

        btn_expand = Gtk.ToolButton.new_from_stock(Gtk.STOCK_ZOOM_IN)
        btn_expand.set_tooltip_text(_("Expand All"))
        btn_expand.connect("clicked", self._on_expand_clicked)

        btn_collapse = Gtk.ToolButton.new_from_stock(Gtk.STOCK_ZOOM_OUT)
        btn_collapse.set_tooltip_text(_("Collapse All"))
        btn_collapse.connect("clicked", self._on_collapse_clicked)

        self._toolbar = Gtk.Toolbar()
        self._toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        self._toolbar.set_icon_size(Gtk.IconSize.MENU)
        self._toolbar.insert(btn_follow, -1)
        self._toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self._toolbar.insert(btn_expand, -1)
        self._toolbar.insert(btn_collapse, -1)
        self._toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self._toolbar.set_hexpand(True)

        grid.add(self._toolbar)

        # tree view

        column = Gtk.TreeViewColumn()

        pixbuf_renderer = Gtk.CellRendererPixbuf()
        column.pack_start(pixbuf_renderer, False)
        column.add_attribute(pixbuf_renderer, "pixbuf", 1)

        text_renderer = Gtk.CellRendererText()
        column.pack_start(text_renderer, True)
        column.add_attribute(text_renderer, "markup", 0)

        self._offset_map = OutlineOffsetMap()

        self._store = Gtk.TreeStore(str, GdkPixbuf.Pixbuf, object)    # label, icon, node object

        self._view = Gtk.TreeView(model=self._store)
        self._view.append_column(column)
        self._view.set_headers_visible(False)
        self._view.connect("row-activated", self._on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self._view)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        grid.add(scrolled)

        # this holds a list of the currently expanded paths
        self._expandedPaths = None

    def get_label(self):
        return _("Outline")

    def get_icon(self):
        return Gtk.Image.new_from_file(Resources().get_icon("outline.png"))

    def _on_follow_toggled(self, toggle_button):
        value = toggle_button.get_active()
        self._preferences.set("outline-connect-to-editor", value)

    def _on_expand_clicked(self, button):
        self._view.expand_all()

    def _on_collapse_clicked(self, button):
        self._view.collapse_all()

    def select_path_by_offset(self, offset):
        """
        Select the path corresponding to a given offset in the source

        Called by the Editor
        """
        LOG.debug("select path by offset %r" % offset)
        try:
            path = self._offset_map.lookup(offset)
            selection = self._view.get_selection()
            if selection:
                self._view.expand_to_path(path)
                selection.select_path(path)
        except KeyError:
            pass

    def _save_state(self):
        """
        Save the current expand state
        """
        self._expanded_paths = []
        self._view.map_expanded_rows(self._save_state_map_function,None)

    def _save_state_map_function(self, view, path, user_data=None):
        """
        Mapping function for saving the current expand state
        """
        self._expanded_paths.append(path.to_string())

    def _restore_state(self):
        """
        Restore the last expand state
        """
        self._view.collapse_all()

        if self._expanded_paths:
            for path in self._expanded_paths:
                self._view.expand_to_path(Gtk.TreePath.new_from_string(path))

    def _on_row_activated(self, view, path, column):
        it = self._store.get_iter(path)
        node = self._store.get(it, 2)[0]

        self._on_node_activated(node)

    #
    # methods to be overridden by the subclass
    #

    def _on_node_activated(self, node):
        """
        To be overridden
        """

    def set_outline(self, outline):
        """
        Load a new outline model

        To be overridden
        """


class Item(object):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __lt__(self, other):
        return self.key < other.key

    def __eq__(self, other):
        return self.key == other.key

    def __hash__(self):
        return hash(self.key)


class OffsetLookupTree(object):
    def __init__(self):
        self.items = []

    def insert(self, key, value):
        """
        Insert a value
        """
        self.items.append(Item(key, value))

    def prepare(self):
        """
        Prepare the structure for being searched
        """
        self.items.sort()

    def find(self, key):
        """
        Find a value by its key
        """
        return self._find(key, 0, len(self.items) - 1)

    def _find(self, key, lo, hi):
        if hi - lo == 0:
            raise KeyError

        i = (hi - lo)/2
        item = self.items[i]
        if item.key == key:
            return item.value
        elif item.key > key:
            return self._find(key, lo, i - 1)
        elif item.key < key:
            return self._find(key, i + 1, hi)


class OutlineOffsetMap(object):
    """
    This stores a mapping from the start offsets of outline elements
    to paths in the outline tree.

    We need this for the 'connect-outline-to-editor' feature.

    We may not use a simple dictionary for that because we need some
    kind of neighborhood lookup as we never get the exact offsets.
    """

    # TODO: find a faster structure for this - this is a tree with a special
    # find method

    def __init__(self):
        self._map = {}

    def clear(self):
        self._map = {}

    def put(self, offset, path):
        self._map[offset] = path

    def lookup(self, offset):
        """
        Returns the outline element containing a certain offset
        """

        # sort offsets
        offsets = list(self._map.keys())
        offsets.sort()

        # find nearest offset
        nearestOffset = None
        for o in offsets:
            if o > offset:
                break
            nearestOffset = o

        if not nearestOffset:
            raise KeyError

        return self._map[nearestOffset]

    def __str__(self):
        s = "<OutlineOffsetMap>"

        ofs = list(self._map.keys())
        ofs.sort()

        for o in ofs:
            s += "\n\t%s : %s" % (o, self._map[o])
        s += "\n</OutlineOffsetMap>"
        return s

# ex:ts=4:et:
