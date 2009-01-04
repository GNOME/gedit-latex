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
latex.inversesearch

DBUS code for managing inverse search from DVI viewer


This is DEPRECATED as xdvi may connect to gedit directly. The following command line was
used to connect xdvi with gedit:

xdvi -unique -s 6 -bg white -editor "dbus-send --type=method_call --dest=org.gedit.LaTeXPlugin /org/gedit/LaTeXPlugin/InverseSearchService org.gedit.LaTeXPlugin.InverseSearchService.inverse_search string:%f int32:%l" "$shortname.dvi"
"""

from logging import getLogger
_log = getLogger("latex.inversesearch")


from ..base import File
from editor import LaTeXEditor


BUS_NAME = 'org.gedit.LaTeXPlugin'
OBJECT_PATH = '/org/gedit/LaTeXPlugin/InverseSearchService'

try:
	import dbus
	import dbus.service
	import dbus.glib	# attach D-Bus connections to main loop
	
	class InverseSearchService(dbus.service.Object):
		"""
		A D-Bus object listening for commands from xdvi. This is a delegate object
		for GeditWindowDecorator.
		
		@deprecated: 
		"""
		
		def __init__(self, context):
			"""
			Construct the service object
			
			@param context: a base.WindowContext instance
			"""
			bus_name = dbus.service.BusName(BUS_NAME, bus=dbus.SessionBus())
			dbus.service.Object.__init__(self, bus_name, OBJECT_PATH)
			
			self._context = context
			
			_log.debug("Created service object %s" % OBJECT_PATH)

		@dbus.service.method('org.gedit.LaTeXPlugin.InverseSearchService')
		def inverse_search(self, filename, line):
			"""
			A service call has been received
			
			@param filename: the filename
			@param line: a line number counting from 1 (!)
			"""
			_log.debug("Received inverse DVI search call: %s %s" % (filename, line))
			
			file = File(filename)
			
			try:
				self._context.activate_editor(file)
				editor = self._context.active_editor
				
				assert type(editor) is LaTeXEditor
				
				editor.select_lines(line - 1)
				
			except KeyError:
				_log.error("Could not activate tab for file %s" % filename)
			
except ImportError:
	# TODO: popup a message
	_log.error("Failed to import D-Bus bindings")
			
			