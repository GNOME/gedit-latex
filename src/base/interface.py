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
import gtk


class View(gtk.HBox):
	"""
	A view
	"""
	
	POSITION_SIDE, POSITION_BOTTOM = 0, 1
	
	SCOPE_WINDOW, SCOPE_EDITOR = 0, 1
	
	
	def __init__(self):
		gtk.HBox.__init__(self)
		
		self._initialized = False
		
		# connect to expose event to init() on first expose
		self._expose_handler = self.connect("expose-event", self._on_expose_event)
		
	def _on_expose_event(self, *args):
		"""
		The View has been exposed for the first time
		"""
		self._do_init()
	
	def _do_init(self):
		self.disconnect(self._expose_handler)
		self.init()
		self.show_all()
		self._initialized = True
	
	def assure_init(self):
		"""
		This may be called by the subclassing instance to assure that the View
		has been initialized. 
		
		This is necessary because methods of the instance may be called before 
		init() as the View is initialized on the first exposure.
		"""
		if not self._initialized:
			self._do_init()
	
	def init(self):
		"""
		To be overridden
		"""

	@property
	def position(self):
		"""
		To be overridden
		
		@return: POSITION_SIDE | POSITION_BOTTOM
		"""
		return self.POSITION_SIDE
	
	@property
	def label(self):
		"""
		To be overridden
		
		@return: a label string used for this view
		"""
		return ""
	
	@property
	def icon(self):
		"""
		To be overridden
		
		@return: an icon for this view (gtk.Image or a stock_id string)
		"""
		return None
	
	@property
	def scope(self):
		"""
		To be overridden
		
		@return: the scope of this View:
			SCOPE_WINDOW: the View is created with the window and the same instance is passed to every Editor
			SCOPE_EDITOR: the View is created with the Editor and destroyed with it
		"""
		return self.SCOPE_WINDOW
	


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

	def activate(self, context):
		"""
		@param context: the current WindowContext instance
		"""
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
from util import RangeMap
from . import Marker


from ..latex.views import LaTeXConsistencyView


EDITOR_SCOPE_VIEWS = { ".tex" : {"LaTeXConsistencyView" : LaTeXConsistencyView } }


