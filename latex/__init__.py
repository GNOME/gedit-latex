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

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)-8s:%(name)-30s: %(message)s (l.%(lineno)d)")

from gi.repository import Gio

if "org.gnome.gedit.plugins.latex" not in Gio.Settings.list_schemas():
    logging.critical("Could not find GSettings schema: org.gnome.gedit.plugins.latex")
    raise Exception("Plugin schema not installed")

from appactivatable import LaTeXAppActivatable
from base.windowactivatable import LaTeXWindowActivatable



# ex:ts=4:et:
