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


from parser import Node
from ..issues import Issue


class OutlineNode(list):
	
	ROOT, STRUCTURE, LABEL, NEWCOMMAND, REFERENCE, GRAPHICS, PACKAGE, TABLE = range(8)
	
	def __init__(self, type, start=None, end=None, value=None, level=None, foreign=False, numOfArgs=None, file=None):
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
		self.file = file
	
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
		self.labels = []			# OutlineNode objects
		self.bibliographies = []	# File objects
		self.colors = []
		self.packages = []			# OutlineNode objects
		self.newcommands = []		# OutlineNode objects, TODO: only the name can be stored


from ..base import File


class LaTeXOutlineGenerator(object):
	
	_log = getLogger("LaTeXOutlineGenerator")
	
	# TODO: foreign flag is not necessary
	
	_STRUCTURE_LEVELS = { "part" : 1, 
						  "chapter" : 2, 
						  "section" : 3, "section*" : 3,
						  "subsection" : 4, "subsection*" : 4,
						  "subsubsection" : 5, "subsubsection*" : 5,
						  "paragraph" : 6, 
						  "subparagraph" : 7 }
	
	def __init__(self):
		# TODO: read config
		self.cfgLabelsInTree = True
		self.cfgTablesInTree = True
		self.cfgGraphicsInTree = True
	
	def generate(self, documentNode, issue_handler):
		"""
		Generates an outline model from a document model and returns a list
		of list of issues if some occured.
		"""
		
		self._issue_handler = issue_handler
		self._outline = Outline()
		self._stack = [self._outline.rootNode]
		
		self._labelCache = {}
		
#		self._file = documentNode.value		# this is updated when a DOCUMENT occurs
		
		self._walk(documentNode)
		
		return self._outline
	
	def _walk(self, parentNode, foreign=False):
		"""
		Recursively walk a node in the document model
		
		foreign		if True this node is a child of a reference node, so it's coming 
					from an expanded reference
		"""
		
		childForeign = foreign
		
		for node in parentNode:
#			if node.type == Node.DOCUMENT:
#				self._file = node.value
			if node.type == Node.COMMAND:
				if node.value in self._STRUCTURE_LEVELS.keys():
					try:
						headline = node.firstOfType(Node.MANDATORY_ARGUMENT).innerMarkup
						level = self._STRUCTURE_LEVELS[node.value]
						outlineNode = OutlineNode(OutlineNode.STRUCTURE, node.start, node.lastEnd, headline, level, foreign, file=node.file)
						
						while self._stack[-1].level >= level:
							self._stack.pop()
						
						self._stack[-1].append(outlineNode)
						self._stack.append(outlineNode)
					except IndexError:
						self._issue_handler.issue(Issue("Malformed structure command", node.start, node.end, node.file, Issue.SEVERITY_ERROR))
				
				elif node.value == "label":
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText

					if value in self._labelCache.keys():
						start, end = self._labelCache[value]
						self._issue_handler.issue(Issue("Label <b>%s</b> has already been defined" % value, start, end, node.file, Issue.SEVERITY_ERROR))
					else:
						self._labelCache[value] = (node.start, node.lastEnd)
					
						labelNode = OutlineNode(OutlineNode.LABEL, node.start, node.lastEnd, value, foreign=foreign, file=node.file)

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
						packageNode = OutlineNode(OutlineNode.PACKAGE, node.start, node.lastEnd, package, file=node.file)
						self._outline.packages.append(packageNode)
					except Exception, e:
						self._issue_handler.issue(Issue("Malformed usepackage command", node.start, node.end, node.file, Issue.SEVERITY_ERROR))
				
				elif self.cfgTablesInTree and node.value == "begin":
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					
					if environ == "tabular":
						tableNode = OutlineNode(OutlineNode.TABLE, node.start, node.lastEnd, "", foreign=foreign, file=node.file)
						self._stack[-1].append(tableNode)
				
				elif self.cfgGraphicsInTree and node.value == "includegraphics":
					target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					graphicsNode = OutlineNode(OutlineNode.GRAPHICS, node.start, node.lastEnd, target, foreign=foreign, file=node.file)
					self._stack[-1].append(graphicsNode)
				
				elif node.value == "bibliography":
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					
					for bib in value.split(","):
						self._outline.bibliographies.append(File("%s/%s.bib" % (node.file.dirname, bib)))
				
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
						self._issue_handler.issue(Issue("Malformed newcommand", node.start, node.end, node.file, Issue.SEVERITY_ERROR))
						nArgs = 0
					ncNode = OutlineNode(OutlineNode.NEWCOMMAND, node.start, node.lastEnd, name, numOfArgs=nArgs, file=node.file)
					self._outline.newcommands.append(ncNode)
					
					# don't walk through \newcommand
					continue
				
				elif node.value == "include" or node.value == "input":
					childForeign = True
			
			self._walk(node, childForeign)



	
	
	