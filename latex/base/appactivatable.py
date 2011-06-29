#    Gedit latex plugin
#    Copyright (C) 2011 Ignacio Casal Quinteiro
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import os

import glib

from gi.repository import Gedit, GObject
from resources import Resources
import platform

class LaTeXAppActivatable(GObject.Object, Gedit.AppActivatable):
    __gtype_name__ = "GeditLaTeXAppActivatable"

    app = GObject.property(type=Gedit.App)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        if platform.platform() == 'Windows':
            latexdir = os.path.expanduser('~/gedit/latex')
        else:
            latexdir = os.path.join(glib.get_user_config_dir(), 'gedit/latex')

        Resources().set_dirs(latexdir, self.plugin_info.get_data_dir())

# vi:ex:ts=4:et
