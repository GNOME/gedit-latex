# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2010 Michael Zeising
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
latex.archive
"""

from parser import LaTeXParser, Node
from expander import LaTeXReferenceExpander
from ..issues import MockIssueHandler


class Dependency:
	def __init__(self, original_filename):
		self.original_filename = original_filename


class LaTeXArchiver:
	def archive(self, file):
		"""
		@param file: the master document File object 
		"""
		self._file = file
		self._scan()
	
	def _scan(self):
		"""
		Scan the document for dependencies
		"""
		self._dependencies = []
		scanner = LaTeXDependencyScanner()
		for filename in scanner.scan(self._file):
			self._dependencies.append(Dependency(filename))
	
	def _copy_to_sandbox(self):
		"""
		Copy the document and its dependencies to a sandbox folder
		"""
		pass
	
	def _repair_references(self):
		"""
		Repair eventually broken absolute paths
		"""
		pass
	
	def _pack(self):
		"""
		Pack the document and its deps into an archive
		"""
		pass


class LaTeXDependencyScanner:
	"""
	This analyzes a document and recognizes its dependent files
	
	@deprecated: 
	"""
	def __init__(self):
		self._parser = LaTeXParser()
		self._expander = LaTeXReferenceExpander()
	
	def scan(self, file):
		# parse
		content = open(file.path, "r").read()
		self._document = self._parser.parse(content, file, MockIssueHandler())
		self._expander.expand(self._document, file, MockIssueHandler(), None)
		# search
		self._filenames = []
		self._search(self._document)
		
		# TODO: add all filenames that match a regex
		
		return self._filenames
	
	def _search(self, parent):
		# search the model for all \in* commands
		for node in parent:
			if node.type == Node.COMMAND:
				if node.value.startswith("in"):
					try:
						argument = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						# TODO: match against regex for filenames and create File object
						if argument.startswith("/"):
							filename = argument
						else:
							filename = node.file.dirname + "/" + argument
						if node.value in ["include", "input"]:
							filename += ".tex"
						self._filenames.append(filename)
					except IndexError:
						pass
			self._search(node)
		
		
