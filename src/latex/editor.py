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

from logging import getLogger

from ..base.interface import Editor
from completion import LaTeXCompletionHandler
from ..snippets.completion import SnippetCompletionHandler
from ..issues import Issue


class LaTeXEditor(Editor):
	_log = getLogger("LaTeXEditor")
	
	@property
	def completion_handlers(self):
		"""
		Return the CompletionHandlers to load when this Editor is used
		"""
		return [ LaTeXCompletionHandler(), SnippetCompletionHandler() ]
	
	def init(self, file, context):
		self._log.debug("init(%s)" % file)
		
		self._file = file
		
		self.register_marker_type("latex-spell", "#ffeccf")
		
		self._consistency_view = context.views["LaTeXConsistencyView"]
		#self._symbol_map_view = context.views["LaTeXSymbolMapView"]
	
	def save(self):
		"""
		The file has been saved
		
		Update models and pass issues
		"""
		self._consistency_view.clear()
		self._consistency_view.append_issue(Issue("Error", 0, 1, self._file, Issue.SEVERITY_ERROR))
	
	def spell_check(self):
		self._log.debug("spell_check")
		
		self.remove_markers("latex-spell")
		
		id = self.create_marker("latex-spell", 15, 30)
	
	def activate_marker(self, marker, event):
		"""
		A marker has been activated
		"""
		self._log.debug("activate_marker(%s, %s)" % (marker, event))
	
	def destroy(self):
		pass
	
	