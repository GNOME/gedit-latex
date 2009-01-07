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
bibtex.parser

BibTeX parser and object model
"""

#
##
## async parser feature
##
#if __name__ == "__main__":
#	#
#	# The script has been started in a shell process
#	#
#	# Parse the file passed as first argument and write the model
#	# as a pickled object to STDOUT
#	#
#	import sys
#	
#	# TODO: fetch issues and pass them together with the model in a special
#	# transfer object
#	
#	plugin_path = sys.argv[1]
#	filename = sys.argv[2]
#	
#	sys.path.append(plugin_path) 
#	sys.path.append("/home/michael/.gnome2/gedit/plugins")
#	
#	from issues import MockIssueHandler
#	from base import File
#	
#	model = BibTeXParser().parse_async(open(filename).read(), filename)
#else:
#	#
#	# normal package code...
#	#


from logging import getLogger
from os.path import getmtime
from xml.sax.saxutils import escape

from ..issues import Issue, MockIssueHandler


#	import sys
#	import os
#	
#	print "======== sys.path=%s, cwd=%s" % (sys.path, os.getcwd())


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
	
	
	def parse_async(self, string, filename):
		"""
		Method called by the AsyncParserRunner
		"""
		return self.parse(string, File(filename), MockIssueHandler())
	
	
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
	
	MAX_MARKUP_LENGTH = 50
	
	@property
	def markup(self):
		text = self.text
		
		# remove braces
		if text.startswith("{{") and text.endswith("}}"):
			text = text[2:-2]
		elif text.startswith("{") and text.endswith("}"):
			text = text[1:-1]
		elif text.startswith("\\url{") and text.endswith("}"):
			text = text[5:-1]
		
		# truncate
		if len(text) > self.MAX_MARKUP_LENGTH:
			text = text[:self.MAX_MARKUP_LENGTH] + "..."
		
		# remove newlines
		text = text.replace("\n", "")
		
		# escape problematic characters
		text = escape(text)
		
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
	
	
#	#
#	# async parser feature
#	#
#	
#	# TODO: put the __main__ part in another file
#	
#	import pickle
#	import os
#	
#	from ..tools.util import Process
#	from ..base.resources import PLUGIN_PATH
#	
#	# TODO: time pickle.loads() and pickle.dump()
#	# TODO: support Process.abort()
#	
#	class AsyncParserRunner(Process):
#		
#		__log = getLogger("AsyncParserRunner")
#		
#		def parse(self, file):
#			self.__pickled_object = None
#			
#			source_path = PLUGIN_PATH + "/src"
#			self.__log.debug("chdir: %s" % source_path)
#			os.chdir(source_path)
#			
#			self.execute("python %s/bibtex/parser.py %s %s" % (source_path, source_path, file.path))
#		
#		def _on_stdout(self, text):
#			# Process._on_stdout
#			self.__pickled_object = text
#			
#		def _on_stderr(self, text):
#			# Process._on_stderr
#			self.__log.debug("_on_stderr: %s" % text)
#		
#		def _on_abort(self):
#			# Process._on_abort
#			pass
#		
#		def _on_exit(self, condition):
#			# Process._on_exit
#			self.__log.debug("_on_exit")
#			
#			model = None
#			
#			if condition:
#				self.__log.error("failed")
#			else:
#				model = pickle.loads(self.__pickled_object)
#			
#			self._on_parser_finished(model)
#		
#		def _on_parser_finished(self, model):
#			"""
#			To be overridden by the subclass
#			"""
	
	
		
		
		
