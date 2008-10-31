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
snippets.completion

Snippet-specific completion classes
"""

from logging import getLogger
from gtk import gdk

from ..base import ICompletionHandler, IProposal, Template
from ..base.resources import find_resource


class SnippetProposal(IProposal):
	
	icon = gdk.pixbuf_new_from_file(find_resource("icons/snippet.png"))
	
	def __init__(self, snippet, overlap):
		self._snippet = snippet
		self._overlap = overlap
	
	@property
	def source(self):
		"""
		@return: a subclass of Source to be inserted on activation
		"""
		return Template(self._snippet.template_expression)
	
	@property
	def label(self):
		"""
		@return: a string (may be pango markup) to be shown in proposals popup
		"""
		return self._snippet.label
	
	@property
	def details(self):
		"""
		@return: a widget to be shown in details popup
		"""
		self._snippet.template_expression
	
	@property
	def overlap(self):
		"""
		@return: the number of overlapping characters from the beginning of the
			proposal and the prefix it was generated for
		"""
		return self._overlap


#from . import Snippet
#
#
#SNIPPETS = [
#		Snippet("includegraphics", "\\includegraphics[${Attributes}]{${Filename}}"),
#		Snippet("begin", "\\begin{${Environment}}\n\t$_\n\\end{${Environment}}") ]

from ..preferences import Preferences


class SnippetCompletionHandler(ICompletionHandler):
	"""
	"""
	
	_log = getLogger("SnippetCompletionHandler")
	
	def __init__(self):
		self._snippets = Preferences().snippets
	
	@property
	def trigger_keys(self):
		return []
	
	@property
	def prefix_delimiters(self):
		return ["\t", "\n", " "]
	
	@property
	def strip_delimiter(self):
		return True
	
	def complete(self, prefix):
		self._log.debug("complete(%s)" % prefix)
		
		overlap = len(prefix)
		
		matching_snippets = [snippet for snippet in self._snippets if snippet.label.startswith(prefix)]
		proposals = [SnippetProposal(snippet, overlap) for snippet in matching_snippets]
		
		return proposals
	
	