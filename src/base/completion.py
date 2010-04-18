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
base.completion
"""

from logging import getLogger
import gtk
import gtk.gdk
import gobject

from ..preferences import Preferences


class ProposalPopup(gtk.Window):
	"""
	Popup showing a list of proposals. This is implemented as a singleton
	as it doesn't make sense to have multiple popups around.
	"""
	
	_log = getLogger("ProposalPopup")
	
	_POPUP_WIDTH = 300
	_POPUP_HEIGHT = 200
	_SPACE = 0
	
	def __new__(cls):
		if not '_instance' in cls.__dict__:
			cls._instance = gtk.Window.__new__(cls)
		return cls._instance
	
	def __init__(self):
		if not '_ready' in dir(self):
			gtk.Window.__init__(self, gtk.WINDOW_POPUP)
			
			self._store = gtk.ListStore(str, object, gtk.gdk.Pixbuf)		# markup, Proposal instance
			
			self._view = gtk.TreeView(self._store)
			
			# pack the icon and text cells in one column to avoid the column separator
			column = gtk.TreeViewColumn()
			pixbuf_renderer = gtk.CellRendererPixbuf()
			column.pack_start(pixbuf_renderer, False)
			column.add_attribute(pixbuf_renderer, "pixbuf", 2)
		
			text_renderer = gtk.CellRendererText()
			column.pack_start(text_renderer, True)
			column.add_attribute(text_renderer, "markup", 0)
		
			self._view.append_column(column)
			
#			self._view.insert_column_with_attributes(-1, "", gtk.CellRendererPixbuf(), pixbuf=2)
#			self._view.insert_column_with_attributes(-1, "", gtk.CellRendererText(), markup=0)

			self._view.set_enable_search(False)
			self._view.set_headers_visible(False)
			
			scr = gtk.ScrolledWindow()
			scr.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
			scr.add(self._view)
			scr.set_size_request(self._POPUP_WIDTH, self._POPUP_HEIGHT)
			
			frame = gtk.Frame()
			frame.set_shadow_type(gtk.SHADOW_OUT)
			frame.add(scr)
			
			self.add(frame)
			
			self._details_popup = DetailsPopup()
			
			self._ready = True
	
	@property
	def selected_proposal(self):	
		"""
		Returns the currently selected proposal
		"""
		store, it = self._view.get_selection().get_selected()
		return store.get_value(it, 1)
	
	def activate(self, proposals, text_view):
		"""
		Load proposals, move to the cursor position and show
		"""
		self._set_proposals(proposals)
		self._move_to_cursor(text_view)
		
		self.show_all()
		
		self._update_details_popup()
	
	def deactivate(self):
		"""
		Hide this popup and the DetailsPopup
		"""
		self._details_popup.deactivate()
		self.hide()
	
	def _set_proposals(self, proposals):
		"""
		Loads proposals into the popup
		"""
		# sort
		proposals.sort()
		
		# load
		self._store.clear()
		for proposal in proposals:
			self._store.append([proposal.label, proposal, proposal.icon])
			
		self._view.set_cursor((0))
		
	def navigate(self, key):
		"""
		Moves the selection in the view according to key
		"""
		if key == "Up":
			d = -1
		elif key == "Down":
			d = 1
		elif key == "Page_Up":
			d = -5
		elif key == "Page_Down":
			d = 5
		else:
			return
		
		path = self._view.get_cursor()[0]
		index = path[0]
		max = self._store.iter_n_children(None)
		
		index += d
		
		if index < 0:
			index = 0
		elif index >= max:
			index = max - 1
			
		self._view.set_cursor(index)
		
		self._update_details_popup()
	
	def _get_cursor_pos(self, text_view):
		"""
		Retrieve the current absolute position of the cursor in a TextView
		"""
		buffer = text_view.get_buffer()
		location = text_view.get_iter_location(buffer.get_iter_at_mark(buffer.get_insert()))
		
		winX, winY = text_view.buffer_to_window_coords(gtk.TEXT_WINDOW_WIDGET, location.x, location.y)
		
		win = text_view.get_window(gtk.TEXT_WINDOW_WIDGET)
		xx, yy = win.get_origin()
		
		x = winX + xx
		y = winY + yy + location.height + self._SPACE
		
		return (x, y)
	
	def _update_details_popup(self):
		"""
		Move and show the DetailsPopup if the currently selected proposal
		contains details.
		"""
		try:
			index = self._view.get_cursor()[0][0]
			proposal = self._store[index][1]
			
#			self._log.debug("proposal.details: " + str(proposal.details))
			
			if proposal.details is None:
				self._details_popup.hide()
				return
			
			# move
			x, y = self.get_position()
			width = self.get_size()[0]
			path, column = self._view.get_cursor()
			rect = self._view.get_cell_area(path, column)
			
			self._details_popup.move(x + width + 2, y + rect.y)
			
			# activate
			self._details_popup.activate(proposal.details)
			
		except Exception, e:
			self._log.error(e)
		
	def _move_to_cursor(self, text_view):
		"""
		Move the popup to the current location of the cursor
		"""
		sw = gtk.gdk.screen_width()
		sh = gtk.gdk.screen_height()
		
		x, y = self._get_cursor_pos(text_view)
		
		w, h = self.get_size()
		
		if x + w > sw:
			x = sw - w - 4
		
		if y + h > sh:
			# get the height of a character
			layout = text_view.create_pango_layout("a")
			ytext = layout.get_pixel_size()[1]
			y = y - ytext - h
		
		self.move(x, y)


class DetailsPopup(gtk.Window):
	"""
	A popup showing additional information at the right of the currently 
	selected proposal in the ProposalPopup.
	
	This is used to display details of a BibTeX entry or the result of
	a template. 
	"""
	
	def __init__(self):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)
		
		self._color = Preferences().get("LightForeground", "#7f7f7f")
		
		self._label = gtk.Label()
		self._label.set_use_markup(True)
		self._label.set_alignment(0, .5)
		
		self._frame = gtk.Frame()
		self._frame.set_shadow_type(gtk.SHADOW_OUT)
		#self._frame.set_border_width(3)
		self._frame.add(self._label)
		
		self.add(self._frame)
		
	def activate(self, details):
		"""
		Create widget(s) for the given details and show the popup
		"""
		# remove the old child widget if present
		child = self._frame.get_child()
		if child:
			self._frame.remove(child)
			child.destroy()
		
		# create a child widget depending on the type of details
		if type(details) is list:
			# table data
			table = gtk.Table()
			table.set_border_width(5)
			table.set_col_spacings(5)
			rc = 0
			for row in details:
				cc = 0
				for column in row:
					if cc == 0:
						# first column
						label = gtk.Label("<span color='%s'>%s</span>" % (self._color, column))
					else:
						label = gtk.Label(column)
					label.set_use_markup(True)
					if cc == 0:
						# 1st column is right aligned
						label.set_alignment(1.0, 0.5)
					else:
						# others are left aligned
						label.set_alignment(0.0, 0.5)
					table.attach(label, cc, cc + 1, rc, rc + 1)
					cc += 1
				rc += 1
			self._frame.add(table)
		
		else:
			# markup text
			label = gtk.Label(details)
			label.set_use_markup(True)
			self._frame.add(label)
		
		self.show_all()
		
		# force a recompute of the window size
		self.resize(1, 1)
		
	def deactivate(self):
		"""
		Hide the popup
		"""
		self.hide()


class CompletionDistributor(object):
	"""
	This forms the lower end of the completion mechanism and hosts one 
	or more CompletionHandlers
	"""
	
	
	# TODO: clearify and simplify states here!
	# TODO: auto-close (maybe...)
	
	
	_log = getLogger("CompletionDistributor")
	
	_MAX_PREFIX_LENGTH = 100
	
	# completion delay in ms
	_DELAY = 500
	
	_STATE_IDLE, _STATE_CTRL_PRESSED, _STATE_ACTIVE = 0, 1, 2
	
	# keys that abort completion
	_ABORT_KEYS = [ "Escape", "Left", "Right", "Home", "End", "space", "Tab" ]
	
	# keys that are used to navigate in the popup
	_NAVIGATION_KEYS = [ "Up", "Down", "Page_Up", "Page_Down" ]
	
	# some characters have key constants that differ from their value
	_SPECIAL_KEYS = {"@" : "at"}
	
	def __init__(self, editor, handlers):
		"""
		@param editor: the instance of Editor this CompletionDistributor should observe
		@param handlers: a list of ICompletionHandler instances
		"""
		
		self._log.debug("init")
		
		self._handlers = handlers		# we already get objects
		
		self._editor = editor
		self._text_buffer = editor.tab_decorator.tab.get_document()
		self._text_view = editor.tab_decorator.tab.get_view()
		
		self._state = self._STATE_IDLE
		self._timer = None
		
		# collect trigger keys from all handlers
		self._trigger_keys = []
		for handler in self._handlers:
			for key in handler.trigger_keys:
				if key in self._SPECIAL_KEYS.keys():
					self._trigger_keys.append(self._SPECIAL_KEYS[key])
				else:
					self._trigger_keys.append(key)
		
		# TODO: is it right to instatiate this here?
		self._popup = ProposalPopup()
		
		# connect to signals
		self._signal_handlers = [
				self._text_view.connect("key-press-event", self._on_key_pressed),
				self._text_view.connect_after("key-release-event", self._on_key_released),
				self._text_view.connect("button-press-event", self._on_button_pressed),
				self._text_view.connect("focus-out-event", self._on_focus_out)
		]
	
	def _on_key_pressed(self, view, event):
		"""
		"""
		key = gtk.gdk.keyval_name(event.keyval)
		
		if self._state == self._STATE_IDLE:
			if key == "Control_L" or key == "Control_R":
				self._state = self._STATE_CTRL_PRESSED
				
			elif key in self._trigger_keys:
				self._start_timer()
				return False

		elif self._state == self._STATE_ACTIVE:
			if key == "Return":
				# select proposal
				
				self._abort()
				
				proposal = self._popup.selected_proposal
				self._select_proposal(proposal)
				
				# TODO: self._autoClose(proposalSelected=True)
				
				# returning True stops the signal
				return True
			
			elif key in self._ABORT_KEYS:
				self._abort()
				
			elif key in self._NAVIGATION_KEYS:
				self._popup.navigate(key)
				
				# returning True stops the signal
				return True
		
		elif self._state == self._STATE_CTRL_PRESSED:
			if key == "space":
				self._state = self._STATE_IDLE
				self._complete()
				return True
			else:
				self._state = self._STATE_IDLE
		
		self._stop_timer()
	
	def _on_key_released(self, view, event):
		"""
		"""
		key = gtk.gdk.keyval_name(event.keyval)
		
#		# trigger auto close on "}"
#		if key == "braceright":
#			# TODO: self._autoClose(braceTyped=True)
#			pass
		
		
		if self._state == self._STATE_ACTIVE:
			if key in self._NAVIGATION_KEYS or key in ["Control_L", "Control_R", "space"]:
				# returning True stops the signal
				return True
			else:
				# user is typing on with active popup...
				
				# TODO: we should check here if the cursor has moved
				# or better if the buffer has changed
				
				self._complete()
	
	def _on_button_pressed(self, view, event):
		self._abort()
	
	def _on_focus_out(self, view, event):
		self._abort()
	
	def _start_timer(self):
		"""
		Start a timer for completion
		"""
		# stop eventually running timer
		self._stop_timer()
		# start timer
		self._timer = gobject.timeout_add(self._DELAY, self._timer_callback)
	
	def _stop_timer(self):
		"""
		Stop the timer if it has been started
		"""
		if self._timer is not None:
			gobject.source_remove(self._timer)
			self._timer = None
		
	def _timer_callback(self):
		"""
		Timeout
		"""
		self._complete()
		
		return False	# do not call again
	
	def _complete(self):
		all_proposals = []
		
		for handler in self._handlers:
			delimiters = handler.prefix_delimiters
			
			prefix = self._find_prefix(delimiters)
			if prefix:
#				if handler.strip_delimiter:
#					prefix = prefix[1:]
				
				proposals = handler.complete(prefix)
				assert type(proposals) is list
				
				all_proposals.extend(proposals)
			
		if len(all_proposals):
			self._popup.activate(all_proposals, self._text_view)
			self._state = self._STATE_ACTIVE
		else:
			self._abort()
	
	def _find_prefix(self, delimiters):
		"""
		Find the start of the surrounding command and return the text
		from there to the cursor position.
		
		This is the prefix forming the basis for LaTeX completion.
		"""
		it_right = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
		it_left = it_right.copy()
		
		# go back by one character (insert iter points to the char at the right of
		# the cursor!)
		if not it_left.backward_char():
			self._log.debug("_find_prefix: start of buffer reached")
			return None
		
		# move left until 'the left-most of a sequence of delimiters'
		#
		# e.g. if 'x' is a delimiter and 'abcxxx' is at left of the cursor, we 
		# recognize 'xxx' as the prefix instead of only 'x'
		delim_found = False
		delim_char = None
		
		i = 0
		while i < self._MAX_PREFIX_LENGTH:
			c = it_left.get_char()
			
			if delim_found:
				if c != delim_char:
					# a delimiter has been found and the preceding character 
					# is different from it
					break
			else:
				if c in delimiters:
					# a delimiter has been found
					delim_found = True
					delim_char = c
			
			if not it_left.backward_char():
				self._log.debug("_find_prefix: start of buffer reached")
				return None
			
			i += 1
		
		# to recognize the left-most delimiter, we have moved one char
		# too much
		it_left.forward_char()
		
		if i == self._MAX_PREFIX_LENGTH:
			self._log.debug("_find_prefix: prefix too long")
			return None
		
		prefix = self._text_buffer.get_text(it_left, it_right, False)
		
		return prefix
	
	def _select_proposal(self, proposal):
		"""
		Insert the source contained in the activated proposal
		"""
		self._editor.delete_at_cursor(- proposal.overlap)
		self._editor.insert(proposal.source)
	
	def _abort(self):
		"""
		Abort completion
		"""
		if self._state == self._STATE_ACTIVE:
			self._popup.deactivate()
			self._state = self._STATE_IDLE
	
	def destroy(self):
		# unreference the editor (very important! cyclic reference)
		del self._editor
		
		# disconnect text view events
		for handler in self._signal_handlers:
			self._text_view.disconnect(handler)
	
	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)
	