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
base.interface

These classes form the interface exposed by the plugin base
"""

from logging import getLogger


class Template(object):
	"""
	This one is exposed and should be used by the 'real' plugin code
	"""
	def __init__(self, expression):
		self._expression = expression
	
	@property
	def expression(self):
		return self._expression


class IAction(object):
	"""
	"""
	
	@property
	def label(self):
		raise NotImplementedError
	
	@property
	def stock_id(self):
		raise NotImplementedError
	
	@property
	def accelerator(self):
		raise NotImplementedError
	
	@property
	def tooltip(self):
		raise NotImplementedError

	def activate(self, editor):
		raise NotImplementedError


class ICompletionHandler(object):
	"""
	This should be implemented for each language or 'proposal source'
	"""
	@property
	def trigger_keys(self):
		"""
		@return: a list of gdk key codes that trigger completion
		"""
		raise NotImplementedError
	
	@property
	def prefix_delimiters(self):
		"""
		@return: a list of characters that delimit the prefix on the left
		"""
		raise NotImplementedError
	
	@property
	def strip_delimiter(self):
		"""
		@return: return whether to cut off the delimiter from the prefix
		or not
		"""
		raise NotImplementedError
	
	def complete(self, prefix):
		"""
		@return: a list of objects implementing IProposal
		"""
		raise NotImplementedError


class IProposal(object):
	"""
	A proposal for completion
	"""
	@property
	def source(self):
		"""
		@return: a subclass of Source to be inserted on activation
		"""
		raise NotImplementedError
	
	@property
	def label(self):
		"""
		@return: a string (may be pango markup) to be shown in proposals popup
		"""
		raise NotImplementedError
	
	@property
	def details(self):
		"""
		@return: a widget to be shown in details popup
		"""
		raise NotImplementedError
	
	@property
	def icon(self):
		"""
		@return: an instance of gtk.gdk.Pixbuf
		"""
		raise NotImplementedError
	
	@property
	def overlap(self):
		"""
		@return: the number of overlapping characters from the beginning of the
			proposal and the prefix it was generated for
		"""
		raise NotImplementedError


import re

from .completion import CompletionDistributor
from .templates import TemplateDelegate


class Editor(object):
	
	__log = getLogger("Editor")
	
	_PATTERN_INDENT = re.compile("[ \t]+")
	
	def __init__(self, tab_decorator, file):
		self._tab_decorator = tab_decorator
		self._file = file
		self._text_buffer = tab_decorator.tab.get_document()
		self._text_view = tab_decorator.tab.get_view()
		
		# template delegate
		self._template_delegate = TemplateDelegate(self)
		
		# hook completion handlers
		completion_handlers = self.completion_handlers
		if len(completion_handlers):
			self._completion_distributor = CompletionDistributor(self, completion_handlers)
		else:
			self._completion_distributor = None
		
		# start life-cycle for subclass
		self.init(file)
	
	@property
	def tab_decorator(self):
		return self._tab_decorator
	
	def delete_at_cursor(self, offset):
		"""
		Delete characters relative to the cursor position:
		
		offset < 0		delete characters from offset to cursor
		offset > 0		delete characters from cursor to offset
		"""
		start = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
		end = self._text_buffer.get_iter_at_offset(start.get_offset() + offset)
		self._text_buffer.delete(start, end)
	
	# methods/properties to be used/overridden by the subclass
	
	@property
	def contents(self):
		"""
		Return the string contained in the TextBuffer
		"""
		charset = self._text_buffer.get_encoding().get_charset()
		return self._text_buffer.get_text(self._text_buffer.get_start_iter(), 
									self._text_buffer.get_end_iter(), False).decode(charset)
	
	def insert(self, source):
		"""
		This may be overridden to catch special types like LaTeXSource
		"""
		self.__log.debug("insert_source(%s)" % source)
		
		if type(source) is Template:
			self._template_delegate.insert(source)
		else:
			self._text_buffer.insert_at_cursor(str(source))
	
	@property
	def indentation(self):
		"""
		Return the indentation string of the line at the cursor
		"""
		i_start = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
		i_start.set_line_offset(0)
		
		i_end = i_start.copy()
		i_end.forward_to_line_end()
		string = self._text_buffer.get_text(i_start, i_end)
		
		match = self._PATTERN_INDENT.match(string)
		if match:
			return match.group()
		else:
			return ""
	
	@property
	def completion_handlers(self):
		"""
		To be overridden
		
		@return: a list of objects implementing CompletionHandler
		"""
		return []
	
	def init(self, file):
		"""
		@param file: File object
		"""
	
	def save(self):
		"""
		The file has been saved to its original location
		"""
	
	def destroy(self):
		"""
		The edited file has been closed or saved as another file
		"""
		
		