class Editor(object):
	
	__log = getLogger("Editor")
	
	_PATTERN_INDENT = re.compile("[ \t]+")
	
	def __init__(self, tab_decorator, file):
		self._tab_decorator = tab_decorator
		self._file = file
		self._text_buffer = tab_decorator.tab.get_document()
		self._text_view = tab_decorator.tab.get_view()
		
		# create template delegate
		self._template_delegate = TemplateDelegate(self)
		
		# hook completion handlers of the subclassing Editor
		completion_handlers = self.completion_handlers
		if len(completion_handlers):
			self._completion_distributor = CompletionDistributor(self, completion_handlers)
		else:
			self._completion_distributor = None
		
		# init marker framework
		self._marker_type_tags = {}    # marker type id -> TextTag object
		self._marker_maps = {}	   	   # marker type id -> RangeMap object
		
		
		# create editor-specific views
		self._views = {}
		try:
			for id, clazz in EDITOR_SCOPE_VIEWS[file.extension].iteritems():
				# create View instance and add it to the map
				view = clazz.__new__(clazz)
				clazz.__init__(view)
				self._views[id] = view
				
				self.__log.debug("Created view " + id)
		except KeyError:
			self.__log.debug("No views")
		
		
		# create context object
		context = WindowContext()
		context.views = self._views
		
		
		# TODO: disconnect on destroy
		self._button_press_handler = self._text_view.connect("button-press-event", self._on_button_pressed)
		
		# start life-cycle for subclass
		self.init(file, context)
	
	@property
	def file(self):
		return self._file
	
	@property
	def views(self):
		return self._views
	
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
	
	def toggle_comment(self, delimiter):
		"""
		Enable/disable the line comment of the current line or the selection.
		
		@param delimiter: The comment delimiter (for LaTeX this is "%")
		"""
		
		# TODO: generalize this, for now we ignore the delimiter
		
		bounds = self._text_buffer.get_selection_bounds()
		
		if bounds:
			startIt, endIt = bounds
			
			# first run: check current comment state
			#
			# We propose that EVERY line is commented and loop through
			# the lines to verify that.
			# Thus we may abort at the first line that is NOT commented.
			
			selectionCommented = True
			
			tmpIt = startIt.copy()
			tmpIt.set_line_offset(0)
			
			while tmpIt.compare(endIt) < 0:
				
				# walk through the line: skip spaces and tabs and abort at "%"
				lineCommented = True
				
				while True:
					c = tmpIt.get_char()
					if c == "%" or c == "\n":
						break
					elif c == " " or c == "\t":
						tmpIt.forward_char()
					else:
						lineCommented = False
						break
				
				if lineCommented:
					tmpIt.forward_line()
				else:
					selectionCommented = False
					break
			
			
			# second run: (un)comment selected 
			
			tmpIt = startIt.copy()
			tmpIt.set_line_offset(0)
			
			while tmpIt.compare(endIt) < 0:
				
				# we must use marks here because iterators are invalidated on buffer changes
				tmpMark = self._text_buffer.create_mark(None, tmpIt, True)
				endMark = self._text_buffer.create_mark(None, endIt, True)
				
				if selectionCommented:
					# uncomment
					
					# walk through the line to find "%" character and delete it
					while True:
						c = tmpIt.get_char()
						if c == "%":
							delIt = tmpIt.copy()
							delIt.forward_char()
							self._text_buffer.delete(tmpIt, delIt)
							break
						elif c == "\n":
							# empty line, skip it
							break
				
				else:
					# comment
					self._text_buffer.insert(tmpIt, "%")
				
				# restore iterators from marks and delete the marks
				tmpIt = self._text_buffer.get_iter_at_mark(tmpMark)
				endIt = self._text_buffer.get_iter_at_mark(endMark)
				
				self._text_buffer.delete_mark(tmpMark)
				self._text_buffer.delete_mark(endMark)
				
				# go to next line
				tmpIt.forward_line()
				
		else:
			# no selection, process the current line, no second run needed
			
			tmpIt = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
			tmpIt.set_line_offset(0)
			
			# get comment status
			lineCommented = True
				
			while True:
				c = tmpIt.get_char()
				if c == "%" or c == "\n":
					break
				elif c == " " or c == "\t":
					tmpIt.forward_char()
				else:
					lineCommented = False
					break
			
			tmpIt.set_line_offset(0)
			
			# toggle
			if lineCommented:
				# uncomment
				
				# walk through the line to find "%" character and delete it
				while True:
					c = tmpIt.get_char()
					if c == "%":
						delIt = tmpIt.copy()
						delIt.forward_char()
						self._text_buffer.delete(tmpIt, delIt)
						break
					elif c == "\n":
						# empty line, skip it
						break
			
			else:
				# comment
				self._text_buffer.insert(tmpIt, "%")
	
	#
	# markers are used for spell checking
	#
	
	def register_marker_type(self, marker_type, background_color):
		"""
		@param marker_type: a string
		@param background_color: a hex color
		"""
		assert not marker_type in self._marker_type_tags.keys()
		
		# add tag
		self._marker_type_tags[marker_type] = self._text_buffer.create_tag(marker_type, 
										background=background_color)
		# create map
		self._marker_maps[marker_type] = RangeMap()
	
	def create_marker(self, marker_type, start_offset, end_offset):
		"""
		Mark a section of the text
		
		@return: a Marker object
		"""
		assert marker_type in self._marker_type_tags.keys()
		
		# hightlight
		left = self._text_buffer.get_iter_at_offset(start_offset)
		right = self._text_buffer.get_iter_at_offset(end_offset)
		self._text_buffer.apply_tag_by_name(marker_type, left, right)
		
		# create Marker object and put into map
		left_mark = self._text_buffer.create_mark(None, left, True)
		right_mark = self._text_buffer.create_mark(None, right, False)
		marker = Marker(left_mark, right_mark)
		
		self._marker_maps[marker_type].put(start_offset, end_offset, marker)
	
	def remove_marker(self, marker):
		"""
		@param id: the id of the marker to remove
		"""
		
	
	def remove_markers(self, marker_type):
		"""
		Remove all markers of a type
		"""
		assert marker_type in self._marker_type_tags.keys()
		
		self._text_buffer.remove_tag_by_name(marker_type, self._text_buffer.get_start_iter(), 
									self._text_buffer.get_end_iter())
	
	def replace_marker_content(self, marker, content):
		# get TextIters
		left = self._text_buffer.get_iter_at_mark(marker.left_mark)
		right = self._text_buffer.get_iter_at_mark(marker.right_mark)
		
		# replace
		self._text_buffer.delete(left, right)
		left = self._text_buffer.get_iter_at_mark(marker.left_mark)
		self._text_buffer.insert(left, content)
		
		# cleanup
		self._text_buffer.delete_mark(marker.left_mark)
		self._text_buffer.delete_mark(marker.right_mark)
	
	def _on_button_pressed(self, text_view, event):
		"""
		Mouse button has been pressed on the TextView
		"""
		if event.button == 3:	# right button
			x, y = text_view.get_pointer()
			x, y = text_view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, x, y)
			it = text_view.get_iter_at_location(x, y)
			offset = it.get_offset()
			
			for map in self._marker_maps.itervalues():
				for marker in map.lookup(offset):
					self.activate_marker(marker, event)
	
	def activate_marker(self, marker, event):
		"""
		A marker has been activated
		
		To be overridden
		
		@param id: id of the activated marker
		@param event: the event of the mouse click (for raising context menus)
		"""
		pass
	
	
	
	@property
	def completion_handlers(self):
		"""
		To be overridden
		
		@return: a list of objects implementing CompletionHandler
		"""
		return []
	
	def init(self, file, context):
		"""
		@param file: File object
		@param context: WindowContext object
		"""
	
	def save(self):
		"""
		The file has been saved to its original location
		"""
	
	def destroy(self):
		"""
		The edited file has been closed or saved as another file
		"""
		
	
class WindowContext(object):
	"""
	The WindowContext is passed to Editors and is used to retrieve View instances. We could 
	pass the map of views directly but a Context is more generic and may be used for more
	things in the future.
	"""
	def __init__(self):
		self.views = {}
		self.active_editor = None
	
	
