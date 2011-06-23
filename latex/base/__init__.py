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
base

These classes form the interface exposed by the plugin base layer.
"""

from logging import getLogger
from gi.repository import Gtk, Gdk


class View(object):
	"""
	Base class for a view
	"""
	
	_log = getLogger("View")
	
	# TODO: this doesn't belong to the interface of base
	# TODO: call destroy()
	
	SCOPE_WINDOW, SCOPE_EDITOR = 0, 1
	
	#
	# these should be overriden by subclasses
	#
	
	# a label string used for this view
	label = ""
	
	# an icon for this view (Gtk.Image or a stock_id string)
	icon = None
	
	# the scope of this View:
	# 	SCOPE_WINDOW: the View is created with the window and the same instance is passed to every Editor
	#	SCOPE_EDITOR: the View is created with the Editor and destroyed with it
	scope = SCOPE_WINDOW
	
	def init(self, context):
		"""
		To be overridden
		"""
	
	def destroy(self):
		"""
		To be overridden
		"""
		
	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)


class SideView(View, Gtk.VBox):
	"""
	"""
	def __init__(self, context):
		GObject.GObject.__init__(self)
		
		self._context = context
		self._initialized = False
		
		# connect to expose event and init() on first expose
		self._expose_handler = self.connect("draw", self._on_expose_event)
		
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
			
	def destroy(self):
		if not self._initialized:
			self.disconnect(self._expose_handler)
		Gtk.VBox.destroy(self)
		self._context = None


class BottomView(View, Gtk.HBox):
	"""
	"""
	def __init__(self, context):
		GObject.GObject.__init__(self)
		
		self._context = context
		self._initialized = False
		
		# connect to expose event and init() on first expose
		self._expose_handler = self.connect("draw", self._on_expose_event)
		
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
			
	def destroy(self):
		if not self._initialized:
			self.disconnect(self._expose_handler)
		Gtk.HBox.destroy(self)
		self._context = None



class Template(object):
	"""
	This one is exposed and should be used by the 'real' plugin code
	"""
	def __init__(self, expression):
		self._expression = expression
	
	@property
	def expression(self):
		return self._expression
	
	def __str__(self):
		return self._expression


from gi.repository import GObject

#
# workaround for MenuToolItem
# see http://library.gnome.org/devel/pygtk/stable/class-gtkaction.html#method-gtkaction--set-tool-item-type
#
# we prepend the plugin name to be sure that it's a unique symbol
# see https://sourceforge.net/tracker/index.php?func=detail&aid=2599705&group_id=204144&atid=988428
#
class GeditLaTeXPlugin_MenuToolAction(Gtk.Action):
	__gtype_name__ = "GeditLaTeXPlugin_MenuToolAction"

#GObject.type_register(GeditLaTeXPlugin_MenuToolAction)
# needs PyGTK 2.10
#GeditLaTeXPlugin_MenuToolAction.set_tool_item_type(Gtk.MenuToolButton)


class Action(object):
	"""
	"""
	
	menu_tool_action = False	# if True a MenuToolAction is created and hooked for this action
								# instead of Gtk.Action
								
	extensions = [None]			# a list of file extensions for which this action should be enabled
								# [None] indicates that this action is to be enabled for all extensions
	
	def hook(self, action_group, window_context):
		"""
		Create an internal action object (Gtk.Action or MenuToolAction), listen to it and
		hook it in an action group
		
		@param action_group: a Gtk.ActionGroup object
		@param window_context: a WindowContext object to pass when this action is activated
		"""
		if self.menu_tool_action:
			action_clazz = GeditLaTeXPlugin_MenuToolAction
		else:
			action_clazz = Gtk.Action
		self._internal_action = action_clazz(self.__class__.__name__, self.label, self.tooltip, self.stock_id)
		self._handler = self._internal_action.connect("activate", lambda gtk_action, action: action.activate(window_context), self)
		action_group.add_action_with_accel(self._internal_action, self.accelerator)
		
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

	def unhook(self, action_group):
		self._internal_action.disconnect(self._handler)
		action_group.remove_action(self._internal_action)
		
	#~ def __del__(self):
		#~ print "Properly destroyed Action %s" % self


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
	
	def complete(self, prefix):
		"""
		@return: a list of objects extending Proposal
		"""
		raise NotImplementedError


class Proposal(object):
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
		@return: an instance of GdkPixbuf.Pixbuf
		"""
		raise NotImplementedError
	
	@property
	def overlap(self):
		"""
		@return: the number of overlapping characters from the beginning of the
			proposal and the prefix it was generated for
		"""
		raise NotImplementedError
	
	def __cmp__(self, other):
		"""
		Compare this proposal to another one
		"""
		return cmp(self.label.lower(), other.label.lower())


