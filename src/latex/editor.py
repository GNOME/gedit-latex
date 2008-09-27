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
latex.editor
"""

import gtk
import gtk.gdk
from logging import getLogger

from ..base import Editor
from completion import LaTeXCompletionHandler
from ..snippets.completion import SnippetCompletionHandler
from ..issues import Issue, IIssueHandler
from ..util import caught

from parser import LaTeXParser, LaTeXReferenceExpander
from outline import LaTeXOutlineGenerator
from validator import LaTeXValidator

from dialogs import ChooseMasterDialog

from . import LaTeXSource


class LaTeXEditor(Editor, IIssueHandler):
	
	# TODO: use _document_dirty
	
	_log = getLogger("LaTeXEditor")
	
	@property
	def completion_handlers(self):
		self.__latex_completion_handler = LaTeXCompletionHandler()
		self.__snippet_completion_handler = SnippetCompletionHandler()
		
		return [ self.__latex_completion_handler, self.__snippet_completion_handler ]
	
	def init(self, file, context):
		self._log.debug("init(%s)" % file)
		
		self._file = file
		self._context = context
		
		self.register_marker_type("latex-spell", "#ffeccf", anonymous=False)
		self.register_marker_type("latex-error", "#ffdddd")
		self.register_marker_type("latex-warning", "#ffffcf")
		
		self._issue_view = context.find_view(self, "LaTeXIssueView")
		
		self._parser = LaTeXParser()
		self._document_dirty = True
		
		self._outline_view = context.find_view(self, "LaTeXOutlineView")
		
		self._connect_outline_to_editor = True	# TODO: read from config
		
		#
		# initially parse
		#
		self._log.debug("Initial parse")
		
		self.__parse()
		self.__update_neighbors()
	
	def insert(self, source):
		# see base.Editor.insert()
		
		if type(source) is LaTeXSource:
			# TODO: ensure that the required packages are included
			
			Editor.insert(self, source.source)
		else:
			Editor.insert(self, source)
	
	def on_save(self):
		"""
		The file has been saved
		
		Update models
		"""
		self.__parse()
		self.__update_neighbors()
	
	def __update_neighbors(self):
		"""
		Find all files in the working directory that are relevant for LaTeX, e.g.
		other *.tex files or images.
		"""
		
		# TODO: this is only needed to feed the LaTeXCompletionHandler. So maybe it should
		# know the edited file and the Editor should call an update() method of the handler
		# when the file is saved.
		
		tex_files = self._file.find_neighbors(".tex")
		bib_files = self._file.find_neighbors(".bib")
		
		graphic_files = []
		for extension in [".ps", ".pdf", ".png", ".jpg", ".eps"]:
			graphic_files.extend(self._file.find_neighbors(extension))
		
		self.__latex_completion_handler.set_neighbors(tex_files, bib_files, graphic_files)
	
	@caught
	def __parse(self):
		"""
		"""
		if self._document_dirty:
			self._log.debug("Parsing content")
			
			# reset highlight
			self.remove_markers("latex-error")
			self.remove_markers("latex-warning")
			
			# reset issues
			self._issue_view.clear()
			
			# parse document
			self._document = self._parser.parse(self.content, self._file, self)
			
			self._log.debug("Parsed %s bytes of content" % len(self.content))
			
			if self._document.is_master:
				# expand child documents
				expander = LaTeXReferenceExpander()
				expander.expand(self._document, self._file, self)
				
				self._context.set_action_enabled("LaTeXChooseMasterAction", False)
			else:
				self._log.debug("Document is not a master")
				
				# find master
				master_file = self._find_master_document()
				# parse master
				master_content = open(master_file.path).read()
				self._document = self._parser.parse(master_content, master_file, self)
				# expand its child documents
				expander = LaTeXReferenceExpander()
				expander.expand(self._document, master_file, self)
				
				self._context.set_action_enabled("LaTeXChooseMasterAction", True)
			
			# generate outline
			self._outline_generator = LaTeXOutlineGenerator()
			self._outline = self._outline_generator.generate(self._document, self)
			
			# validate
			self._validator = LaTeXValidator()
			self._validator.validate(self._document, self._outline, self._file, self)
			
			# pass outline to view
			self._outline_view.set_outline(self._outline)
			
			self.__latex_completion_handler.set_outline(self._outline)
	
	def _find_master_document(self):
		property_file = PropertyFile(self._file)
		try:
			return File(property_file["MasterFilename"])
		except KeyError:
			master_filename = ChooseMasterDialog().run(self._file.dirname)
			if master_filename:
				property_file["MasterFilename"] = master_filename
				property_file.save()
				return File(master_filename)
			else:
				raise RuntimeError("No master file chosen")
	
	def issue(self, issue):
		#
		# see IIssueHandler.issue
		#
		self._issue_view.append_issue(issue)
		
		if issue.file == self._file:
			if issue.severity == Issue.SEVERITY_ERROR:
				self.create_marker("latex-error", issue.start, issue.end)
			elif issue.severity == Issue.SEVERITY_WARNING:
				self.create_marker("latex-warning", issue.start, issue.end)
	
	def spell_check(self):
		"""
		Run a spell check on the file
		"""
		self._log.debug("spell_check")
		
		self.remove_markers("latex-spell")
		
		id = self.create_marker("latex-spell", 15, 30)
	
	def on_marker_activated(self, marker, event):
		"""
		A marker has been activated
		"""
		self._log.debug("activate_marker(%s, %s)" % (marker, event))
	
	def on_cursor_moved(self, offset):
		"""
		The cursor has moved
		"""
		if self._connect_outline_to_editor:
			self._outline_view.select_path_by_offset(offset)


from xml.dom import minidom
from xml.parsers.expat import ExpatError

from ..base import File


class PropertyFile(dict):
	"""
	A property file is a hidden XML file that holds meta data for exactly one file.
	It can be used to store the master file of a LaTeX document fragment.
	"""
	
	__log = getLogger("PropertyFile")
	
	# TODO: insert value as TEXT node
	
	def __init__(self, file):
		"""
		Create or load the property file for a given File
		"""
		self.__file = File("%s/.%s.properties.xml" % (file.dirname, file.basename))
		
		try:
			self.__dom = minidom.parse(self.__file.path)
			
			for property_node in self.__dom.getElementsByTagName("property"):
				k = property_node.getAttribute("key")
				v = property_node.getAttribute("value")
				self.__setitem__(k, v)
				
		except IOError:
			self.__log.debug("File %s not found, creating empty one" % self.__file)
			
			self.__dom = minidom.getDOMImplementation().createDocument(None, "properties", None)
		
		except ExpatError, e:
			self.__log.error("Error parsing %s: %s" % (self.__file, e))
		
	
	def __find_node(self, k):
		for node in self.__dom.getElementsByTagName("property"):
			if node.getAttribute("key") == str(k):
				return node
		raise KeyError
	
	def __getitem__(self, k):
		return self.__find_node(k).getAttribute("value")
	
	def __setitem__(self, k, v):
		try:
			self.__find_node(k).setAttribute("value", str(v))
		except KeyError:
			node = self.__dom.createElement("property")
			node.setAttribute("key", str(k))
			node.setAttribute("value", str(v))
			self.__dom.documentElement.appendChild(node)
	
	def save(self):
		filename = self.__file.path
		
		if self.__file.exists:
			mode = "w"
		else:
			mode = "a"
		
		try:
			f = open(self.__file.path, mode)
			f.write(self.__dom.toxml())
			f.close()
			self.__log.debug("Saved to %s" % self.__file.path)
		except IOError, e:
			self.__log.error("Error saving %s: %s" % (self.__file.path, e))
	
	
	
	
	
	
	
	
	