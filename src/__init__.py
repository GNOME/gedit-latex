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
This is searched by gedit for a class extending gedit.Plugin
"""

import gedit
import gtk
import logging
import platform

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s	%(name)s - %(message)s")

from base.decorators import GeditWindowDecorator
from util import open_error
from preferences.dialog import PreferencesDialog


class GeditLaTeXPlugin(gedit.Plugin):
	"""
	This controls the plugin life-cycle
	"""
	
	# we need Python 2.5 because it contains the ElementTree XML library
	_REQUIRED_PYTHON_VERSION = (2, 5, 0)
	
	# be sure that we're running on a gedit with the new binding API
	# see http://ftp.acc.umu.se/pub/GNOME/sources/gedit/2.15/gedit-2.15.2.changes
	#
	# TODO: we should support earlier versions because e.g. Debian Etch still offers 2.14
	_REQUIRED_GEDIT_VERSION = (2, 15, 2)
	
	# we need gtk.IconView.set_tooltip_column
	_REQUIRED_PYGTK_VERSION = (2, 12, 0)
	
	# we need to pack a gtk.Expander into a gtk.VBox which fails before GTK+ 2.10.14
	_REQUIRED_GTK_VERSION = (2, 10, 14)
	
	_log = logging.getLogger("GeditLaTeXPlugin")
	
	_platform_okay = True
	
	def __init__(self):
		gedit.Plugin.__init__(self)
		self._window_decorators = {}

		# check requirements
		requirements = [
				(tuple(platform.python_version_tuple()), self._REQUIRED_PYTHON_VERSION, "Python"),
				(gedit.version, self._REQUIRED_GEDIT_VERSION, "gedit"),
				(gtk.pygtk_version, self._REQUIRED_PYGTK_VERSION, "PyGTK"),
				(gtk.ver, self._REQUIRED_GTK_VERSION, "GTK+")]
		
		for version, required_version, label in requirements:
			if version < required_version:
				self._platform_okay = False
				version_s = ".".join(map(str, required_version))
				open_error("LaTeX Plugin requires %s %s or newer" % (label, version_s))
		
	def activate(self, window):
		"""
		Called when the plugin is loaded with gedit or activated in 
		configuration
		
		@param window: GeditWindow
		"""
		self._log.debug("activate")
		
		if self._platform_okay:
			self._window_decorators[window] = GeditWindowDecorator(window)
	
	def deactivate(self, window):
		"""
		Called when the plugin is deactivated in configuration
		
		@param window: GeditWindow
		"""
		self._log.debug("deactivate")
		
		if self._platform_okay:
			self._window_decorators[window].destroy()
			del self._window_decorators[window]
	
	def create_configure_dialog(self):
		if self._platform_okay:
			return PreferencesDialog().dialog
	
	