import re
from uuid import uuid1
import time

from .completion import CompletionDistributor
from .templates import TemplateDelegate


class Editor(object):
	"""
	The base class for editors. This manages
	 - the subclass life-cycle
	 - the marker framework
	 - change monitoring
	 - drag'n'drop support
	"""
	
	__log = getLogger("Editor")
	
	
	class Marker(object):
		"""
		Markers refer to and highlight a range of text in the TextBuffer decorated by 
		an Editor. They are used for highlighting issues.
		
		Each Marker instance stores two Gtk.TextMark objects refering to the start and
		end of the text range.
		"""
		def __init__(self, left_mark, right_mark, id, type):
			"""
			@param left_mark: a Gtk.TextMark
			@param right_mark: a Gtk.TextMark
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
			@param tag: a Gtk.TextTag
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
		self._tags = []
		self._marker_types = {}    # {marker type -> MarkerTypeRecord object}
		self._markers = {}		# { marker id -> marker object }
		
		
		self._window_context = self._tab_decorator._window_decorator._window_context
		self._window_context.create_editor_views(self, file)
		
		
		self._offset = None		# used by move_cursor

		self.__view_signal_handlers = [
				self._text_view.connect("button-press-event", self.__on_button_pressed),
				self._text_view.connect("key-release-event", self.__on_key_released),
				self._text_view.connect("button-release-event", self.__on_button_released) ]
		
		self.__buffer_change_timestamp = time.time()
		self.__buffer_signal_handlers = [
				self._text_buffer.connect("changed", self.__on_buffer_changed) ]
		
		# dnd support
		if len(self.dnd_extensions) > 0:
			self.__view_signal_handlers.append(
					self._text_view.connect("drag-data-received", self.__on_drag_data_received))
		
		# start life-cycle for subclass
		self.init(file, self._window_context)
		
	def __on_buffer_changed(self, text_buffer):
		"""
		Store the timestamp of the last buffer change
		"""
		self.__buffer_change_timestamp = time.time()
	
	def __on_drag_data_received(self, widget, context, x, y, data, info, timestamp):
		"""
		The drag destination received the data from the drag operation
		
		@param widget: the widget that received the signal
		@param context: the Gdk.DragContext
		@param x: the X position of the drop
		@param y: the Y position of the drop
		@param data: a Gtk.SelectionData object
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
			x, y = text_view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, x, y)
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
						if name in self._markers.keys():
							marker = self._markers[name]
							return self.on_marker_activated(marker, event)
						else:
							self.__log.warning("No marker found for TextMark '%s'" % name)
					else:
						# FIXME: this is not safe - use another symbol for right boundaries!
						self.__log.debug("Unnamed TextMark found, outside of any Markers")
						return
				
				# move left by one char and continue 
				if not it.backward_char():
					# start of buffer reached
					return
		
		elif event.button == 1 and event.get_state() & Gdk.ModifierType.CONTROL_MASK:
			x, y = text_view.get_pointer()
			x, y = text_view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, x, y)
			it = text_view.get_iter_at_location(x, y)
			# notify subclass
			self._ctrl_left_clicked(it)
	
	def _ctrl_left_clicked(self, it):
		"""
		Left-clicked on the editor with Ctrl modifier key pressed
		@param it: the Gtk.TextIter at the clicked position
		"""
	
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
	def extensions(self):
		"""
		Return a list of extensions for which this Editor is to be activated
		"""
		raise NotImplementedError
	
	def drag_drop_received(self, files):
		"""
		To be overridden
		
		@param files: a list of File objects dropped on the Editor
		"""
		pass
	
	@property
	def initial_timestamp(self):
		"""
		Return an initial reference timestamp (this just has to be smaller than
		every value returned by current_timestamp)
		"""
		return 0
	
	@property
	def current_timestamp(self):
		"""
		Return the current timestamp for buffer change recognition
		"""
		return time.time()
	
	def content_changed(self, reference_timestamp):
		"""
		Return True if the content of this Editor has changed since a given
		reference timestamp (this must be a timestamp as returned by current_timestamp)
		"""
		return self.__buffer_change_timestamp > reference_timestamp
	
	@property
	def charset(self):
		"""
		Return the character set used by this Editor
		"""
		return self._text_buffer.get_encoding().get_charset()
	
	@property
	def cursor_position(self):
		"""
		@return: a tuple containing (line, column)
		"""
		# only need by LaTeXForwardSearchAction
		iter = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
		return (iter.get_line(), iter.get_line_offset())
	
	@property
	def content(self):
		"""
		Return the string contained in the TextBuffer
		"""
		return self._text_buffer.get_text(self._text_buffer.get_start_iter(), 
									self._text_buffer.get_end_iter(), False).decode(self.charset)
	
	@property
	def content_at_left_of_cursor(self):
		"""
		Only return the content at left of the cursor
		"""
		end_iter = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
		return self._text_buffer.get_text(self._text_buffer.get_start_iter(), 
									end_iter, False).decode(self.charset)
	
	def insert(self, source):
		"""
		This may be overridden to catch special types like LaTeXSource
		"""
		self.__log.debug("insert(%s)" % source)
		
		if type(source) is Template:
			self._template_delegate.insert(source)
		else:
			self._text_buffer.insert_at_cursor(str(source))
		
		# grab the focus again (necessary e.g. after symbol insert)
		self._text_view.grab_focus()
	
	def insert_at_offset(self, offset, string, scroll=False):
		"""
		Insert a string at a certain offset
		
		@param offset: a positive int
		@param string: a str
		@param scroll: if True the view is scrolled to the insert position
		"""
		iter = self._text_buffer.get_iter_at_offset(offset)
		self._text_buffer.insert(iter, str(string))
		
		if scroll:
			self._text_view.scroll_to_iter(iter, .25)
		
		# grab the focus again (necessary e.g. after symbol insert)
		self._text_view.grab_focus()
	
	def append(self, string):
		"""
		Append some source (only makes sense with simple string) and scroll to it
		
		@param string: a str
		"""
		self._text_buffer.insert(self._text_buffer.get_end_iter(), str(string))
		self._text_view.scroll_to_iter(self._text_buffer.get_end_iter(), .25)
		
		# grab the focus again (necessary e.g. after symbol insert)
		self._text_view.grab_focus()
	
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
		# select
		it_start = self._text_buffer.get_iter_at_offset(start_offset)
		it_end = self._text_buffer.get_iter_at_offset(end_offset)
		self._text_buffer.select_range(it_start, it_end)
		# scroll
		self._text_view.scroll_to_iter(it_end, .25)
	
	def select_lines(self, start_line, end_line=None):
		"""
		Select a range of lines in the text
		
		@param start_line: the first line to select (counting from 0)
		@param end_line: the last line to select (if None only the first line is selected)
		"""
		it_start = self._text_buffer.get_iter_at_line(start_line)
		if end_line:
			it_end = self._text_buffer.get_iter_at_line(end_line)
		else:
			it_end = it_start.copy()
		it_end.forward_to_line_end()
		# select
		self._text_buffer.select_range(it_start, it_end)
		# scroll
		self._text_view.scroll_to_iter(it_end, .25)
	
	#
	# markers are used for highlighting (anonymous)
	#
	
	def register_marker_type(self, marker_type, background_color, anonymous=True):
		"""
		@param marker_type: a string
		@param background_color: a hex color
		@param anonymous: markers of an anonymous type may not be activated and do not get a unique ID
		"""
		assert not marker_type in self._marker_types.keys()
		
		# create Gtk.TextTag
		tag = self._text_buffer.create_tag(marker_type, background=background_color)
		
		self._tags.append(tag)
		
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
		
		# disconnect signal handlers
		for handler in self.__view_signal_handlers:
			self._text_view.disconnect(handler)
		
		for handler in self.__buffer_signal_handlers:
			self._text_buffer.disconnect(handler)
		
		# delete the tags that were created for markers
		table = self._text_buffer.get_tag_table()
		for tag in self._tags:
			table.remove(tag)
		
		# destroy the template delegate
		self._template_delegate.destroy()
		del self._template_delegate
		
		# destroy the views associated to this editor
		for i in self._window_context.editor_scope_views[self]:
			self._window_context.editor_scope_views[self][i].destroy()
		del self._window_context.editor_scope_views[self]
		
		# unreference the tab decorator
		del self._tab_decorator

		# destroy the completion distributor
		if self._completion_distributor != None:
			self._completion_distributor.destroy()
		del self._completion_distributor

		# unreference the window context
		del self._window_context
		
	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)


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
		
		self.window_scope_views = {}	# maps view ids to View objects
		self.editor_scope_views = {}	# maps Editor object to a map from ID to View object
		
		self.latex_previews = None

		self._log.debug("init")
	
	def create_editor_views(self, editor, file):
		"""
		Create instances of the editor specific Views for a given Editor instance
		and File
		
		Called by Editor base class
		"""
		self.editor_scope_views[editor] = {}
		try:
			for id, clazz in self._editor_scope_view_classes[file.extension].iteritems():
				# create View instance and add it to the map
				self.editor_scope_views[editor][id] = clazz(self, editor)
				
				self._log.debug("Created view " + id)
		except KeyError:
			self._log.debug("No views for %s" % file.extension)
	
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
			return self.editor_scope_views[editor][view_id]
		except KeyError:
			return self.window_scope_views[view_id]
	
	def set_action_enabled(self, action_id, enabled):
		"""
		Enable/disable an IAction object
		"""
		self._window_decorator._action_group.get_action(action_id).set_sensitive(enabled)
		
	def destroy(self):
		# unreference the window decorator
		del self._window_decorator
		
		# destroy the internal pdf previews
		if self.latex_previews != None:
			self.latex_previews.destroy()
			del self.latex_previews
		
	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)
	

