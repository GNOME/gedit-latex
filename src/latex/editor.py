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

from ..base.util import RangeMap
from outline import OutlineConverter
from ..outline import OutlineOffsetMap


class LaTeXEditor(Editor, IIssueHandler):
	
	# TODO: use _document_dirty
	
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
		
		self.register_marker_type("latex-spell", "#ffeccf", anonymous=False)
		self.register_marker_type("latex-error", "#ffdddd")
		self.register_marker_type("latex-warning", "#ffffcf")
		
		self._issue_view = context.views["LaTeXIssueView"]
		
		self._parser = LaTeXParser()
		self._document_dirty = True
		
		self._offset_map = OutlineOffsetMap()
		self._outline_tree_store = gtk.TreeStore(str, gtk.gdk.Pixbuf, object)
		self._outline_view = context.views["LaTeXOutlineView"]
		self._outline_view.set_model(self._outline_tree_store)
		
		self._connect_outline_to_editor = True	# TODO: read from config
		
		#
		# initially parse
		#
		self._log.debug("Initial parse")
		
		self._parse()
	
	def save(self):
		"""
		The file has been saved
		
		Update models
		"""
		self._parse()
	
	@caught
	def _parse(self):
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
			else:
				self._log.debug("Document is not a master")
				
				# find master
				master_file = find_master_document(self._file)
				# parse master
				master_content = open(master_file.path).read()
				self._document = self._parser.parse(master_content, master_file, self)
				# expand its child documents
				expander = LaTeXReferenceExpander()
				expander.expand(self._document, master_file, self)
			
			# generate outline
			self._outline_generator = LaTeXOutlineGenerator()
			self._outline = self._outline_generator.generate(self._document, self)
			
			# validate
			self._validator = LaTeXValidator()
			self._validator.validate(self._document, self._outline, self._file, self)
			
			# convert outline model and pass to outline view
			self._offset_map = OutlineOffsetMap()
			self._outline_view.save_state()
			OutlineConverter().convert(self._outline_tree_store, self._outline, self._offset_map)
			self._outline_view.restore_state()
	
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
		self._log.debug("spell_check")
		
		self.remove_markers("latex-spell")
		
		id = self.create_marker("latex-spell", 15, 30)
	
	def activate_marker(self, marker, event):
		"""
		A marker has been activated
		"""
		self._log.debug("activate_marker(%s, %s)" % (marker, event))
	
	def move_cursor(self, offset):
		"""
		The cursor has moved
		"""
		if self._connect_outline_to_editor:
			try:
				path = self._offset_map.lookup(offset)
				self._outline_view.select_path(path)
			except KeyError:
				pass
	
#	def destroy(self):
#		Editor.destroy(self)


def find_master_document(file):
	# TODO:
	raise RuntimeError("Master not found")
	
	
	
	
	
	
	
	
	
	
	