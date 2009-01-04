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
#from xml.dom.minidom import parse
#from xml.parsers.expat import ExpatError
import xml.etree.ElementTree as ElementTree

from ..preferences import Preferences
from ..base import View, SideView
from ..base.resources import find_resource, MODE_READWRITE
from ..base.templates import Template
from ..issues import Issue


class SymbolCollection(object):
	"""
	A collection of symbols read from an XML file
	"""
	
	_log = getLogger("SymbolCollection")
	
	
	class Group(object):
		def __init__(self, label):
			"""
			@param label: a label for this Group
			"""
			self.label = label
			self.symbols = []
		
		
	class Symbol(object):
		def __init__(self, template, icon):
			"""
			@param template: a Template instance
			@param icon: an icon filename
			"""
			self.template = template
			self.icon = icon
	
	
	def __init__(self):
		filename = find_resource("symbols.xml")
		
		self.groups = []
		
		symbols_el = ElementTree.parse(filename).getroot()
		for group_el in symbols_el.findall("group"):
			group = self.Group(group_el.get("label"))
			for symbol_el in group_el.findall("symbol"):
				symbol = self.Symbol(Template(symbol_el.text.strip()), find_resource("icons/%s" % symbol_el.get("icon")))
				group.symbols.append(symbol)
			self.groups.append(group)
		
#		try:
#			dom = parse(filename)
#			
#			for groupEl in dom.getElementsByTagName("group"):
#				group = self.Group(groupEl.getAttribute("label"))
#				
#				counter = 0
#				
#				for symbolEl in groupEl.getElementsByTagName("symbol"):
#					source = symbolEl.getAttribute("source")
#					icon = symbolEl.getAttribute("icon")
#					
#					symbol = self.Symbol(source, find_resource("icons/%s" % icon))
#					
#					group.symbols.append(symbol)
#					
#					counter += 1
#				
#				self.groups.append(group)
#				
#		except IOError:
#			self._log.error("File not found: %s" % filename)
#		except ExpatError, s:
#			self._log.error("Parse error: %s" % s)

		
class LaTeXSymbolMapView(SideView):
	"""
	"""
	__log = getLogger("LaTeXSymbolMapView")
	
	label = "Symbols"
	icon = gtk.STOCK_INDEX
	scope = View.SCOPE_WINDOW
	
	def init(self, context):
		self.__log.debug("init")
		
		self.__context = context
		self.__preferences = Preferences()
		
		scrolled = gtk.ScrolledWindow()
		scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		scrolled.set_shadow_type(gtk.SHADOW_NONE)
		
		self.__box = gtk.VBox()
		scrolled.add_with_viewport(self.__box)
		
		self.add(scrolled)
		self.show_all()
		
		self.__load_collection(SymbolCollection())
	
	def __load_collection(self, collection):
		self.__expanded_groups = set(self.__preferences.get("ExpandedSymbolGroups", "").split(","))
		
		for group in collection.groups:
			self.__add_group(group)
	
	def __add_group(self, group):
		model = gtk.ListStore(gtk.gdk.Pixbuf, str, object)		# icon, tooltip, Template
		
		for symbol in group.symbols:
			try:
				model.append([gtk.gdk.pixbuf_new_from_file(symbol.icon), str(symbol.template), symbol.template])
			except GError, s:
				print s
		
		view = gtk.IconView(model)
		view.set_pixbuf_column(0)
		view.set_selection_mode(gtk.SELECTION_SINGLE)
		view.connect("selection-changed", self.__on_symbol_selected)
		view.set_item_width(-1)
		view.set_spacing(0)
		view.set_column_spacing(0)
		view.set_row_spacing(0)
		view.set_columns(-1)
		view.set_text_column(-1)
		
		view.set_tooltip_column(1)		# this requires PyGTK 2.12
		
		view.show()
		
		expander = gtk.Expander(group.label)
		expander.add(view)
		expander.show_all()
		
		if group.label in self.__expanded_groups:
			expander.set_expanded(True)
		
		expander.connect("notify::expanded", self.__on_group_expanded, group.label)
		
		self.__box.pack_start(expander, False)
	
	def __on_group_expanded(self, expander, paramSpec, group_label):
		"""
		The Expander for a symbol group has been expanded
		"""
		if expander.get_expanded():
			self.__expanded_groups.add(group_label)
		else:
			self.__expanded_groups.remove(group_label)
		
		self.__preferences.set("ExpandedSymbolGroups", ",".join(self.__expanded_groups))
	
	def __on_symbol_selected(self, icon_view):
		"""
		A symbol has been selected
		
		@param icon_view: the gtk.IconView 
		"""
		try: 
			path = icon_view.get_selected_items()[0]
			template = icon_view.get_model()[path][2]
			
			self.__context.active_editor.insert(template)
			
			icon_view.unselect_all()
		except IndexError:
			pass				# must be caught after unselect_all()


from os import system

from ..base import File
from ..outline import OutlineOffsetMap, BaseOutlineView
from outline import OutlineNode


