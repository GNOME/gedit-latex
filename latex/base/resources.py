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
base.resources
"""

import logging
import os
import errno

_log = logging.getLogger("resources")

class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(
                     cls, *args, **kwargs)
            cls._instance.__init_once__()

        return cls._instance

class Resources(Singleton):
    def __init_once__(self):
        pass

    def set_dirs(self, userdir, systemdir):
        self.userdir = userdir
        self.systemdir = systemdir

        # Make sure dir exists
        try:
            os.makedirs(userdir)
        except OSError, e:
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
