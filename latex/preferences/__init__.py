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
preferences
"""

from gi.repository import GObject, Gio, GLib

import os.path
import logging

from ..base.resources import find_resource, MODE_READWRITE
from ..util import singleton

@singleton
class Preferences(GObject.GObject):

    __gsignals__ = {
        "preferences-changed": (
            GObject.SignalFlags.RUN_LAST, None, [str, str]),
    }

    """
    A simple map storing preferences as key-value-pairs
    """

    _log = logging.getLogger("Preferences")

    TEMPLATE_DIR = os.path.join(GLib.get_user_data_dir(), "gedit", "latex", "templates")

    def __init__(self):
        GObject.GObject.__init__(self)
        self._settings = Gio.Settings("org.gnome.gedit.plugins.latex")
        self._log.debug("Constructed")

    def get(self, key, default=None):
        if default:
            return default
        return self._settings[key]

    def get_bool(self, key):
        return self._settings[key]

    def set(self, key, value):
        self._settings[key] = value
        self.emit("preferences-changed", str(key), str(value))

    def save(self):
        pass

# ex:ts=8:et:
