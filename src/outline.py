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

from base import View


#class BaseOutlineView(View):
#	"""
#	The OutlineViews for LaTeX and BibTeX are derived from this one
#	"""
#	
#	_log = getLogger("BaseOutlineView")
#	
#	def init(self):
#		
#		#
#		# build toolbar - contains the "connect" toggle button per default
#		#
#		btnConnect = gtk.ToggleToolButton(gtk.STOCK_CONNECT)
#		btnConnect.set_tooltip_text("Connect Outline to Editor")
#		btnConnect.set_active(Settings().get("LinkOutlineToEditor", True, True))
#		btnConnect.connect("toggled", self._connectToggled)
#		
#		btn_expand = gtk.ToolButton(gtk.STOCK_ZOOM_IN)
#		btn_expand.set_tooltip_text("Expand all")
#		btn_expand.connect("clicked", self._on_expand_clicked)
#		
#		btn_collapse = gtk.ToolButton(gtk.STOCK_ZOOM_OUT)
#		btn_collapse.set_tooltip_text("Collapse all")
#		btn_collapse.connect("clicked", self._on_collapse_clicked)
#		
#		self._toolbar = gtk.Toolbar()
#		self._toolbar.set_style(gtk.TOOLBAR_ICONS)
#		self._toolbar.set_icon_size(gtk.ICON_SIZE_MENU)
#		self._toolbar.insert(btnConnect, -1)
#		self._toolbar.insert(gtk.SeparatorToolItem(), -1)
#		self._toolbar.insert(btn_expand, -1)
#		self._toolbar.insert(btn_collapse, -1)
#		self._toolbar.insert(gtk.SeparatorToolItem(), -1)
#		
#		self.pack_start(self._toolbar, False)
#		#
#		# tree view
#		#
#		column = gtk.TreeViewColumn()
#		
#		pixbuf_renderer = gtk.CellRendererPixbuf()
#		column.pack_start(pixbuf_renderer, False)
#		column.add_attribute(pixbuf_renderer, "pixbuf", 1)
#		
#		text_renderer = gtk.CellRendererText()
#		column.pack_start(text_renderer, True)
#		column.add_attribute(text_renderer, "markup", 0)
#		
#		self._treeView = gtk.TreeView()
#		self._treeView.append_column(column)
#		self._treeView.set_headers_visible(False)
#		self._cursorChangedId = self._treeView.connect("cursor-changed", self._cursorChanged)
#		self._treeView.connect("row-activated", self._rowActivated)
#		
#		scrolledWindow = gtk.ScrolledWindow()
#		scrolledWindow.add(self._treeView)
#		scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
#		
#		self.pack_start(scrolledWindow, True)
#		
#		self.show_all()
#		
#		self._expandedPaths = None	# the list of paths currently expanded
#	
#	def jumpToPath(self, path):
#		"""
#		This is used by the "connect-tree-to-editor"-feature
#		"""
#		# disconnect
#		self._treeView.disconnect(self._cursorChangedId)
#		
#		# select
#		self._treeView.expand_to_path(path)
#		self._treeView.set_cursor(path)
#		
#		# connect again
#		self._cursorChangedId = self._treeView.connect("cursor-changed", self._cursorChanged)
#	
#	def save_state(self):
#		"""
#		Store a list of paths of the expanded rows 
#		"""
#		self._expandedPaths = []
#		self._treeView.map_expanded_rows(self._mapFunc)
#	
#	def _mapFunc(self, treeView, path):
#		"""
#		Mapping function for collecting the expand state
#		"""
#		self._expandedPaths.append(path)
#	
#	def restore_state(self):
#		"""
#		Expand all paths stored in the list
#		"""
#		self._treeView.collapse_all()
#		
#		if self._expandedPaths:
#			for path in self._expandedPaths:
#				self._treeView.expand_to_path(path)
#		else:
#			self._treeView.expand_to_path((0,))
#	
#	def _cursorChanged(self, treeView):
#		self._log.debug("_cursorChanged")
#		
#	def _rowActivated(self, treeView, path, column):
#		self._log.debug("_rowActivated")
#		
#	def _connectToggled(self, toggleButton):
#		value = toggleButton.get_active()
#		Settings().set("LinkOutlineToEditor", value)
#		
#		self.trigger("connectToggled", value)
#	
#	def _on_expand_clicked(self, button):
#		self._treeView.expand_all()
#	
#	def _on_collapse_clicked(self, button):
#		self._treeView.collapse_all()
#		
#	def set_outline_model(self, model):
#		self._treeView.set_model(model)
		

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

