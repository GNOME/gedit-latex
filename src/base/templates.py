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
base.templates
"""

from logging import getLogger


class Placeholder(object):
	def __init__(self, label, offset):
		"""
		@param label: label of this placeholder
		@param offset: offset in plain text
		"""
		self._label = label
		self._offset = offset
	
	@property
	def label(self):
		return self._label
	
	@property
	def offset(self):
		return self._offset


class MalformedTemplateException(Exception):
	"""
	Raised if a template expression could not be tokenized
	"""


from ..util import caught


class TemplateCompiler(object):
	
	_S_DEFAULT, _S_IDENT, _S_PLACEHOLDER = 0, 1, 2
	
	def _reset(self):
		self._placeholders = []
		self._plain = ""
		self._final_cursor_offset = None
	
	@property
	def placeholders(self):
		return self._placeholders
	
	@property
	def plain(self):
		return self._plain
	
	@property
	def final_cursor_offset(self):
		return self._final_cursor_offset
	
	def compile(self, expression):
		"""
		@param expression: template expression
		@raise MalformedTemplateException: if the expression could not be tokenized
		@return: a list of tokens
		"""
		
		# TODO: redo this from DFA
		
		self._reset()
		
		state = self._S_DEFAULT
		offset = 0
		
		try:
			for c in expression:
				if state == self._S_DEFAULT:
					# we're in plain text
					if c == "$":
						# the magic char appeared, so change state
						state = self._S_IDENT
					else:
						# nothing special, so append to plain text
						self._plain += c
						offset += 1
						
				elif state == self._S_IDENT:
					# the magic char has appeared
					if c == "{":
						# a placeholder is starting, so create a builder for its name
						name = []
						# save its position
						position = offset
						# and change state
						state = self._S_PLACEHOLDER
					elif c == "_":
						# "$_" marks the final cursor position
						self._final_cursor_offset = offset
						# and change state back to default
						state = self._S_DEFAULT
					else:
						# false alarm, the magic sign was just a dollar sign, so append
						# the "$" and the current char to plain text
						plain += "$" + c
						offset += 2
						# and change to default state
						state = self._S_DEFAULT
						
				elif state == self._S_PLACEHOLDER:
					# we're in a placeholder definition
					if c == "}":
						# it is ending, so append object
						self._placeholders.append(Placeholder("".join(name), position))
						self._plain += "".join(name)
						# change state
						state = self._S_DEFAULT
					else:
						# it is not ending
						name.append(c)
						offset += 1
		except Exception, e:
			raise MalformedTemplateException(e)
		
		# if everything went fine we should end up in default state
		if state != self._S_DEFAULT:
			raise MalformedTemplateException
	

import gtk.gdk

from .interface import Template

	
class TemplateDelegate(object):
	"""
	This handles templates for an Editor instance
	"""
	
	_log = getLogger("TemplateDelegate")
	
	
	def __init__(self, editor):
		self._editor = editor
		self._text_buffer = editor.tab_decorator.tab.get_document()
		self._text_view = editor.tab_decorator.tab.get_view()
		
		self._compiler = TemplateCompiler()
		
		# create tags
		self._tag_template = self._text_buffer.create_tag("template", background="#f2f7ff")
		self._tag_placeholder = self._text_buffer.create_tag("placeholder", background="#d6e4ff", foreground="#2a66e1")
		
		self._active = False
	
	def insert(self, template):
		"""
		@param template: a Template instance
		"""
		assert type(template) is Template
		
		# apply indentation
		expression = template.expression.replace("\n", "\n%s" % self._editor.indentation)
		
		try:
			self._compiler.compile(expression)
			self._do_insert()
		except MalformedTemplateException, e:
			self._log.error(e)
	
	def _do_insert(self):
		if len(self._compiler.placeholders) == 0:
			# template contains no placeholders > just insert plain text
			#
			# if it contains a cursor position, we check if there's a selection
			# if there is one, we surround that selection by the two pieces of the template
			
			if self._compiler.final_cursor_offset:
				bounds = self._text_buffer.get_selection_bounds()
				if len(bounds):
					# cursor position and selection > surround selection
					
					text = self._compiler.plain
					position = self._compiler.final_cursor_offset
					
					leftText = text[:position]
					rightText = text[position:]
					
					# store the selection marks
					lMark = self._text_buffer.create_mark(None, bounds[0], False)
					
					rMark = self._text_buffer.create_mark(None, bounds[1], True)
					
					# insert first piece at the beginning...
					self._text_buffer.insert(bounds[0], leftText)				
					
					# ...and the other one at the end
					rIter = self._text_buffer.get_iter_at_mark(rMark)
					self._text_buffer.insert(rIter, rightText)					
					
					# restore selection
					lIter = self._text_buffer.get_iter_at_mark(lMark)
					rIter = self._text_buffer.get_iter_at_mark(rMark)
					self._text_buffer.select_range(lIter, rIter)
					
					# delete marks
					self._text_buffer.delete_mark(lMark)
					self._text_buffer.delete_mark(rMark)
				
				else:
					# cursor position, no selection > insert text and place cursor
					
					startOffset = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert()).get_offset()
					self._text_buffer.insert_at_cursor(self._compiler.plain)
					self._markEnd = self._text_buffer.create_mark(None, 
							self._text_buffer.get_iter_at_offset(startOffset + self._compiler.final_cursor_offset),  True)
					self._text_buffer.place_cursor(self._text_buffer.get_iter_at_mark(self._markEnd))
			
			else:
				# no final cursor position > just insert plain text
				
				self._text_buffer.insert_at_cursor(self._compiler.plain)
			
		else:
			# avoid inserting templates into templates
			if self._active:
				self._leave_template(place_cursor=False)
			
			# save template start offset
			startIter = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
			start = startIter.get_offset()
			self._markStart = self._text_buffer.create_mark(None, startIter, True)
			
			# insert template text
			self._text_buffer.insert_at_cursor(self._compiler.plain)
			
			# highlight placeholders and save their positions

			self._placeholder_marks = []		# holds the left and right marks of all placeholders in the active template
			
			for placeholder in self._compiler.placeholders:
				
				itLeft = self._text_buffer.get_iter_at_offset(start + placeholder.offset)
				itRight = self._text_buffer.get_iter_at_offset(start + placeholder.offset + len(placeholder.label))
				
				self._text_buffer.apply_tag_by_name("placeholder", itLeft, itRight)
				
				markLeft = self._text_buffer.create_mark(None, itLeft, True)
				markRight = self._text_buffer.create_mark(None, itRight, False)
				
				self._placeholder_marks.append([markLeft, markRight])
			
			
			# highlight complete template area
			itStart = self._text_buffer.get_iter_at_offset(start)
			itEnd = self._text_buffer.get_iter_at_offset(start + len(self._compiler.plain))
			
			self._text_buffer.apply_tag_by_name("template", itStart, itEnd)
			
			self._markEnd = self._text_buffer.create_mark(None, itEnd, True)
			
			# mark end cursor position or template end
			if self._compiler.final_cursor_offset:
				self._mark_final = self._text_buffer.create_mark(None, 
														self._text_buffer.get_iter_at_offset(start + self._compiler.final_cursor_offset), 
														True)
			else:
				self._mark_final = self._text_buffer.create_mark(None, itEnd, True)
			
			
			self._selected_placeholder = 0
			
			self._activate()
			
			self._select_placeholder(0)
	
	def _activate(self):
		"""
		Listen to TextView signals
		"""
		assert not self._active
		
		self._handlers = [ self._text_view.connect("key-press-event", self._on_key_pressed),
							self._text_view.connect_after("key-release-event", self._on_key_released),
							self._text_view.connect("button-press-event", self._on_button_pressed) ]
		self._active = True
	
	def _deactivate(self):
		"""
		Disconnect from TextView signals
		"""
		assert self._active
		
		for handler in self._handlers:
			self._text_view.disconnect(handler)
		self._active = False
	
	def _on_key_pressed(self, text_view, event):
		"""
		Jump to the next or to the previous placeholder mark
		"""
		assert self._active
		
		key = gtk.gdk.keyval_name(event.keyval)
		
		if key == "Tab":
			# select next placeholder
			self._selected_placeholder += 1
			
			try:
				self._select_placeholder(self._selected_placeholder)
			except IndexError:
				# last reached
				self._leave_template()
			
			# swallow event
			return True
		
		elif key == "ISO_Left_Tab":
			# select previous placeholder
			self._selected_placeholder -= 1
			
			try:
				self._select_placeholder(self._selected_placeholder)
			except IndexError:
				# first reached
				self._selected_placeholder = 0
				
			# swallow event
			return True
		
		elif key == "Escape":
			# abort
			self._leave_template()
		
	
	def _on_key_released(self, text_view, event):
		"""
		Swallow key events if neccessary
		"""
		assert self._active
		
		key = gtk.gdk.keyval_name(event.keyval)
		
		if key == "Tab" or key == "ISO_Left_Tab":
			# swallow event
			return True
		
		else:
			# check if the cursor has left the template
			if not self._cursor_in_template:
				self._leave_template(place_cursor=False)
			
	
	def _on_button_pressed(self, text_view, event):
		"""
		Leave template when mouse button is pressed
		"""
		assert self._active
		
		self._leave_template()
		
	def _select_placeholder(self, placeholder_index):
		"""
		Select a given placeholder
		"""
		# TODO: replace by _next_placeholder() and _prior_placeholder() or anything
		# more robust
		
		#self._log.debug("_select_placeholder(%s)" % placeholder_index)
		
		# get stored marks
		markLeft, markRight = self._placeholder_marks[self._selected_placeholder]
		
		# select
		itLeft = self._text_buffer.get_iter_at_mark(markLeft)
		itRight = self._text_buffer.get_iter_at_mark(markRight)
		
		self._text_buffer.select_range(itLeft, itRight)
	
	def _leave_template(self, place_cursor=True):
		"""
		Quit template insertion.
		
		Disconnect from signals, remove highlight, delete marks and place the cursor
		at the final position.
		"""
		#self._log.debug("_leaveTemplate")

		# remove highlighting
		self._text_buffer.remove_tag_by_name("placeholder", self._text_buffer.get_start_iter(), 
									self._text_buffer.get_end_iter())
		self._text_buffer.remove_tag_by_name("template", self._text_buffer.get_start_iter(), 
									self._text_buffer.get_end_iter())
		
		# move to end cursor position or template end
		if place_cursor:
			self._text_buffer.place_cursor(self._text_buffer.get_iter_at_mark(self._mark_final))
		
		self._deactivate()
	
	@property
	def _cursor_in_template(self):
		"""
		@return: True if the cursor is in the template
		"""
		itLeft = self._text_buffer.get_iter_at_mark(self._markStart)
		itRight = self._text_buffer.get_iter_at_mark(self._markEnd)
		
		left = itLeft.get_offset()
		right = itRight.get_offset()
		offset = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert()).get_offset()
		
		if offset < left or offset > right:
			return False
		return True
	
	def destroy(self):
		self._log.debug("destroy")
		
		# remove tags
		table = self._text_buffer.get_tag_table()
		table.remove(self._tag_template)
		table.remove(self._tag_placeholder)
		
		# disconnect from key signals
		
	
