# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2010 Michael Zeising
#               2011 Ignacio Casal Quinteiro
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
resources
"""

from gi.repository import GLib

import logging
import platform
import os.path
import errno
from .singleton import Singleton

_log = logging.getLogger("resources")

class Resources(Singleton):
    def __init_once__(self):

        #check if running from srcdir and if so, prefer that for all data files
        me = os.path.realpath(os.path.dirname(__file__))
        if os.path.exists(os.path.join(me, "..", "meson.build")):
            self.from_source = True
            self.systemdir = os.path.abspath(os.path.join(me, "..", "data"))
        else:
            self.from_source = False
            # In this case, we need to wait for app to be instantiated
            # before setting "systemdir"

    def set_paths(self, lapp):
        #check if running from srcdir and if so, prefer that for all data files
        me = os.path.realpath(os.path.dirname(__file__))
        if not self.from_source:
            self.systemdir = lapp.plugin_info.get_data_dir()

        if platform.platform() == 'Windows':
            self.userdir = os.path.expanduser('~/gedit/latex')
        else:
            self.userdir = os.path.join(GLib.get_user_config_dir(), 'gedit/latex')

        # Make sure dir exists
        try:
            os.makedirs(self.userdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def get_user_dir(self):
        return self.userdir

    def get_system_dir(self):
        return self.systemdir

    def get_user_file(self, user_file):
        return os.path.join(self.userdir, user_file)

    def get_ui_file(self, ui_name):
        return os.path.join(self.systemdir, "ui", ui_name)

    def get_icon(self, icon_name):
        return os.path.join(self.systemdir, "icons", icon_name)

    def get_data_file(self, data_name):
        return os.path.join(self.systemdir, data_name)

# ex:ts=4:et:
