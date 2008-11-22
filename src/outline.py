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
outline

Classes used for creating an outline view of LaTeX and BibTeX files
"""

from logging import getLogger
import gtk

from base import View, SideView
from preferences import Preferences
from base.resources import find_resource


class BaseOutlineView(SideView):
	"""
	Base class for the BibTeX and LaTeX outline views
	"""
	
	__log = getLogger("BaseOutlineView")
	
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
		
		self._preferences = Preferences()

		# toolbar

		btn_follow = gtk.ToggleToolButton(gtk.STOCK_CONNECT)
		btn_follow.set_tooltip_text("Follow Editor")
		btn_follow.set_active(self._preferences.get_bool("ConnectOutlineToEditor", True))
		btn_follow.connect("toggled", self._on_follow_toggled)
		
		btn_expand = gtk.ToolButton(gtk.STOCK_ZOOM_IN)
		btn_expand.set_tooltip_text("Expand All")
		btn_expand.connect("clicked", self._on_expand_clicked)
		
		btn_collapse = gtk.ToolButton(gtk.STOCK_ZOOM_OUT)
		btn_collapse.set_tooltip_text("Collapse All")
		btn_collapse.connect("clicked", self._on_collapse_clicked)
		
		self._toolbar = gtk.Toolbar()
		self._toolbar.set_style(gtk.TOOLBAR_ICONS)
		# TODO: why is this deprecated?
		self._toolbar.set_icon_size(gtk.ICON_SIZE_MENU)
		self._toolbar.insert(btn_follow, -1)
		self._toolbar.insert(gtk.SeparatorToolItem(), -1)
		self._toolbar.insert(btn_expand, -1)
		self._toolbar.insert(btn_collapse, -1)
		self._toolbar.insert(gtk.SeparatorToolItem(), -1)
		
		self.pack_start(self._toolbar, False)
		
		# tree view
		
		column = gtk.TreeViewColumn()
		
		pixbuf_renderer = gtk.CellRendererPixbuf()
		column.pack_start(pixbuf_renderer, False)
		column.add_attribute(pixbuf_renderer, "pixbuf", 1)
		
		text_renderer = gtk.CellRendererText()
		column.pack_start(text_renderer, True)
		column.add_attribute(text_renderer, "markup", 0)
		
		self._offset_map = OutlineOffsetMap()
		
		self._store = gtk.TreeStore(str, gtk.gdk.Pixbuf, object)	# label, icon, node object
		
		self._view = gtk.TreeView(self._store)
		self._view.append_column(column)
		self._view.set_headers_visible(False)
		self._cursor_changed_id = self._view.connect("cursor-changed", self._on_cursor_changed)
		self._view.connect("row-activated", self._on_row_activated)
		
		scrolled = gtk.ScrolledWindow()
		scrolled.add(self._view)
		scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		
		self.pack_start(scrolled, True)
		
		# this holds a list of the currently expanded paths
		self._expandedPaths = None
		
		self.show_all()
	
	def _on_follow_toggled(self, toggle_button):
		value = toggle_button.get_active()
		#Settings().set("LinkOutlineToEditor", value)
		
		#self.trigger("connectToggled", value)
	
	def _on_expand_clicked(self, button):
		self._view.expand_all()
	
	def _on_collapse_clicked(self, button):
		self._view.collapse_all()
	
	def select_path_by_offset(self, offset):
		"""
		Select the path corresponding to a given offset in the source
		
		Called by the Editor
		"""
		self.assure_init()
		
		try:
			path = self._offset_map.lookup(offset)
			self._select_path(path)
		except KeyError:
			pass
	
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
		
		self._on_node_selected(outline_node)
	
	def _on_row_activated(self, view, path, column):
		it = self._store.get_iter(path)
		node = self._store.get(it, 2)[0]
		
		self._on_node_activated(node)
	
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
	
	#
	# methods to be overridden by the subclass
	#
	
	def _on_node_selected(self, node):
		"""
		To be overridden
		"""
	
	def _on_node_activated(self, node):
		"""
		To be overridden
		"""
		
	def set_outline(self, outline):
		"""
		Load a new outline model
		
		To be overridden
		"""


class OutlineOffsetMap(object):
	"""
	This stores a mapping from the start offsets of outline elements 
	to paths in the outline tree.
	
	We need this for the 'connect-outline-to-editor' feature.
	
	We may not use a simple dictionary for that because we need some
	kind of neighborhood lookup as we never get the exact offsets.
	"""
	
	# TODO: find a faster structure for this - but what is this?
	
	def __init__(self):
		self._map = {}
	
	def clear(self):
		self._map = {}
	
	def put(self, offset, path):
		self._map[offset] = path
	
	def lookup(self, offset):
		"""
		Returns the outline element containing a certain offset
		"""
		
		# sort offsets
		offsets = self._map.keys()
		offsets.sort()
		
		# find nearest offset
		nearestOffset = None
		for o in offsets:
			if o > offset:
				break
			nearestOffset = o
		
		if not nearestOffset:
			raise KeyError
		
		return self._map[nearestOffset]
	
	def __str__(self):
		s = "<OutlineOffsetMap>"
		
		ofs = self._map.keys()
		ofs.sort()
		
		for o in ofs:
			s += "\n\t%s : %s" % (o, self._map[o])
		s += "\n</OutlineOffsetMap>"
		return s

