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

import logging

from gi.repository import Gtk

LOG = logging.getLogger(__name__)

#FIXME: this should probably be just a Gtk.Orientable iface
# HORIZONTAL: means Bottom Panel
# VERTICAL: means Side Panel
class PanelView(Gtk.Box):
    """
    Base class for a View
    """

    def __init__(self, context):
        Gtk.Box.__init__(self)
        self._context = context

    # these should be overriden by subclasses

    # a label string used for this view
    def get_label(self):
        raise NotImplementedError

    # an icon for this view (Gtk.Image or a stock_id string)
    def get_icon(self):
        return None

# ex:ts=4:et:
