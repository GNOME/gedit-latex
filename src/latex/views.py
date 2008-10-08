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
		
		
class LaTeXSymbolMapView(View):
	"""
	"""
	_log = getLogger("LaTeXSymbolMapView")
	
	position = View.POSITION_SIDE
	label = "Symbols"
	icon = gtk.STOCK_INDEX
	scope = View.SCOPE_WINDOW
	
	def init(self, context):
		self._log.debug("init")


from ..outline import OutlineOffsetMap


class LaTeXOutlineView(View):
	"""
	A View showing an outline of the edited LaTeX document
	"""
	
	_log = getLogger("LaTeXOutlineView")
	
	position = View.POSITION_SIDE
	label = "Outline"
	scope = View.SCOPE_EDITOR
	
	@property
	def icon(self):
		image = gtk.Image()
		image.set_from_file(find_resource("icons/outline.png"))
		return image
	
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
		
		self._offset_map = OutlineOffsetMap()
		
		self._store = gtk.TreeStore(str, gtk.gdk.Pixbuf, object)
		
		self._view = gtk.TreeView(self._store)
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
	
	def select_path_by_offset(self, offset):
		"""
		Select the path corresponding to a given offset in the source
		"""
		self.assure_init()
		
		try:
			path = self._offset_map.lookup(offset)
			self._select_path(path)
		except KeyError:
			pass
	
	def set_outline(self, outline):
		"""
		Load a new outline model
		"""
		self.assure_init()
		
		self._save_state()
		
		self._offset_map = OutlineOffsetMap()
		OutlineConverter().convert(self._store, outline, self._offset_map)
		
		self._restore_state()
	
	def _save_state(self):
		"""
		Save the current expand state
		"""
		self._expanded_paths = []
		self._view.map_expanded_rows(self._save_state_map_function)
	
	def _save_state_map_function(self, view, path):
		"""
		Mapping function for saving the current expand state
		"""
		self._expanded_paths.append(path)
	
	def _restore_state(self):
		"""
		Restore the last expand state
		"""
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
	
	def _select_path(self, path):
		"""
		Expand a path and select the last node
		"""
		# disconnect from 'cursor-changed'
		self._view.disconnect(self._cursor_changed_id)
		
		# select path
		self._view.expand_to_path(path)
		self._view.set_cursor(path)
		
		# connect to 'cursor-changed' again
		self._cursor_changed_id = self._view.connect("cursor-changed", self._on_cursor_changed)
	


from ..base.resources import find_resource
from outline import OutlineNode
from os.path import basename


class OutlineConverter(object):
	"""
	This creates a gtk.TreeStore object from a LaTeX outline model
	"""
	
	_ICON_LABEL = gtk.gdk.pixbuf_new_from_file(find_resource("icons/label.png"))
	_ICON_TABLE = gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_table.png"))
	_ICON_GRAPHICS = gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_includegraphics.png"))
	
	_LEVEL_ICONS = { 1 : gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_part.png")),
				2 : gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_chapter.png")),
				3 : gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_section.png")),
				4 : gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_subsection.png")),
				5 : gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_subsubsection.png")),
				6 : gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_paragraph.png")),
				7 : gtk.gdk.pixbuf_new_from_file(find_resource("icons/tree_paragraph.png")) }
	
	def convert(self, tree_store, outline, offset_map):
		self._offsetMap = offset_map
		self._treeStore = tree_store
		self._treeStore.clear()
		
		self._load(None, outline.rootNode)
	
	def _load(self, parent, node):
		if node.type == OutlineNode.STRUCTURE:
			icon = self._LEVEL_ICONS[node.level]
			parent = self._treeStore.append(parent, [node.value, icon, node])
		elif node.type == OutlineNode.LABEL:
			parent = self._treeStore.append(parent, [node.value, self._ICON_LABEL, node])
		elif node.type == OutlineNode.TABLE:
			parent = self._treeStore.append(parent, [node.value, self._ICON_TABLE, node])
		elif node.type == OutlineNode.GRAPHICS:
			label = basename(node.value)
			parent = self._treeStore.append(parent, [label, self._ICON_GRAPHICS, node])
		
		# store path in offset map for all non-foreign nodes
		# check for parent to ignore root node
		if parent and not node.foreign:
			path = self._treeStore.get_path(parent)
			self._offsetMap.put(node.start, path)
			
		for child in node:
			self._load(parent, child)


		
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
	
	
		
		
		