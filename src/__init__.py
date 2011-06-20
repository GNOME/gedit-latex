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

from gi.repository import Gedit, GObject, Gtk
import logging
#import platform

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s	%(name)s - %(message)s")

from base.decorators import GeditWindowDecorator
from util import open_error
from preferences.dialog import PreferencesDialog


class GeditLaTeXPlugin(GObject.Object, Gedit.WindowActivatable):
	"""
	This controls the plugin life-cycle
	"""
	__gtype_name__ =  "GeditLatexWindowActivatable"

        window = GObject.property(type=Gedit.Window)
	
	
	_log = logging.getLogger("GeditLaTeXPlugin")
	
	_platform_okay = True 
	
	def __init__(self):
		GObject.Object.__init__(self)
		self._window_decorators = {}
	
	def do_activate(self):
		"""
		Called when the plugin is loaded with gedit or activated in 
		configuration
		
		@param window: GeditWindow
		"""
		self._log.debug("activate")
		
		if self._platform_okay:
			self._window_decorators[self.window] = GeditWindowDecorator(self.window)
	
	def do_deactivate(self):
		"""
		Called when the plugin is deactivated in configuration
		
		@param window: GeditWindow
		"""
		self._log.debug("deactivate")
		
		if self._platform_okay:
			self._window_decorators[self.window].destroy()
			del self._window_decorators[self.window]
	
	def create_configure_dialog(self):
		if self._platform_okay:
			return PreferencesDialog().dialog
	
		pass	
