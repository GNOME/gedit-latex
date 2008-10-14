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
base

These classes form the interface exposed by the plugin base layer.
"""

from logging import getLogger
import gtk


class View(gtk.VBox):
	"""
	Base class for a view
	"""
	
	# TODO: call destroy()
	
	POSITION_SIDE, POSITION_BOTTOM = 0, 1
	
	SCOPE_WINDOW, SCOPE_EDITOR = 0, 1
	
	#
	# these should be overriden by subclasses
	#
	
	# a label string used for this view
	label = ""
	
	# an icon for this view (gtk.Image or a stock_id string)
	icon = None
	
	# position: POSITION_SIDE | POSITION_BOTTOM
	position = POSITION_SIDE
	
	# the scope of this View:
	# 	SCOPE_WINDOW: the View is created with the window and the same instance is passed to every Editor
	#	SCOPE_EDITOR: the View is created with the Editor and destroyed with it
	scope = SCOPE_WINDOW
	
	
	def __init__(self, context):
		gtk.VBox.__init__(self)
		
		self._context = context
		self._initialized = False
		
		# connect to expose event and init() on first expose
		self._expose_handler = self.connect("expose-event", self._on_expose_event)
		
	def _on_expose_event(self, *args):
		"""
		The View has been exposed for the first time
		"""
		self._do_init()
	
	def _do_init(self):
		self.disconnect(self._expose_handler)
		self.init(self._context)
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
	
	def init(self, context):
		"""
		To be overridden
		"""
	
	def destroy(self):
		"""
		To be overridden
		"""
		

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
from uuid import uuid1

from .completion import CompletionDistributor
from .templates import TemplateDelegate
from util import RangeMap


class Editor(object):
	"""
	"""
	
	__log = getLogger("Editor")
	
	
	class Marker(object):
		"""
		Markers refer to and highlight a range of text in the TextBuffer decorated by 
		an Editor. They are used for spell checking and highlighting issues.
		
		Each Marker instance stores two gtk.TextMark objects refering to the start and
		end of the text range.
		"""
		def __init__(self, left_mark, right_mark, id, type):
			"""
			@param left_mark: a gtk.TextMark
			@param right_mark: a gtk.TextMark
			@param id: a unique string
			@param type: a marker type string
			"""
			self.left_mark = left_mark
			self.right_mark = right_mark
			self.type = type
			self.id = id
	
	
	class MarkerTypeRecord(object):
		"""
		This used for managing Marker types
		"""
		def __init__(self, tag, anonymous):
			"""
			@param tag: a gtk.TextTag
			"""
			self.tag = tag
			self.anonymous = anonymous
			self.markers = []
	
	
	__PATTERN_INDENT = re.compile("[ \t]+")
	
	
	# A list of file extensions
	#
	# If one or more files with one of these extensions is dragged and dropped on the editor,
	# the Editor.drag_drop_received method is called. An empty list disables the dnd support.
	dnd_extensions = []
	
	
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
		
		#
		# init marker framework
		#
		
		# needed for cleanup
		self._marker_types = {}    # {marker type -> MarkerTypeRecord object}
		self._markers = {}		# { marker id -> marker object }
		
		
		# TODO: pass window_context to Editor?
		
		self._window_context = self._tab_decorator._window_decorator._window_context
		self._window_context.create_editor_views(self, file)
		
		
		self._offset = None

		# TODO: disconnect on destroy
		self._button_press_handler = self._text_view.connect("button-press-event", self.__on_button_pressed)
		self._text_view.connect("key-release-event", self.__on_key_released)
		self._text_view.connect("button-release-event", self.__on_button_released)
		
		# dnd support
		if len(self.dnd_extensions) > 0:
			self._text_view.connect("drag-data-received", self.__on_drag_data_received)
		
		# start life-cycle for subclass
		self.init(file, self._window_context)
	
	def __on_drag_data_received(self, widget, context, x, y, data, info, timestamp):
		"""
		The drag destination received the data from the drag operation
		
		@param widget: the widget that received the signal
		@param context: the gtk.gdk.DragContext
		@param x: the X position of the drop
		@param y: the Y position of the drop
		@param data: a gtk.SelectionData object
		@param info: an integer ID for the drag
		@param timestamp: the time of the drag event
		"""
		self.__log.debug("drag-data-received")
		
		files = []
		match = False
		
		for uri in data.get_uris():
			file = File(uri)
			files.append(file)
			if file.extension.lower() in self.dnd_extensions:
				match = True
		
		if match:
			self.drag_drop_received(files)

	def drag_drop_received(self, files):
		"""
		To be overridden
		
		@param files: a list of File objects dropped on the Editor
		"""
		pass

	def __on_key_released(self, *args):
		"""
		This helps to call 'move_cursor'
		"""
		offset = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert()).get_offset()
		if offset != self._offset:
			self._offset = offset
			self.on_cursor_moved(offset)
	
	def __on_button_released(self, *args):
		"""
		This helps to call 'move_cursor'
		"""
		offset = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert()).get_offset()
		if offset != self._offset:
			self._offset = offset
			self.on_cursor_moved(offset)
	
	def __on_button_pressed(self, text_view, event):
		"""
		Mouse button has been pressed on the TextView
		"""
		if event.button == 3:	# right button
			x, y = text_view.get_pointer()
			x, y = text_view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, x, y)
			it = text_view.get_iter_at_location(x, y)
			
			self.__log.debug("Right button pressed at offset %s" % it.get_offset())
			
			#
			# find Marker at this position
			#
			while True:
				for mark in it.get_marks():
					name = mark.get_name()
					
					self.__log.debug("Found TextMark '%s' at offset %s" % (name, it.get_offset()))
					
					if name:
						try:
							marker = self._markers[name]
							self.on_marker_activated(marker, event)
							return
						except KeyError:
							self.__log.warning("No marker found for TextMark '%s'" % name)
					else:
						# FIXME: this is not safe - use another symbol for right boundaries!
						self.__log.debug("Unnamed TextMark found, outside of any Markers")
						return
				
				# move left by one char and continue 
				if not it.backward_char():
					# start of buffer reached
					return
	
	@property
	def file(self):
		return self._file
	
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
	def charset(self):
		"""
		Return the character set used by this Editor
		"""
		return self._text_buffer.get_encoding().get_charset()
	
	@property
	def content(self):
		"""
		Return the string contained in the TextBuffer
		"""
		return self._text_buffer.get_text(self._text_buffer.get_start_iter(), 
									self._text_buffer.get_end_iter(), False).decode(self.charset)
	
	def content_changed(self, reference_timestamp):
		"""
		Return True if the content of this Editor has changed since a given
		reference
		"""
		# TODO:
	
	def insert(self, source):
		"""
		This may be overridden to catch special types like LaTeXSource
		"""
		self.__log.debug("insert(%s)" % source)
		
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
		
		match = self.__PATTERN_INDENT.match(string)
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
	
	def select(self, start_offset, end_offset):
		"""
		Select a range of text and scroll the view to the right position
		"""
		it_start = self._text_buffer.get_iter_at_offset(start_offset)
		it_end = self._text_buffer.get_iter_at_offset(end_offset)
		self._text_buffer.select_range(it_start, it_end)
		self._text_view.scroll_to_iter(it_start, .25)
	
	#
	# markers are used for spell checking (identified) and highlighting (anonymous)
	#
	
	def register_marker_type(self, marker_type, background_color, anonymous=True):
		"""
		@param marker_type: a string
		@param background_color: a hex color
		@param anonymous: markers of an anonymous type may not be activated and do not get a unique ID
		"""
		assert not marker_type in self._marker_types.keys()
		
		# create gtk.TextTag
		tag = self._text_buffer.create_tag(marker_type, background=background_color)
		
		# create a MarkerTypeRecord for this type
		self._marker_types[marker_type] = self.MarkerTypeRecord(tag, anonymous)
	
	def create_marker(self, marker_type, start_offset, end_offset):
		"""
		Mark a section of the text
		
		@param marker_type: type string
		@return: a Marker object if the type is not anonymous or None otherwise
		"""
		
		# check offsets
		if start_offset < 0:
			self.__log.error("create_marker(): start offset out of range (%s < 0)" % start_offset)
			return
		
		buffer_end_offset = self._text_buffer.get_end_iter().get_offset()
		
		if end_offset > buffer_end_offset:
			self.__log.error("create_marker(): end offset out of range (%s > %s)" % (end_offset, buffer_end_offset))
		
		
		type_record = self._marker_types[marker_type]
		
		# hightlight
		left = self._text_buffer.get_iter_at_offset(start_offset)
		right = self._text_buffer.get_iter_at_offset(end_offset)
		self._text_buffer.apply_tag_by_name(marker_type, left, right)
		
		if type_record.anonymous:
			# create TextMarks
			left_mark = self._text_buffer.create_mark(None, left, True)
			right_mark = self._text_buffer.create_mark(None, right, False)
			
			# create Marker object
			marker = self.Marker(left_mark, right_mark, None, marker_type)
			
			# store Marker
			type_record.markers.append(marker)
			
			return None
		else:
			# create unique marker id
			id = str(uuid1())
			
			# create Marker object and put into map
			left_mark = self._text_buffer.create_mark(id, left, True)
			right_mark = self._text_buffer.create_mark(None, right, False)
			marker = self.Marker(left_mark, right_mark, id, marker_type)
		
			# store Marker
			self._markers[id] = marker
			type_record.markers.append(marker)
			
			return marker
	
	def remove_marker(self, marker):
		"""
		@param marker: the Marker object to remove
		"""
		# create TextIters from TextMarks
		left_iter = self._text_buffer.get_iter_at_mark(marker.left_mark)
		right_iter = self._text_buffer.get_iter_at_mark(marker.right_mark)
		
		# remove TextTag
		type_record = self._marker_types[marker.type]
		self._text_buffer.remove_tag(type_record.tag, left_iter, right_iter)
		
		# remove TextMarks
		self._text_buffer.delete_mark(marker.left_mark)
		self._text_buffer.delete_mark(marker.right_mark)
		
		# remove Marker from MarkerTypeRecord
		i = type_record.markers.index(marker)
		del type_record.markers[i]
		
		# remove from id map
		del self._markers[marker.id]
	
	def remove_markers(self, marker_type):
		"""
		Remove all markers of a certain type
		"""
		type_record = self._marker_types[marker_type]
		
		for marker in type_record.markers:
			assert not marker.left_mark.get_deleted()
			assert not marker.right_mark.get_deleted()
			
			# create TextIters from TextMarks
			left_iter = self._text_buffer.get_iter_at_mark(marker.left_mark)
			right_iter = self._text_buffer.get_iter_at_mark(marker.right_mark)
			
			# remove TextTag
			self._text_buffer.remove_tag(type_record.tag, left_iter, right_iter)
			
			# remove TextMarks
			self._text_buffer.delete_mark(marker.left_mark)
			self._text_buffer.delete_mark(marker.right_mark)
			
			if not type_record.anonymous:
				# remove Marker from id map
				del self._markers[marker.id]
		
		# remove markers from MarkerTypeRecord
		type_record.markers = []
	
	def replace_marker_content(self, marker, content):
		# get TextIters
		left = self._text_buffer.get_iter_at_mark(marker.left_mark)
		right = self._text_buffer.get_iter_at_mark(marker.right_mark)
		
		# replace
		self._text_buffer.delete(left, right)
		left = self._text_buffer.get_iter_at_mark(marker.left_mark)
		self._text_buffer.insert(left, content)
		
		# remove Marker
		self.remove_marker(marker)
	
	def on_marker_activated(self, marker, event):
		"""
		A marker has been activated
		
		To be overridden
		
		@param id: id of the activated marker
		@param event: the GdkEvent of the mouse click (for raising context menus)
		"""
	
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
	
	def on_save(self):
		"""
		The file has been saved to its original location
		"""
	
	def on_cursor_moved(self, offset):
		"""
		The cursor has moved
		"""
	
	def destroy(self):
		"""
		The edited file has been closed or saved as another file
		"""
		self.__log.debug("destroy")
		
		self._template_delegate.destroy()


class WindowContext(object):
	"""
	The WindowContext is passed to Editors and is used to 
	 * retrieve View instances
	 * activate a specific Editor instance
	 * retrieve the currently active Editor
	
	This also creates and destroys the View instances.
	"""
	
	_log = getLogger("WindowContext")
	
	def __init__(self, window_decorator, editor_scope_view_classes):
		"""
		@param window_decorator: the GeditWindowDecorator this context corresponds to
		@param editor_scope_view_classes: a map from extension to list of View classes
		"""
		self._window_decorator = window_decorator
		self._editor_scope_view_classes = editor_scope_view_classes
		self._window_scope_views = {}	# maps view ids to View objects
		self._editor_scope_views = {}	# maps Editor object to a map from ID to View object
		
		self._log.debug("init")
	
	def create_editor_views(self, editor, file):
		"""
		Create instances of the editor specific Views for a given Editor instance
		and File
		
		Called Editor base class
		"""
		self._editor_scope_views[editor] = {}
		try:
			for id, clazz in self._editor_scope_view_classes[file.extension].iteritems():
				# create View instance and add it to the map
				view = clazz.__new__(clazz)
				clazz.__init__(view, self)
				self._editor_scope_views[editor][id] = view
				
				self._log.debug("Created view " + id)
		except KeyError:
			self._log.debug("No views for %s" % file.extension)
	
	def set_window_views(self, views):
		"""
		
		Called by GeditWindowDecorator
		"""
		self._window_scope_views = views
	
	def get_editor_views(self, editor):
		"""
		Return a map of all editor scope views
		"""
		return self._editor_scope_views[editor]
	
	###
	# public interface
	
	@property
	def active_editor(self):
		"""
		Return the active Editor instance
		"""
		return self._window_decorator._active_tab_decorator.editor
	
	def activate_editor(self, file):
		"""
		Activate the Editor containing a given File or open a new tab for it
		
		@param file: a File object
		
		@raise AssertError: if the file is no File object
		"""
		assert type(file) is File
		
		self._window_decorator.activate_tab(file)
	
	def find_view(self, editor, view_id):
		"""
		Return a View object
		"""
		try:
			return self._editor_scope_views[editor][view_id]
		except KeyError:
			return self._window_scope_views[view_id]
	
	def set_action_enabled(self, action_id, enabled):
		"""
		Enable/disable an IAction object
		"""
		self._window_decorator._action_group.get_action(action_id).set_sensitive(enabled)
	

from urlparse import urlparse
from os.path import splitext, basename, dirname, exists, getmtime
from glob import glob


class File(object):
	"""
	Abstracts from filename
	"""
	
	__log = getLogger("File")
	
	_DEFAULT_SCHEME = "file://"
	
	def __init__(self, uri):
		"""
		@param uri: any URI, URL or local filename
		"""
		self._uri = urlparse(uri)
		if len(self._uri.scheme) == 0:
			self._uri = urlparse("%s%s" % (self._DEFAULT_SCHEME, uri))
	
	@property
	def path(self):
		"""
		Returns '/home/user/image.jpg' for 'file:///home/user/image.jpg'
		"""
		return self._uri.path
	
	@property
	def extension(self):
		"""
		Returns 'jpg' for 'file:///home/user/image.jpg'
		"""
		return splitext(self.path)[1]
	
	@property
	def shortname(self):
		"""
		Returns '/home/user/image' for 'file:///home/user/image.jpg'
		"""
		return splitext(self.path)[0]
	
	@property
	def basename(self):
		"""
		Returns 'image.jpg' for 'file:///home/user/image.jpg'
		"""
		return basename(self.path)
	
	@property
	def shortbasename(self):
		"""
		Returns 'image' for 'file:///home/user/image.jpg'
		"""
		return splitext(basename(self.path))[0]
	
	@property
	def dirname(self):
		"""
		Returns '/home/user' for 'file:///home/user/image.jpg'
		"""
		return dirname(self.path)
	
	@property
	def uri(self):
		return self._uri.geturl()
	
	@property
	def exists(self):
		return exists(self.path)
	
	@property
	def mtime(self):
		return getmtime(self.path)
	
	def find_neighbors(self, extension):
		"""
		Find other files in the directory of this one having
		a certain extension
		
		@param extension: a file extension like '.tex'
		"""
		
		# TODO: glob is quite expensive, find a simpler way for this
		
		try:
			filenames = glob("%s/*%s" % (self.dirname, extension))
			neighbors = [File(filename) for filename in filenames]
			return neighbors
		
		except Exception, e:
			# as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
			# for an exception from that because self.baseDir may contain regex characters
			
			# TODO: a more robust solution would be an escape() method for re
			
			self.__log.debug("find_neighbors: %s" % e)
			
			return []
	
	def __eq__(self, file):
		"""
		Override equality operator
		"""
		return self.uri == file.uri
	
	def __str__(self):
		return self.uri

