# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2008 Michael Zeising
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
import logging

logging.basicConfig(level=logging.DEBUG)

from base.decorators import GeditWindowDecorator


class GeditLaTeXPlugin(gedit.Plugin):
	"""
	This controls the plugin life-cycle
	"""
	
	_log = logging.getLogger("GeditLaTeXPlugin")
	
	def __init__(self):
		gedit.Plugin.__init__(self)
		self._window_decorators = {}
		
		# be sure that we're running on a gedit with the new binding API
		# see http://ftp.acc.umu.se/pub/GNOME/sources/gedit/2.15/gedit-2.15.2.changes
		#
		# TODO: we should support earlier versions because e.g. Debian Etch still offers 2.14
		
		if gedit.version < (2, 15, 2):
			from util import open_error
			open_error("LaTeX Plugin requires gedit 2.15.2 or newer")
		
	def activate(self, window):
		"""
		Called when the plugin is loaded with gedit or activated in 
		configuration
		
		@param window: GeditWindow
		"""
		self._window_decorators[window] = GeditWindowDecorator(window)
	
	def deactivate(self, window):
		"""
		Called when the plugin is deactivated in configuration
		
		@param window: GeditWindow
		"""
		self._window_decorators[window].destroy()
		del self._window_decorators[window]
	
	def create_configure_dialog(self):
		# TODO: 
		return None
	
	