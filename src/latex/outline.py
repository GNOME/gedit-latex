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
latex.outline
"""

from logging import getLogger
import gtk
import gtk.gdk
from os.path import basename


from document import Node
from LaTeXPlugin2.concepts import Issue
from LaTeXPlugin2.outline import AbstractOutlineView
from LaTeXPlugin2.installation import getSystemResource, getUserResource
from LaTeXPlugin2.settings import Settings


class OutlineNode(list):
	
	ROOT, STRUCTURE, LABEL, NEWCOMMAND, REFERENCE, GRAPHICS, PACKAGE, TABLE = range(8)
	
	def __init__(self, type, start=None, end=None, value=None, level=None, foreign=False, numOfArgs=None):
		"""
		numOfArgs		only used for NEWCOMMAND type
		"""
		self.type = type
		self.start = start
		self.end = end
		self.value = value
		self.level = level
		self.foreign = foreign
		self.numOfArgs = numOfArgs
	
	@property
	def xml(self):
		if self.type == self.ROOT:
			return "<root>%s</root>" % "".join([child.xml for child in self])
		elif self.type == self.STRUCTURE:
			return "<structure level=\"%s\" headline=\"%s\">%s</structure>" % (self.level, self.value, 
																				"".join([child.xml for child in self]))

class Outline(object):
	def __init__(self):
		self.rootNode = OutlineNode(OutlineNode.ROOT, level=0)
		self.labels = []	# OutlineNode objects
		self.bibliographies = []
		self.colors = []
		self.packages = []	# OutlineNode objects
		self.newcommands = []	# OutlineNode objects, TODO: only the name can be stored


class OutlineGenerator(object):
	
	# FIXME: every firstOfType() may raise and IndexError!!!
	# TODO: generate issues
	
	_log = getLogger("OutlineGenerator")
	
	_STRUCTURE_LEVELS = { "part" : 1, "chapter" : 2, 
			"section" : 3, "section*" : 3,
			"subsection" : 4, "subsection*" : 4,
			"subsubsection" : 5, "subsubsection*" : 5,
			"paragraph" : 6, "subparagraph" : 7 }
	
	def __init__(self):
		self.cfgLabelsInTree = False
		self.cfgTablesInTree = Settings().get("LatexOutlineTables", True, True)
		self.cfgGraphicsInTree = Settings().get("LatexOutlineGraphics", True, True)
	
	def generate(self, documentNode, outline):
		"""
		Generates an outline model from a document model and returns a list
		of list of issues if some occured.
		"""
		
		self._issues = []
		self._outline = outline
		self._stack = [outline.rootNode]
		
		self._labelCache = {}
		
		self._walk(documentNode)
	
	def _walk(self, parentNode, foreign=False):
		"""
		Recursively walk a node in the document model
		
		foreign		if True this node is a child of a reference node, so it's coming 
					from an expanded reference
		"""
		
		childForeign = foreign
		
		for node in parentNode:
			if node.type == Node.COMMAND:
				if node.value in self._STRUCTURE_LEVELS.keys():
					try:
						headline = node.firstOfType(Node.MANDATORY_ARGUMENT).innerMarkup
						level = self._STRUCTURE_LEVELS[node.value]
						outlineNode = OutlineNode(OutlineNode.STRUCTURE, node.start, node.lastEnd, headline, level, foreign)
						
						while self._stack[-1].level >= level:
							self._stack.pop()
						
						self._stack[-1].append(outlineNode)
						self._stack.append(outlineNode)
					except IndexError:
						self._log.error("%s: Malformed structure command" % node.start)
				
				elif node.value == "label":
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText

					if value in self._labelCache.keys():
						start, end = self._labelCache[value]
						self._issues.append(Issue("Label <b>%s</b> has already been defined" % value, 
													Issue.VALIDATE_ERROR, start, end))
					else:
						self._labelCache[value] = (node.start, node.lastEnd)
					
						labelNode = OutlineNode(OutlineNode.LABEL, node.start, node.lastEnd, value, foreign=foreign)

						self._outline.labels.append(labelNode)
						if self.cfgLabelsInTree:
							self._stack[-1].append(labelNode)
				
#				elif node.value == "begin":
#					environment = str(node.filter(Node.MANDATORY_ARGUMENT)[0][0])
#					if environment == "lstlisting":
#						# look for label in listing environment
#						try:
#							# TODO: Node should have a method like toDict() or something
#							optionNode = node.filter(Node.OPTIONAL_ARGUMENT)[0]
#							option = "".join([str(child) for child in optionNode])
#							for pair in option.split(","):
#								key, value = pair.split("=")
#								if key.strip() == "label":
#									labelNode = OutlineNode(OutlineNode.LABEL, node.start, node.end, value.strip())
#									outline.labels.append(labelNode)
#									if self.cfgLabelsInTree:
#										stack[-1].append(labelNode)
#						except IndexError:
#							pass
				
				elif node.value == "usepackage":
					try:
						package = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						packageNode = OutlineNode(OutlineNode.PACKAGE, node.start, node.lastEnd, package)
						self._outline.packages.append(packageNode)
					except Exception, e:
						self._log.error("Malformed newcommand: %s" % e)
				
				elif self.cfgTablesInTree and node.value == "begin":
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					
					if environ == "tabular":
						tableNode = OutlineNode(OutlineNode.TABLE, node.start, node.lastEnd, "<i>Table</i>", foreign=foreign)
						self._stack[-1].append(tableNode)
				
				elif self.cfgGraphicsInTree and node.value == "includegraphics":
					target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					graphicsNode = OutlineNode(OutlineNode.GRAPHICS, node.start, node.lastEnd, target, foreign=foreign)
					self._stack[-1].append(graphicsNode)
				
				elif node.value == "bibliography":
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					self._outline.bibliographies.extend(value.split(","))
				
				elif node.value == "definecolor" or node.value == "xdefinecolor":
					name = str(node.firstOfType(Node.MANDATORY_ARGUMENT)[0])
					self._outline.colors.append(name)
				
				elif node.value == "newcommand":
					name = str(node.firstOfType(Node.MANDATORY_ARGUMENT)[0])[1:]	# remove "\"
					try:
						nArgs = int(node.filter(Node.OPTIONAL_ARGUMENT)[0].innerText)
					except IndexError:
						nArgs = 0
					except Exception, e:
						self._log.error("Malformed newcommand: %s" % e)
						nArgs = 0
					ncNode = OutlineNode(OutlineNode.NEWCOMMAND, node.start, node.lastEnd, name, numOfArgs=nArgs)
					self._outline.newcommands.append(ncNode)
					
					# don't walk through \newcommand
					continue
				
				elif node.value == "include" or node.value == "input":
					childForeign = True
			
			self._walk(node, childForeign)
	
	@property
	def issues(self):
		return self._issues


class OutlineTreeStore(gtk.TreeStore):
	"""
	Used to have defined columns in the outline TreeStore.
	"""

	def __init__(self):
		gtk.TreeStore.__init__(self, str, gtk.gdk.Pixbuf, object)
	
	def load(self, outlineRootNode):
		"""
		Load new outline model
		"""
		# TODO: recursive
		
		self.clear()
		
		for node in outlineRootNode:
			if node.type == OutlineNode.STRUCTURE:
				icon = self._LEVEL_ICONS[node.level]
				self.append(None, [node.value, icon, node])


class OutlineTransformer(object):
	
	_ICON_LABEL = gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/label.png"))
	_ICON_TABLE = gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_table.png"))
	_ICON_GRAPHICS = gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_includegraphics.png"))
	
	_LEVEL_ICONS = { 1 : gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_part.png")),
				2 : gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_chapter.png")),
				3 : gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_section.png")),
				4 : gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_subsection.png")),
				5 : gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_subsubsection.png")),
				6 : gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_paragraph.png")),
				7 : gtk.gdk.pixbuf_new_from_file(getSystemResource("/pixmaps/tree_paragraph.png")) }
	
	def transform(self, treeStore, outline, offsetMap):
		assert type(treeStore) is OutlineTreeStore
		
		self._offsetMap = offsetMap
		self._treeStore = treeStore
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


class OutlineView(AbstractOutlineView):
	"""
	Special outline view for LaTeX
	"""
	
	#_log = getLogger("latex.outline.OutlineView")
	
	def __init__(self, treeStore):
		AbstractOutlineView.__init__(self, treeStore)
		
		icoGraphics = gtk.image_new_from_file(getSystemResource("/pixmaps/tree_includegraphics.png"))
		btnGraphics = gtk.ToggleToolButton()
		btnGraphics.set_icon_widget(icoGraphics)
		self._toolbar.insert(btnGraphics, -1)
		
		icoTables = gtk.image_new_from_file(getSystemResource("/pixmaps/tree_table.png"))
		btnTables = gtk.ToggleToolButton()
		btnTables.set_icon_widget(icoTables)
		self._toolbar.insert(btnTables, -1)
		
		btnGraphics.set_active(Settings().get("LatexOutlineGraphics", True, True))
		btnTables.set_active(Settings().get("LatexOutlineTables", True, True))
		
		btnGraphics.connect("toggled", self._graphicsToggled)
		btnTables.connect("toggled", self._tablesToggled)
		
		self._toolbar.show_all()
	
	def _cursorChanged(self, treeView):
		store, it = treeView.get_selection().get_selected()
		if not it: 
			return
			
		node = store.get_value(it, 2)
		
		if not node.foreign:
			self.trigger("elementSelected", node.start, node.end)
		
	def _rowActivated(self, treeView, path, column):
		it = self._treeStore.get_iter(path)
		node = self._treeStore.get(it, 2)[0]
		
		if node.type == OutlineNode.REFERENCE:
			self.trigger("referenceActivated", node.value)
		elif node.type == OutlineNode.GRAPHICS:
			self.trigger("graphicsActivated", node.value)
	
	def _tablesToggled(self, toggleButton):
		value = toggleButton.get_active()
		Settings().set("LatexOutlineTables", value)
		self.trigger("tablesToggled", value)
	
	def _graphicsToggled(self, toggleButton):
		value = toggleButton.get_active()
		Settings().set("LatexOutlineGraphics", value)
		self.trigger("graphicsToggled", value)


	