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
BibTeX parser and object model

Benchmark with listb.bib:

 * this		2.870 real
 * old		3.320 real

"""

from logging import getLogger
from os.path import getmtime
from xml.sax.saxutils import escape

from ..issues import Issue


class Token(object):
	"""
	A BibTeX token
	"""
	
	AT, TEXT, COMMA, EQUALS, QUOTE, HASH, CURLY_OPEN, CURLY_CLOSE, ROUND_OPEN, ROUND_CLOSE = range(10)
	
	def __init__(self, type, offset, value):
		self._type = type
		self._offset = offset
		self._value = value
	
	@property
	def type(self):
		return self._type
	
	@property
	def offset(self):
		return self._offset
	
	@property
	def value(self):
		return self._value
	
	def __str__(self):
		return "<Token type='%s' value='%s' @%s>" % (self._type, self._value, self._offset)


class StringBuilder(list):
	"""
	One of the fastest ways to build strings in Python is to use a list
	and join it
	
	@deprecated: use "".join() directly
	"""
	_EMPTY = ""
	
	def __str__(self):
		return self._EMPTY.join(self)


from ..util import StringReader


class Lexer(object):
	"""
	BibTeX lexer. We only separate text from special tokens here and
	apply escaping.
	"""
	
	_TERMINALS_TOKENS = {"@" : Token.AT, "," : Token.COMMA, "=" : Token.EQUALS, 
						 "{" : Token.CURLY_OPEN, "}" : Token.CURLY_CLOSE, "\"" : Token.QUOTE,
						 "#" : Token.HASH, "(" : Token.ROUND_OPEN, ")" : Token.ROUND_CLOSE}
	
	_TERMINALS = set(_TERMINALS_TOKENS.keys()) 
	
	def __init__(self, string):
		self._reader = StringReader(string)
	
	def __iter__(self):
		return self
	
	def next(self):
		"""
		Return the next token
		"""
		
		escaping = False
		textBuilder = None
		textStart = None
		
		while True:
			c = self._reader.read()
			
			if not escaping and c in self._TERMINALS:
				if textBuilder:
					self._reader.unread(c)
					text = str(textBuilder)
					textBuilder = None
					return Token(Token.TEXT, textStart, text)
				
				return Token(self._TERMINALS_TOKENS[c], self._reader.offset, c)
				
			else:
				if not textBuilder:
					textStart = self._reader.offset
					textBuilder = StringBuilder(c)
				else:
					textBuilder.append(c)
				
				if c == "\\":
					escaping = True
				else:
					escaping = False


class BibTeXParser(object):
	
	_OUTSIDE, _TYPE, _AFTER_TYPE, _AFTER_STRING_TYPE, _KEY, _STRING_KEY, _AFTER_KEY, _AFTER_STRING_KEY, \
			_STRING_VALUE, _QUOTED_STRING_VALUE, _FIELD_NAME, _AFTER_FIELD_NAME, _FIELD_VALUE, _EMBRACED_FIELD_VALUE, \
			_QUOTED_FIELD_VALUE = range(15) 
	
	def parse(self, string, file, issue_handler):
		"""
		Parse a BibTeX content
		@param string: the content to be parsed
		@param file: the File object containing the BibTeX
		@param issue_handler: an object implementing IIssueHandler
		"""
		
		document = Document()
		state = self._OUTSIDE
		
		for token in Lexer(string):
			
			if state == self._OUTSIDE:
				if token.type == Token.AT:
					state = self._TYPE
					
			elif state == self._TYPE:
				if token.type == Token.TEXT:
					type = token.value.strip()
					
					if type.lower() == "string" :
						constant = Constant()
						state = self._AFTER_STRING_TYPE
					elif type.lower() == "preamble":	# skip
						state = self._OUTSIDE
					else:
						entry = Entry()
						entry.type = type
						entry.start = token.offset - 1
						state = self._AFTER_TYPE
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> in entry type" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					entry = None
					state = self._OUTSIDE
					
			elif state == self._AFTER_TYPE:
				if token.type == Token.CURLY_OPEN:
					closingDelimiter = Token.CURLY_CLOSE
					state = self._KEY
				elif token.type == Token.ROUND_OPEN:
					closingDelimiter = Token.ROUND_CLOSE
					state = self._KEY
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> after entry type" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					entry = None
					state = self._OUTSIDE
			
			elif state == self._AFTER_STRING_TYPE:
				if token.type == Token.CURLY_OPEN:
					closingDelimiter = Token.CURLY_CLOSE
					state = self._STRING_KEY
				elif token.type == Token.ROUND_OPEN:
					closingDelimiter = Token.ROUND_CLOSE
					state = self._STRING_KEY
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> after string type" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					constant = None
					state = self._OUTSIDE
			
			elif state == self._KEY:
				if token.type == Token.TEXT:
					entry.key = token.value.strip()
					state = self._AFTER_KEY
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> in entry key" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					entry = None
					state = self._OUTSIDE
			
			elif state == self._STRING_KEY:
				if token.type == Token.TEXT:
					constant.name = token.value.strip()
					state = self._AFTER_STRING_KEY
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> in string key" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					constant = None
					state = self._OUTSIDE

			elif state == self._AFTER_KEY:
				if token.type == Token.COMMA:
					state = self._FIELD_NAME
				elif token.type == closingDelimiter:
					entry.end = token.offset + 1
					document.entries.append(entry)
					state = self._OUTSIDE
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> after entry key" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					entry = None
					state = self._OUTSIDE
			
			elif state == self._AFTER_STRING_KEY:
				if token.type == Token.EQUALS:
					state = self._STRING_VALUE
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> after string key" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					constant = None
					state = self._OUTSIDE
			
			elif state == self._STRING_VALUE:
				if token.type == Token.QUOTE:
					state = self._QUOTED_STRING_VALUE
			
			elif state == self._QUOTED_STRING_VALUE:
				if token.type == Token.TEXT:
					constant.value = token.value
					document.constants.append(constant)
					state = self._OUTSIDE
			
			elif state == self._FIELD_NAME:
				if token.type == Token.TEXT:
					
					if token.value.isspace():
						continue
					
					field = Field()
					field.name = token.value.strip()
					state = self._AFTER_FIELD_NAME
				elif token.type == closingDelimiter:
					entry.end = token.offset + 1
					document.entries.append(entry)
					state = self._OUTSIDE
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> in field name" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					entry = None
					state = self._OUTSIDE
			
			elif state == self._AFTER_FIELD_NAME:
				if token.type == Token.EQUALS:
					state = self._FIELD_VALUE
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> after field name" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					entry = None
					state = self._OUTSIDE
			
			elif state == self._FIELD_VALUE:
				# TODO: we may not recognize something like "author = ," as an error
				
				if token.value.isspace():
					continue
				
				if token.type == Token.TEXT:
					value = token.value.strip()
					if value.isdigit():
						field.value.append(NumberValue(value))
					else:
						field.value.append(ConstantReferenceValue(value))
				elif token.type == Token.CURLY_OPEN:
					value = ""
					stack = [Token.CURLY_OPEN]
					state = self._EMBRACED_FIELD_VALUE
				elif token.type == Token.QUOTE:
					value = ""
					#stack = [Token.QUOTE]
					state = self._QUOTED_FIELD_VALUE
				elif token.type == Token.COMMA:
					entry.fields.append(field)
					state = self._FIELD_NAME
				elif token.type == closingDelimiter:
					entry.fields.append(field)
					entry.end = token.offset + 1
					document.entries.append(entry)
					state = self._OUTSIDE
				elif token.type == Token.HASH:
					pass
				else:
					issue_handler.issue(Issue("Unexpected token <b>%s</b> in field value" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
					entry = None
					state = self._OUTSIDE
			
			elif state == self._EMBRACED_FIELD_VALUE:
				if token.type == Token.CURLY_OPEN:
					stack.append(Token.CURLY_OPEN)
					value += token.value
				elif token.type == Token.CURLY_CLOSE:
					try:
						while stack[-1] != Token.CURLY_OPEN:
							stack.pop()
						stack.pop()
						
						if len(stack) == 0:
							field.value.append(StringValue(value))
							state = self._FIELD_VALUE
						else:
							value += token.value
						
					except IndexError:
						issue_handler.issue(Issue("Unexpected token <b>%s</b> in field value" % escape(token.value), 
											token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
						entry = None
						state = self._OUTSIDE
				else:
					value += token.value
			
			elif state == self._QUOTED_FIELD_VALUE:
				if token.type == Token.QUOTE:
					field.value.append(StringValue(value))
					state = self._FIELD_VALUE
				else:
					value += token.value
			
		return document


class Value(object):
	def __init__(self, text):
		self.text = text 
	
	@property
	def markup(self):
		# improve display
		
		if self.text[0] == "{" and self.text[-1] == "}":
			text = escape(self.text[1:-1])
		elif self.text.startswith("\\url{") and self.text[-1] == "}":
			text = "<u>%s</u>" % escape(self.text[5:-1])
		else:
			text = escape(self.text)
		
		return text
	
	def __str__(self):
		return "<Value text='%s'>" % self.text


class NumberValue(Value):
	def __str__(self):
		return "<NumberValue text='%s'>" % self.text


class StringValue(Value):
	def __str__(self):
		return "<StringValue text='%s'>" % self.text


class ConstantReferenceValue(Value):
	@property
	def markup(self):
		return "<i>%s</i>" % escape(self.text)
	
	def __str__(self):
		return "<ReferenceValue text='%s'>" % self.text


class Field(object):
	def __init__(self):
		self.name = None
		self.value = []
	
	@property
	def valueMarkup(self):
		return " ".join([v.markup for v in self.value])
	
	@property
	def valueString(self):
		return " ".join([v.text for v in self.value])
	
	def __str__(self):
		return "<Field name='%s' value='%s' />" % (self.name, self.value)


class Entry(object):
	def __init__(self):
		self.type = None
		self.key = None
		self.start = None
		self.end = None
		self.fields = []
	
	def findField(self, name):
		for field in self.fields:
			if field.name == name:
				return field
		raise KeyError
	
	def __str__(self):
		s = "<Entry type='%s' key='%s'>\n" % (self._type, self._key)
		for field in self._fields:
			s += "\t" + str(field) + "\n"
		s += "</Entry>"
		return s


class Constant(object):
	"""
	A BibTeX string constant
	"""
	def __init__(self):
		self.name = None
		self.value = None


class Document(object):
	def __init__(self):
		self.entries = []
		self.constants = []
	
	def __str__(self):
		s = "<Document>\n"
		for entry in self.entries:
			s += str(entry) + "\n"
		s += "</Document>"
		return s