from os import remove
import os.path
from glob import glob

from ..relpath import relpath
from ..typecheck import accepts
from ..typecheck.typeclasses import String


import re
import urllib
import urlparse

@accepts(String)
def fixurl(url):
	r"""From http://stackoverflow.com/questions/804336/best-way-to-convert-a-unicode-url-to-ascii-utf-8-percent-escaped-in-python/805166#805166 .
	Was named canonurl(). Comments added to the original are prefixed with ##.
	
	Return the canonical, ASCII-encoded form of a UTF-8 encoded URL, or ''
	if the URL looks invalid.

	>>> canonurl('	')
	''
	>>> canonurl('www.google.com')
	'http://www.google.com/'
	>>> canonurl('bad-utf8.com/path\xff/file')
	''
	>>> canonurl('svn://blah.com/path/file')
	'svn://blah.com/path/file'
	>>> canonurl('1234://badscheme.com')
	''
	>>> canonurl('bad$scheme://google.com')
	''
	>>> canonurl('site.badtopleveldomain')
	''
	>>> canonurl('site.com:badport')
	''
	>>> canonurl('http://123.24.8.240/blah')
	'http://123.24.8.240/blah'
	>>> canonurl('http://123.24.8.240:1234/blah?q#f')
	'http://123.24.8.240:1234/blah?q#f'
	>>> canonurl('\xe2\x9e\xa1.ws')  # tinyarro.ws
	'http://xn--hgi.ws/'
	>>> canonurl('  http://www.google.com:80/path/file;params?query#fragment  ')
	'http://www.google.com:80/path/file;params?query#fragment'
	>>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5')
	'http://xn--hgi.ws/%E2%99%A5'
	>>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5/pa%2Fth')
	'http://xn--hgi.ws/%E2%99%A5/pa/th'
	>>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5/pa%2Fth;par%2Fams?que%2Fry=a&b=c')
	'http://xn--hgi.ws/%E2%99%A5/pa/th;par/ams?que/ry=a&b=c'
	>>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5?\xe2\x99\xa5#\xe2\x99\xa5')
	'http://xn--hgi.ws/%E2%99%A5?%E2%99%A5#%E2%99%A5'
	>>> canonurl('http://\xe2\x9e\xa1.ws/%e2%99%a5?%E2%99%A5#%E2%99%A5')
	'http://xn--hgi.ws/%E2%99%A5?%E2%99%A5#%E2%99%A5'
	>>> canonurl('http://badutf8pcokay.com/%FF?%FE#%FF')
	'http://badutf8pcokay.com/%FF?%FE#%FF'
	>>> len(canonurl('google.com/' + 'a' * 16384))
	4096
	"""
	# strip spaces at the ends and ensure it's prefixed with 'scheme://'	
	url = url.strip()
	if not url:
		return ''
	if not urlparse.urlsplit(url).scheme:
		## We usually deal with local files here
		url = 'file://' + url
		## url = 'http://' + url

	# turn it into Unicode
	try:
		url = unicode(url, 'utf-8')
	except Exception, exc: #UnicodeDecodeError, exc:
		## It often happens that the url is already "python unicode" encoded
		if not str(exc) == "decoding Unicode is not supported":
			return ''  # bad UTF-8 chars in URL
		## If the exception is indeed "decoding Unicode is not supported"
		## this generally means that url is already unicode encoded,
		## so we can just continue (see http://www.red-mercury.com/blog/eclectic-tech/python-mystery-of-the-day/ )

	# parse the URL into its components
	parsed = urlparse.urlsplit(url)
	scheme, netloc, path, query, fragment = parsed

	# ensure scheme is a letter followed by letters, digits, and '+-.' chars
	if not re.match(r'[a-z][-+.a-z0-9]*$', scheme, flags=re.I):
		return ''
	scheme = str(scheme)

	## We mostly deal with local files here, and the following check 
	## would exclude all local files, so we drop it.	
	# ensure domain and port are valid, eg: sub.domain.<1-to-6-TLD-chars>[:port]
	#~ match = re.match(r'(.+\.[a-z0-9]{1,6})(:\d{1,5})?$', netloc, flags=re.I)
	#~ if not match:
		#~ print "return 4"
		#~ return ''
	#~ domain, port = match.groups()
	#~ netloc = domain + (port if port else '')
	netloc = netloc.encode('idna')

	# ensure path is valid and convert Unicode chars to %-encoded
	if not path:
		path = '/'  # eg: 'http://google.com' -> 'http://google.com/'
	path = urllib.quote(urllib.unquote(path.encode('utf-8')), safe='/;')

	# ensure query is valid
	query = urllib.quote(urllib.unquote(query.encode('utf-8')), safe='=&?/')

	# ensure fragment is valid
	fragment = urllib.quote(urllib.unquote(fragment.encode('utf-8')))

	# piece it all back together, truncating it to a maximum of 4KB
	url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
	return url[:4096]