class LaTeXOutlineView(BaseOutlineView):
	"""
	A View showing an outline of the edited LaTeX document
	"""
	
	_log = getLogger("LaTeXOutlineView")
	
	label = "Outline"
	scope = View.SCOPE_EDITOR
	
	@property
	def icon(self):
		image = gtk.Image()
		image.set_from_file(find_resource("icons/outline.png"))
		return image
	
	def init(self, context):
		BaseOutlineView.init(self, context)
		
		self._offset_map = OutlineOffsetMap()
		
		# additional toolbar buttons
		btn_graphics = gtk.ToggleToolButton()
		btn_graphics.set_icon_widget(gtk.image_new_from_file(find_resource("icons/tree_includegraphics.png")))
		self._toolbar.insert(btn_graphics, -1)
		
		btn_tables = gtk.ToggleToolButton()
		btn_tables.set_icon_widget(gtk.image_new_from_file(find_resource("icons/tree_table.png")))
		self._toolbar.insert(btn_tables, -1)
		
		btn_graphics.set_active(Preferences().get_bool("ShowGraphicsInOutline", True))
		btn_tables.set_active(Preferences().get_bool("ShowTablesInOutline", True))
		
		btn_graphics.connect("toggled", self._on_graphics_toggled)
		btn_tables.connect("toggled", self._on_tables_toggled)
	
	def set_outline(self, outline):
		"""
		Load a new outline model
		"""
		self.assure_init()
		
		self._save_state()
		
		self._offset_map = OutlineOffsetMap()
		OutlineConverter().convert(self._store, outline, self._offset_map, self._context.active_editor.edited_file)
		
		self._restore_state()
	
	def _on_node_selected(self, node):
		"""
		An outline node has been selected
		"""
		if Preferences().get_bool("ConnectOutlineToEditor", True):
			if node.file == self._context.active_editor.edited_file:
				self._context.active_editor.select(node.start, node.end)
	
	def _on_node_activated(self, node):
		"""
		An outline node has been double-clicked on
		
		@param node: an instance of latex.outline.OutlineNode
		"""
		if node.type == OutlineNode.GRAPHICS:
			# use 'gnome-open' to open the graphics file
			
			target = node.value
			
			if not target:
				return
			
			if target.startswith("/"):
				filename = target
			else:
				filename = "%s/%s" % (node.file.dirname, target)
			
			f = File(filename)
			
			if not f.exists:
				self._log.error("File not found: %s" % filename)
				return
			
			system("gnome-open %s" % filename)
			
		else:
			# open/activate the referenced file, if the node is 'foreign'
			
			if node.file != self._context.active_editor.edited_file:
				self._context.activate_editor(node.file)
	
	def _on_tables_toggled(self, toggle_button):
		value = toggle_button.get_active()
#		Settings().set("LatexOutlineTables", value)
#		self.trigger("tablesToggled", value)
		Preferences().set("ShowTablesInOutline", value)
	
	def _on_graphics_toggled(self, toggle_button):
		value = toggle_button.get_active()
#		Settings().set("LatexOutlineGraphics", value)
#		self.trigger("graphicsToggled", value)
		Preferences().set("ShowGraphicsInOutline", value)
	
	

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
	
	def __init__(self):
		self._preferences = Preferences()
	
	def convert(self, tree_store, outline, offset_map, file):
		"""
		Convert an Outline object to a gtk.TreeStore and update an OutlineOffsetMap
		
		@param tree_store: gtk.TreeStore
		@param outline: latex.outline.Outline
		@param offset_map: outline.OutlineOffsetMap
		@param file: the edited File (to identify foreign outline nodes)
		"""
		self._offsetMap = offset_map
		self._treeStore = tree_store
		self._treeStore.clear()
		self._file = file
		
		self._append(None, outline.rootNode)
	
	def _append(self, parent, node):
		"""
		Recursively append an outline node to the TreeStore
		
		@param parent: a gtk.TreeIter or None
		@param node: an OutlineNode
		"""
		value = node.value
		
		color = self._preferences.get("LightForeground", "#957d47")
		
		if node.file and node.file != self._file:
			value = "%s <span color='%s'>%s</span>" % (value, color, node.file.shortbasename)
		
		if node.type == OutlineNode.STRUCTURE:
			icon = self._LEVEL_ICONS[node.level]
			parent = self._treeStore.append(parent, [value, icon, node])
		elif node.type == OutlineNode.LABEL:
			parent = self._treeStore.append(parent, [value, self._ICON_LABEL, node])
		elif node.type == OutlineNode.TABLE:
			parent = self._treeStore.append(parent, [value, self._ICON_TABLE, node])
		elif node.type == OutlineNode.GRAPHICS:
			label = basename(node.value)
			
			if node.file and node.file != self._file:
				label = "%s <span color='%s'>%s</span>" % (label, color, node.file.shortbasename)
				
			parent = self._treeStore.append(parent, [label, self._ICON_GRAPHICS, node])
		
		# store path in offset map for all non-foreign nodes
		# check for parent to ignore root node
		if parent and not node.foreign:
			path = self._treeStore.get_path(parent)
			self._offsetMap.put(node.start, path)
			
		for child in node:
			self._append(parent, child)



	