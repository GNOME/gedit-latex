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
latex.views

LaTeX-specific views
"""

import gtk
from gtk.gdk import Pixbuf, pixbuf_new_from_file
from logging import getLogger

from ..base import View
from ..issues import Issue


class LaTeXIssueView(View):
	"""
	Checking consistency of a LaTeX document means parsing and validating it.
	
	This view is editor-specific
	"""
	
	_log = getLogger("LaTeXIssueView")
	
	position = View.POSITION_BOTTOM
	label = "LaTeX Issues"
	icon = gtk.STOCK_CONVERT
	scope = View.SCOPE_EDITOR
	
	def init(self, context):
		self._log.debug("init")
		
		self._context = context
		
		self._icons = { Issue.SEVERITY_WARNING : None, 
						Issue.SEVERITY_ERROR : None, 
			   			Issue.SEVERITY_INFO : None,
			   			Issue.SEVERITY_TASK : None }
		
		self._store = gtk.ListStore(Pixbuf, str, str, object)
		
		self._view = gtk.TreeView(self._store)
		#self._view.set_headers_visible(False)
		
		column = gtk.TreeViewColumn()
		column.set_title("Message")
		
		pixbuf_renderer = gtk.CellRendererPixbuf()
		column.pack_start(pixbuf_renderer, False)
		column.add_attribute(pixbuf_renderer, "pixbuf", 0)
		
		text_renderer = gtk.CellRendererText()
		column.pack_start(text_renderer, True)
		column.add_attribute(text_renderer, "markup", 1)
		
		self._view.append_column(column)
		#self._view.insert_column_with_attributes(-1, "Message", column)
		
		#self._view.insert_column_with_attributes(-1, "", gtk.CellRendererPixbuf(), pixbuf=0)
		#self._view.insert_column_with_attributes(-1, "Description", gtk.CellRendererText(), markup=1)
		self._view.insert_column_with_attributes(-1, "File", gtk.CellRendererText(), text=2)
		self._view.connect("row-activated", self._on_row_activated)
		
		self._scr = gtk.ScrolledWindow()
		
		self._scr.add(self._view)
		self._scr.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self._scr.set_shadow_type(gtk.SHADOW_IN)
		
		self.pack_start(self._scr, True)
	
	def _on_row_activated(self, view, path, column):
		it = self._store.get_iter(path)
		issue = self._store.get(self._store.get_iter(path), 3)[0]
		
		self._context.activate_editor(issue.file)
	
	def clear(self):
		self.assure_init()
		
		self._log.debug("clear")
		
		self._store.clear()
	
	def append_issue(self, issue):
		self.assure_init()
		
		self._log.debug("append_issue: " + str(issue))
		
		self._store.append([None, issue.message, issue.file.basename, issue])
		
		
class LaTeXSymbolMapView(View):
	"""
	"""
	_log = getLogger("LaTeXSymbolMapView")
	
	position = View.POSITION_SIDE
	label = "Symbols"
	icon = gtk.STOCK_CONVERT
	scope = View.SCOPE_WINDOW
	
	def init(self, context):
		self._log.debug("init")
	
	
class LaTeXOutlineView(View):
	"""
	"""
	_log = getLogger("LaTeXOutlineView")
	
	position = View.POSITION_SIDE
	label = "Outline"
	icon = gtk.STOCK_CONVERT
	scope = View.SCOPE_EDITOR
	
	def init(self, context):
		self._log.debug("init")
	
	
		
		
		