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
	A View showing an outline of the edited LaTeX document
	"""
	
	_log = getLogger("LaTeXOutlineView")
	
	position = View.POSITION_SIDE
	label = "Outline"
	icon = gtk.STOCK_CONVERT
	scope = View.SCOPE_EDITOR
	
	def init(self, context):
		self._log.debug("init")
		
		self._context = context
		
		column = gtk.TreeViewColumn()
		
		pixbuf_renderer = gtk.CellRendererPixbuf()
		column.pack_start(pixbuf_renderer, False)
		column.add_attribute(pixbuf_renderer, "pixbuf", 1)
		
		text_renderer = gtk.CellRendererText()
		column.pack_start(text_renderer, True)
		column.add_attribute(text_renderer, "markup", 0)
		
		self._view = gtk.TreeView()
		self._view.append_column(column)
		self._view.set_headers_visible(False)
		self._cursor_changed_id = self._view.connect("cursor-changed", self._on_cursor_changed)
		#self._view.connect("row-activated", self._on_row_activated)
		
		scrolled = gtk.ScrolledWindow()
		scrolled.add(self._view)
		scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		
		self.pack_start(scrolled, True)
		
		# this holds a list of the currently expanded paths
		self._expandedPaths = None
		
	def set_model(self, model):
		self.assure_init()
		
		self._view.set_model(model)
		
	def save_state(self):
		"""
		Save the current expand state
		"""
		self.assure_init()
		
		self._expanded_paths = []
		self._view.map_expanded_rows(self._save_state_map_function)
	
	def _save_state_map_function(self, view, path):
		"""
		Mapping function for saving the current expand state
		"""
		self._expanded_paths.append(path)
	
	def restore_state(self):
		"""
		Restore the last expand state
		"""
		self.assure_init()
		
		self._view.collapse_all()
		
		if self._expanded_paths:
			for path in self._expanded_paths:
				self._view.expand_to_path(path)
		else:
			self._view.expand_to_path((0,))
			
	def _on_cursor_changed(self, view):
		store, it = view.get_selection().get_selected()
		if not it: 
			return
			
		outline_node = store.get_value(it, 2)
		
		if not outline_node.foreign:
			self._context.active_editor.select(outline_node.start, outline_node.end)
		
		
#class OutlineView(AbstractOutlineView):
#	"""
#	Special outline view for LaTeX
#	"""
#	
#	#_log = getLogger("latex.outline.OutlineView")
#	
#	def __init__(self, treeStore):
#		AbstractOutlineView.__init__(self, treeStore)
#		
#		icoGraphics = gtk.image_new_from_file(getSystemResource("/pixmaps/tree_includegraphics.png"))
#		btnGraphics = gtk.ToggleToolButton()
#		btnGraphics.set_icon_widget(icoGraphics)
#		self._toolbar.insert(btnGraphics, -1)
#		
#		icoTables = gtk.image_new_from_file(getSystemResource("/pixmaps/tree_table.png"))
#		btnTables = gtk.ToggleToolButton()
#		btnTables.set_icon_widget(icoTables)
#		self._toolbar.insert(btnTables, -1)
#		
#		btnGraphics.set_active(Settings().get("LatexOutlineGraphics", True, True))
#		btnTables.set_active(Settings().get("LatexOutlineTables", True, True))
#		
#		btnGraphics.connect("toggled", self._graphicsToggled)
#		btnTables.connect("toggled", self._tablesToggled)
#		
#		self._toolbar.show_all()
#	
#	def _cursorChanged(self, treeView):
#		store, it = treeView.get_selection().get_selected()
#		if not it: 
#			return
#			
#		node = store.get_value(it, 2)
#		
#		if not node.foreign:
#			self.trigger("elementSelected", node.start, node.end)
#		
#	def _rowActivated(self, treeView, path, column):
#		it = self._treeStore.get_iter(path)
#		node = self._treeStore.get(it, 2)[0]
#		
#		if node.type == OutlineNode.REFERENCE:
#			self.trigger("referenceActivated", node.value)
#		elif node.type == OutlineNode.GRAPHICS:
#			self.trigger("graphicsActivated", node.value)
#	
#	def _tablesToggled(self, toggleButton):
#		value = toggleButton.get_active()
#		Settings().set("LatexOutlineTables", value)
#		self.trigger("tablesToggled", value)
#	
#	def _graphicsToggled(self, toggleButton):
#		value = toggleButton.get_active()
#		Settings().set("LatexOutlineGraphics", value)
#		self.trigger("graphicsToggled", value)
	
	
		
		
		