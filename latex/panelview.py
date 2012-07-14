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

from gi.repository import GObject, Gtk

class PanelView(Gtk.Bin, Gtk.Orientable):
    """
    Base class for a View
    """

    orientation = GObject.property(type=Gtk.Orientation, default=Gtk.Orientation.HORIZONTAL)

    def __init__(self, context):
        Gtk.Bin.__init__(self)
        self._context = context

    def _get_size(self, orientation):
        minimum, maximum = 0, 0
        child = self.get_child()

        if child is not None and child.get_visible():
            if orientation == Gtk.Orientation.HORIZONTAL:
                minimum, maximum = child.get_preferred_width()
            else:
                minimum, maximum = child.get_preferred_height()

        return minimum, maximum

    def do_get_preferred_width(self):
        return self._get_size(Gtk.Orientation.HORIZONTAL)

    def do_get_preferred_height(self):
        return self._get_size(Gtk.Orientation.VERTICAL)

    def do_size_allocate(self, allocation):
        Gtk.Bin.do_size_allocate(self, allocation)

        child = self.get_child()
        if child is not None and child.get_visible():
            child.size_allocate(allocation)

    # these should be overriden by subclasses

    # a label string used for this view
    def get_label(self):
        raise NotImplementedError

    # an icon for this view (Gtk.Image or a stock_id string)
    def get_icon(self):
        return None

# ex:ts=4:et:
