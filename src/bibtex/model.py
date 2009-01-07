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
bibtex.model

The model of BibTeX read from an XML file. This is used for 
the 'New Entry' dialog.
"""

from xml.sax import ContentHandler, parse


class EntryType(object):
	def __init__(self, name):
		self._name = name
		self._required_fields = []
		self._optional_fields = []
	
	@property
	def name(self):
		return self._name

	@property
	def requiredFields(self):
		return self._required_fields
	
	@property
	def optionalFields(self):
		return self._optional_fields


class Field(object):
	def __init__(self, name, label):
		self._name = name
		self._label = label
	
	@property
	def name(self):
		return self._name
	
	@property
	def label(self):
		return self._label


class Definition(object):
	"""
	Holds a definition for BibTeX
	"""
	def __init__(self):
		self._fields = {}
		self._types = []
	
	@property
	def fields(self):
		return self._fields
	
	@property
	def types(self):
		return self._types


class DefinitionParser(ContentHandler):
	"""
	This parses the bibtex.xml and builds up an object model of the
	above classes.
	"""
	
	S_IDLE, S_FIELDS, S_REQUIRED, S_OPTIONAL = range(4)
	
	def __init__(self):
		self._state = self.S_IDLE
		self._type = None
	
	def startElement(self, name, attributes):
		if name == "fields":
			self._state = self.S_FIELDS		# we are now parsing the known fields
		elif name == "required":
			self._state = self.S_REQUIRED
		elif name == "optional":
			self._state = self.S_OPTIONAL
		elif name == "field":
			if self._state == self.S_FIELDS:
				# we are in <fields>
				id = attributes["id"]
				self._definition.fields[id] = Field(id, attributes["_label"])
			elif self._state == self.S_REQUIRED:
				# we are in <types><type><required>
				id = attributes["id"]
				try:
					f = self._definition.fields[id]
					self._type.requiredFields.append(f)
				except KeyError:
					raise Exception("Field '%s' not declared in <fields>" % id)
			elif self._state == self.S_OPTIONAL:
				# we are in <types><type><optional>
				id = attributes["id"]
				try:
					f = self._definition.fields[id]
					self._type.optionalFields.append(f)
				except KeyError:
					raise Exception("Field '%s' not declared in <fields>" % id)
			else:
				raise Exception("<field> is not allowed here")
		elif name == "type":
			t = EntryType(attributes["id"])
			self._definition.types.append(t)
			self._type = t
			
	def parse(self, definition, filename):
		self._definition = definition
		parse(filename, self)
		
		