class File(object):
	"""
	This is an object-oriented wrapper for all the os.* stuff. A File object
	represents the reference to a file.
	"""
	
	# TODO: use Gio.File as underlying implementation
	
	@staticmethod
	def create_from_relative_path(relative_path, working_directory):
		"""
		Create a File from a path relative to some working directory. 
		
		File.create_from_relative_path('../sub/file.txt', '/home/michael/base') == File('/home/michael/sub/file.txt')
		
		@param relative_path: a relative path, e.g. '../../dir/myfile.txt'
		@param working_directory: an absolute directory to be used as the starting point for the relative path
		"""
		absolute_path = os.path.abspath(os.path.join(working_directory, relative_path))
		return File(absolute_path)
	
	@staticmethod
	def is_absolute(path):
		return os.path.isabs(path)
	
	__log = getLogger("File")
	
	_DEFAULT_SCHEME = "file://"
	
	def __init__(self, uri):
		"""
		@param uri: any URI, URL or local filename
		"""
		if uri is None:
			raise ValueError("URI must not be None")
		
		self._uri = urlparse.urlparse(uri)
		if len(self._uri.scheme) == 0:
			# prepend default scheme if missing
			self._uri = urlparse.urlparse("%s%s" % (self._DEFAULT_SCHEME, uri))
	
	def create(self, content=None):
		"""
		Create a the File in the file system
		"""
		f = open(self.path, "w")
		if content is not None:
			f.write(content)
		f.close()
	
	@property
	def path(self):
		"""
		Returns '/home/user/image.jpg' for 'file:///home/user/image.jpg'
		"""
		return urllib.url2pathname(self._uri.path)
	
	@property
	def extension(self):
		"""
		Returns '.jpg' for 'file:///home/user/image.jpg'
		"""
		return os.path.splitext(self.path)[1]
	
	@property
	def shortname(self):
		"""
		Returns '/home/user/image' for 'file:///home/user/image.jpg'
		"""
		return os.path.splitext(self.path)[0]
	
	@property
	def basename(self):
		"""
		Returns 'image.jpg' for 'file:///home/user/image.jpg'
		"""
		return os.path.basename(self.path)
	
	@property
	def shortbasename(self):
		"""
		Returns 'image' for 'file:///home/user/image.jpg'
		"""
		return os.path.splitext(os.path.basename(self.path))[0]
	
	@property
	def dirname(self):
		"""
		Returns '/home/user' for 'file:///home/user/image.jpg'
		"""
		return os.path.dirname(self.path)
	
	@property
	def uri(self):
		# TODO: urllib.quote doesn't support utf-8
		return fixurl(self._uri.geturl())
	
	@property
	def exists(self):
		return os.path.exists(self.path)
	
	@property
	def mtime(self):
		if self.exists:
			return os.path.getmtime(self.path)
		else:
			raise IOError("File not found")
	
	def find_neighbors(self, extension):
		"""
		Find other files in the directory of this one having
		a certain extension
		
		@param extension: a file extension pattern like '.tex' or '.*'
		"""
		
		# TODO: glob is quite expensive, find a simpler way for this
		
		try:
			filenames = glob("%s/*%s" % (self.dirname, extension))
			neighbors = [File(filename) for filename in filenames]
			return neighbors
		
		except Exception, e:
			# as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
			# for an exception from that because the shortname may contain regex characters
			
			# TODO: a more robust solution would be an escape() method for re
			
			self.__log.debug("find_neighbors: %s" % e)
			
			return []
	
	@property
	def siblings(self):
		"""
		Find other files in the directory of this one having the same 
		basename. This means for a file '/dir/a.doc' this method returns 
		[ '/dir/a.tmp', '/dir/a.sh' ]
		"""
		siblings = []
		try:
			filenames = glob("%s.*" % self.shortname)
			siblings = [File(filename) for filename in filenames]
		except Exception, e:
			# as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
			# for an exception from that because the shortname may contain regex characters
			
			# TODO: a more robust solution would be an escape() method for re
			
			self.__log.debug("find_siblings: %s" % e)
		return siblings
	
	def relativize(self, base, allow_up_level=False):
		"""
		Relativize the path of this File against a base directory. That means that e.g.
		File("/home/user/doc.tex").relativize("/home") == "user/doc.tex"
		
		If up-level references are NOT allowed but necessary (e.g. base='/a/b/c', path='/a/b/d') 
		then the absolute path is returned.
		
		@param base: the base directory to relativize against
		@param allow_up_level: allow up-level references (../../) or not
		"""
		if allow_up_level:
			# TODO: os.path.relpath from Python 2.6 does the job
			
			return relpath(base, self.path)
		else:
			# TODO: why do we need this?
			
			# relative path must be 'below' base path
			if len(base) >= len(self.path):
				return self.path
			if self.path[:len(base)] == base:
				# bases match, return relative part
				return self.path[len(base)+1:]
			return self.path
	
	def relativize_shortname(self, base):
		"""
		Relativize the path of this File and return only the shortname of the resulting
		relative path. That means that e.g.
		File("/home/user/doc.tex").relativize_shortname("/home") == "user/doc"
		
		This is just a convenience method.
		
		@param base: the base directory to relativize against
		"""
		relative_path = self.relativize(base)
		return os.path.splitext(relative_path)[0]
	
	def delete(self):
		"""
		Delete the File from the file system
		
		@raise OSError: 
		"""
		if self.exists:
			remove(self.path)
		else:
			raise IOError("File not found")
	
	def __eq__(self, other):
		"""
		Override == operator
		"""
		try:
			return self.uri == other.uri
		except AttributeError:		# no File object passed or None
			# returning NotImplemented is bad because we have to
			# compare None with File
			return False
	
	def __ne__(self, other):
		"""
		Override != operator
		"""
		return not self.__eq__(other)
	
	def __str__(self):
		return self.uri
	
	def __cmp__(self, other):
		try:
			return self.basename.__cmp__(other.basename)
		except AttributeError:		# no File object passed or None
			# returning NotImplemented is bad because we have to
			# compare None with File
			return False

class Folder(File):
	
	# FIXME: a Folder is NOT a subclass of a File, both are a subclass of some AbstractFileSystemObject,
	# this is just a quick hack
	#
	# FIXME: but basically a Folder is a File so this class should not be needed 
	
	__log = getLogger("Folder")
	
	@property
	def files(self):
		"""
		Return File objects for all files in this Folder
		"""
		try:
			filenames = glob("%s/*" % (self.path))
			files = [File(filename) for filename in filenames]
			return files
		
		except Exception, e:
			# as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
			# for an exception from that because the shortname may contain regex characters
			
			# TODO: a more robust solution would be an escape() method for re
			
			self.__log.debug("files: %s" % e)
			
			return []
		
		
		
