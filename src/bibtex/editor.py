# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2009 Michael Zeising
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
bibtex.editor
"""

from logging import getLogger

from ..base import Editor
from ..preferences import Preferences
from ..issues import Issue, IIssueHandler
from ..util import verbose

from parser import BibTeXParser
from completion import BibTeXCompletionHandler
from validator import BibTeXValidator

BENCHMARK = True

if BENCHMARK:
	import time

class BibTeXEditor(Editor, IIssueHandler):
	
	_log = getLogger("BibTeXEditor")
	
	@property
	def completion_handlers(self):
		self.__bibtex_completion_handler = BibTeXCompletionHandler()
		return [ self.__bibtex_completion_handler ]
	
	def init(self, file, context):
		self._log.debug("init(%s)" % file)
		
		self._preferences = Preferences()
		
		self._file = file
		self._context = context
		
		self.register_marker_type("bibtex-error", self._preferences.get("ErrorBackgroundColor"))
		self.register_marker_type("bibtex-warning", self._preferences.get("WarningBackgroundColor"))
		
		self._issue_view = context.find_view(self, "IssueView")
		self._parser = BibTeXParser()
		self._validator = BibTeXValidator()
		self._outline_view = context.find_view(self, "BibTeXOutlineView")
		
		self._connect_outline_to_editor = True	# TODO: read from config
		
		# initially parse
		self.__parse()
	
	def on_save(self):
		"""
		The file has been saved
		
		Update models
		"""
		self.__parse()
	
	@verbose
	def __parse(self):
		"""
		"""
		self._log.debug("__parse")
		
		content = self.content
		
		# reset highlight
		self.remove_markers("bibtex-error")
		self.remove_markers("bibtex-warning")
		
		# reset issues
		self._issue_view.clear()
		
#		self.parse(self._file)
		
		if BENCHMARK: t = time.clock()
		
		# parse document
		self._document = self._parser.parse(content, self._file, self)
		
		if BENCHMARK: self._log.info("BibTeXParser.parse: %f" % (time.clock() - t))
		
		self._log.debug("Parsed %s bytes of content" % len(content))
		
		# validate
		if BENCHMARK: t = time.clock()
		
		self._validator.validate(self._document, self._file, self)
		
		# 0.11
		if BENCHMARK: self._log.info("BibTeXValidator.validate: %f" % (time.clock() - t))
		
		self._outline_view.set_outline(self._document)
	
#	def _on_parser_finished(self, model):
#		"""
#		"""
#		self._document = model
#		self._outline_view.set_outline(self._document)
	
	def issue(self, issue):
		# overriding IIssueHandler.issue
		
		self._issue_view.append_issue(issue)
		
		if issue.file == self._file:
			if issue.severity == Issue.SEVERITY_ERROR:
				self.create_marker("bibtex-error", issue.start, issue.end)
			elif issue.severity == Issue.SEVERITY_WARNING:
				self.create_marker("bibtex-warning", issue.start, issue.end)
	
	def on_cursor_moved(self, offset):
		"""
		The cursor has moved
		"""
		if self._preferences.get_bool("ConnectOutlineToEditor", True):
			self._outline_view.select_path_by_offset(offset)
		
		
		