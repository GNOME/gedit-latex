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


#import gtk
from logging import getLogger
from xml.sax.saxutils import escape
from os.path import exists
from os import popen, system
from re import compile


#from ..concepts import Issue, EventTrigger
#from ..environment import Environment

from ..util import caught
from ..issues import Issue


class StringListener(object):
	"""
	Recognizes a string in a stream of characters
	"""
	def __init__(self, string, any_position=True):
		"""
		@param string: the character sequence to be recognized
		@param any_position: if True the sequence may occur at any position in
				the stream, if False it must occur at the start
		"""
		self._string = string
		self._last = len(string)
		self._pos = 0
		self._any_position = any_position
		
		self._active = True
		
	def put(self, char):
		"""
		Returns True if the string is recognized
		"""
		if not self._active:
			return False
		
		if char == self._string[self._pos]:
			self._pos += 1
		
			if self._pos == self._last:
				return True
		else:
			if self._any_position:
				self._pos = 0
			else:
				self._active = False
			
		return False


class Node(list):
	"""
	This is the base class of the LaTeX object model
	"""
	
	DOCUMENT, COMMAND, MANDATORY_ARGUMENT, OPTIONAL_ARGUMENT, TEXT, EMBRACED = range(6)
	
	def __init__(self, type, value=None):
		self.type = type
		self.value = value
		self.parent = None
		
		# this indicates if an argument is closed or not
		# (only used by the PrefixParser)
		self.closed = False
	
	def firstOfType(self, type):
		"""
		Return the first child node of a given type
		"""
		for node in self:
			if node.type == type:
				return node
		raise IndexError
	
	def filter(self, type):
		"""
		Return all child nodes of this node having a certain type
		"""
		return [node for node in self if node.type == type]
	
	@property
	def xml(self):
		"""
		Return an XML representation of this node (for debugging)
		"""
		if self.type == self.COMMAND:
			content = "".join([node.xml for node in self])
			if len(content):
				return "<command name=\"%s\">%s</command>" % (self.value, content)
			else:
				return "<command name=\"%s\" />" % self.value
		elif self.type == self.MANDATORY_ARGUMENT:
			return "<mandatory>%s</mandatory>" % "".join([node.xml for node in self])
		elif self.type == self.OPTIONAL_ARGUMENT:
			return "<optional>%s</optional>" % "".join([node.xml for node in self])
		elif self.type == self.TEXT:
			return escape(self.value)
		elif self.type == self.DOCUMENT:
			return "<document>%s</document>" % "".join([node.xml for node in self])
		elif self.type == self.EMBRACED:
			return "<embraced>%s</embraced>" % "".join([node.xml for node in self])
	
	@property
	def xmlPrefix(self):
		"""
		Return an XML representation of this node (for debugging)
		
		This is for the prefix mode, so we print if the arguments are closed or not
		"""
		if self.type == self.COMMAND:
			content = "".join([node.xmlPrefix for node in self])
			if len(content):
				return "<command name=\"%s\">%s</command>" % (self.value, content)
			else:
				return "<command name=\"%s\" />" % self.value
		elif self.type == self.MANDATORY_ARGUMENT:
			return "<mandatory closed=%s>%s</mandatory>" % (self.closed, "".join([node.xmlPrefix for node in self]))
		elif self.type == self.OPTIONAL_ARGUMENT:
			return "<optional closed=%s>%s</optional>" % (self.closed, "".join([node.xmlPrefix for node in self]))
		elif self.type == self.TEXT:
			return escape(self.value)
		elif self.type == self.DOCUMENT:
			return "<document>%s</document>" % "".join([node.xmlPrefix for node in self])
		elif self.type == self.EMBRACED:
			return "<embraced>%s</embraced>" % "".join([node.xmlPrefix for node in self])
	
	def __str__(self):
		"""
		Return the original LaTeX representation of this node
		"""
		if self.type == self.COMMAND:
			return "\\%s%s" % (self.value, "".join([str(node) for node in self]))
		elif self.type == self.MANDATORY_ARGUMENT or self.type == self.EMBRACED:
			return "{%s}" % "".join([str(node) for node in self])
		elif self.type == self.OPTIONAL_ARGUMENT:
			return "[%s]" % "".join([str(node) for node in self])
		elif self.type == self.TEXT:
			return self.value
		elif self.type == self.DOCUMENT:
			return "".join([str(node) for node in self])
	
	@property
	def innerText(self):
		"""
		Return the concatenated values of all TEXT child nodes
		"""
		return "".join([child.value for child in self if child.type == Node.TEXT])
	
	@property
	def markup(self):
		"""
		Return the concatenated markup values of this node and all child nodes
		"""
		if self.type == self.COMMAND:
			return "<span color=\"grey\">\\%s</span>%s" % (self.value, "".join([node.markup for node in self]))
		elif self.type == self.MANDATORY_ARGUMENT or self.type == self.EMBRACED:
			return "<span color=\"grey\">{</span>%s<span color=\"grey\">}</span>" % "".join([node.markup for node in self])
		elif self.type == self.OPTIONAL_ARGUMENT:
			return "<span color=\"grey\">[</span>%s<span color=\"grey\">]</span>" % "".join([node.markup for node in self])
		elif self.type == self.TEXT:
			return escape(self.value)
		elif self.type == self.DOCUMENT:
			return "".join([node.markup for node in self])
	
	@property
	def innerMarkup(self):
		"""
		Return the concatenated markup values of only the child nodes
		"""
		return "".join([node.markup for node in self])
	
	def append(self, node):
		"""
		Append a child node and store a back-reference
		"""
		node.parent = self
		list.append(self, node)
	
	def find(self, value):
		"""
		Find child node with given value (recursive, so grand-children are found, too)
		"""
		# TODO
		

class Document(Node):
	"""
	An extended Node with special methods for a LaTeX document
	"""
	
	def __init__(self, file):
		Node.__init__(self, Node.DOCUMENT, file)
		
		self._is_master_called = False
		self._is_master = False
	
	def _do_is_master(self):
		# TODO: this should be recursive
		
		for node in self:
			if node.type == Node.COMMAND and node.value == "begin":
				if node.firstOfType(Node.MANDATORY_ARGUMENT).innerText == "document":
					return True
		return False
	
	@property
	def is_master(self):
		"""
		@return: True if this document is a master document
		"""
		
		# TODO: determine this while parsing
		
		if not self._is_master_called:
			self._is_master = self._do_is_master()
			self._is_master_called = True
		return self._is_master


class LocalizedNode(Node):
	"""
	This Node type holds the start and end offsets of the substring it belongs to
	in the source
	"""
	def __init__(self, type, start, end, value=None):
		Node.__init__(self, type, value)
		self.start = start
		self.end = end
	
	@property
	def lastEnd(self):
		"""
		Return the end of the last child node or of this node if
		it doesn't have children.
		"""
		try:
			return self[-1].end
		except IndexError:
			return self.end


class StringReader(object):
	"""
	A simple string reader that is able to push back one character
	"""
	def __init__(self, string):
		self._iter = iter(string)
		self.offset = 0
		self._pushbackChar = None
		self._pushbackFlag = False
	
	def read(self):
		if self._pushbackFlag:
			self._pushbackFlag = False
			return self._pushbackChar
		else:
			self.offset += 1
			return self._iter.next()
	
	def unread(self, char):
		#assert not self._pushbackFlag
		
		self._pushbackChar = char
		self._pushbackFlag = True


class Token(object):
	"""
	A Token returned by the Lexer
	"""
	
	COMMAND, TEXT, COMMENT, VERBATIM, BEGIN_CURLY, END_CURLY, BEGIN_SQUARE, END_SQUARE = range(8)
	
	def __init__(self, type, offset=None, value=None):
		self.type = type
		self.offset = offset
		self.value = value
	
	@property
	def xml(self):
		if self.type == self.COMMAND:
			return "<t:command>%s</t:command>" % self.value
		elif self.type == self.TEXT:
			return "<t:text>%s</t:text>" % self.value
		elif self.type == self.VERBATIM:
			return "<t:verbatim>%s</t:verbatim>" % self.value
		elif self.type == self.COMMENT:
			return "<t:comment>%s</t:comment>" % self.value
		else:
			return "<t:terminal />"


class Lexer(object):
	"""
	LaTeX lexer
	"""
	
	# TODO: redesign and optimize this from a DFA
	
	# states of the lexer
	_DEFAULT, _BACKSLASH, _COMMAND, _TEXT, _COMMENT, _VERB, _VERBATIM = range(7)
	
	_SPECIAL = set(["&", "$", "{", "}", "[", "]", "%", "#", "_", "\\"])
	
	_TERMINALS = set(["{", "}", "[", "]"])
	_TERMINALS_MAP = {"{" : Token.BEGIN_CURLY, "}" : Token.END_CURLY, 
					  "[" : Token.BEGIN_SQUARE, "]" : Token.END_SQUARE}
	
	_VERBATIM_ENVIRONS = set(["verbatim", "verbatim*", "lstlisting", "lstlisting*"])
	
	
	# additional states for recognizing "\begin{verbatim}"
	_VERBATIM_BEGIN, _VERBATIM_BEGIN_CURLY, _VERBATIM_BEGIN_CURLY_ENVIRON = range(3)
	
	
	def __init__(self, string, skipWs=True, skipComment=False):
		self._reader = StringReader(string)
		
		self._skipWs = skipWs
		self._skipComment = skipComment
		
		self._state = self._DEFAULT
		self._verbatimState = self._DEFAULT
		
		self._eof = False
		self._tokenStack = []	# used to return a sequence of tokens after a verbatim ended
		
	def __iter__(self):
		return self
	
	def next(self):
		if self._eof:
			raise StopIteration
		
		# first empty the token stack
		if len(self._tokenStack):
			return self._tokenStack.pop()
		
		while True:
			try:
				char = self._reader.read()
				
				if self._state == self._DEFAULT:
					if char == "\\":
						self._state = self._BACKSLASH
						self._verbatimState = self._DEFAULT
						self._startOffset = self._reader.offset - 1
					
					elif char == "%":
						self._state = self._COMMENT
						self._verbatimState = self._DEFAULT
						self._startOffset = self._reader.offset - 1
						if not self._skipComment:
							self._text = []
					
					elif char in self._TERMINALS:
						if self._verbatimState == self._VERBATIM_BEGIN and char == "{":
							self._verbatimState = self._VERBATIM_BEGIN_CURLY
							
						elif self._verbatimState == self._VERBATIM_BEGIN_CURLY_ENVIRON and char == "}":
							# we have "\begin{verbatim}"
							self._verbatimState = self._DEFAULT
							self._state = self._VERBATIM
							self._text = []
							self._startOffset = self._reader.offset
							self._verbatimSequenceListener = StringListener("\\end{%s}" % self._verbatimEnviron)
							
						else:
							self._verbatimState = self._DEFAULT
							
						return Token(self._TERMINALS_MAP[char], self._reader.offset - 1)
					
					else:
						self._state = self._TEXT
						self._startOffset = self._reader.offset - 1
						self._text = [char]
					
				elif self._state == self._BACKSLASH:
					if char in self._SPECIAL or char.isspace():
						# this is a one-character-command, also whitespace is allowed
						self._state = self._DEFAULT
						return Token(Token.COMMAND, self._startOffset, "\\" + char)
					
					else:
						self._state = self._COMMAND
						self._verbListener = StringListener("verb", any_position=False)
						self._text = [char]
				
				elif self._state == self._COMMENT:
					if char == "\n":
						self._state = self._DEFAULT
						if not self._skipComment:
							return Token(Token.COMMENT, self._startOffset, "".join(self._text))
					
					else:
						if not self._skipComment:
							self._text.append(char)
				
				elif self._state == self._COMMAND:
					if char in self._SPECIAL or char.isspace():

						name = "".join(self._text)
						
						if name == "verb":
							self._state = self._VERB
							self._verbDelimiter = char
							self._startOffset = self._reader.offset - 1
							self._text = [char]
						
						elif name == "url": 	# we handle "\url" just like "\verb"
							self._state = self._VERB
							self._verbDelimiter = "}"
							self._startOffset = self._reader.offset - 1
							self._text = []
						
						else:
							self._state = self._DEFAULT
							self._reader.unread(char)
							
							if name == "begin":
								self._verbatimState = self._VERBATIM_BEGIN
							
							return Token(Token.COMMAND, self._startOffset, name)
					
					else:
						if self._verbListener.put(char):
							# we have "\verb"
							self._state = self._VERB_COMMAND
						else:
							self._text.append(char)
				
				elif self._state == self._TEXT:
					if char in self._SPECIAL:
						self._state = self._DEFAULT
						self._reader.unread(char)
						
						text = "".join(self._text)
						
						if self._skipWs and text.isspace():
							continue
						else:
							
							if self._verbatimState == self._VERBATIM_BEGIN_CURLY:
								# we have "\begin{" until now, handle verbatim environment
								
								if text in self._VERBATIM_ENVIRONS:
									self._verbatimEnviron = text
									self._verbatimState = self._VERBATIM_BEGIN_CURLY_ENVIRON
								
								else:
									self._verbatimState = self._DEFAULT
							
							return Token(Token.TEXT, self._startOffset, text)
					
					else:
						self._text.append(char)
				
				elif self._state == self._VERB:
					if char == self._verbDelimiter:
						self._state = self._DEFAULT
						
						return Token(Token.VERBATIM, self._startOffset, "".join(self._text) + char)
					
					else:
						self._text.append(char)
				
				elif self._state == self._VERBATIM:
					if self._verbatimSequenceListener.put(char):
						self._state = self._DEFAULT
						
						# TODO: calculate offsets
						self._tokenStack = [ Token(Token.END_CURLY, 0),
											 Token(Token.TEXT, 0, self._verbatimEnviron),
											 Token(Token.BEGIN_CURLY, 0),
											 Token(Token.COMMAND, 0, "end") ]
						
						text = "".join(self._text)
						text = text[5:]		# cut off "\end{"
						return Token(Token.VERBATIM, self._startOffset, text)
					else:
						self._text.append(char)
				
				elif self._state == self._VERB_COMMAND:
					# this char is the verb delimiter
					pass
						
			except StopIteration:
				self._eof = True
				
				# evaluate final state
				if self._state == self._BACKSLASH:
					return Token(Token.COMMAND, self._startOffset, "")
				
				elif self._state == self._COMMAND:
					return Token(Token.COMMAND, self._startOffset, "".join(self._text))
				
				elif self._state == self._TEXT:
					text = "".join(self._text)
					if not (self._skipWs and text.isspace()):
						return Token(Token.TEXT, self._startOffset, text)
				
				elif self._state == self._VERB:
					
					# TODO: the document is malformed in this case, so the lexer should be
					# able to produce issues, too
					#
					# TODO: return a VERBATIM token
					
					return Token(Token.TEXT, self._startOffset, "".join(self._text)) 
				
				raise StopIteration
				

class FatalParseException(Exception):
	"""
	This raised of the Parser faces a fatal error and cannot continue
	"""


class LaTeXParser(object):
	"""
	A tree parser building an object model of nodes
	"""
	
	# TODO: remove second parse method
	
	@caught
	def _parse(self, string, documentNode, file, issue_handler):
		"""
		@deprecated: use parse_string() and issues() instead
		"""
		self._file = file
		self._issue_handler = issue_handler
		
		# TODO: include comments into the model
		self.comments = []
		
		self._stack = [documentNode]
		
		callables = {
				Token.COMMAND : self.command, 
				Token.TEXT : self.text, 
				Token.BEGIN_CURLY : self.beginCurly,
				Token.END_CURLY : self.endCurly, 
				Token.BEGIN_SQUARE : self.beginSquare, 
				Token.END_SQUARE : self.endSquare,
				Token.COMMENT : self.comment, 
				Token.VERBATIM : self.verbatim }
		
		try:
			for token in Lexer(string):
				callables[token.type].__call__(token.value, token.offset)
		except FatalParseException:
			return self._issues
		
		# check stack remainder
		for node in self._stack:
			if node.type == Node.MANDATORY_ARGUMENT or node.type == Node.EMBRACED:
				self._issue_handler.issue(Issue("Unclosed {", node.start, node.start + 1, self._file, Issue.SEVERITY_ERROR))
			elif node.type == Node.OPTIONAL_ARGUMENT:
				self._issue_handler.issue(Issue("Unclosed [", node.start, node.start + 1, self._file, Issue.SEVERITY_ERROR))
	
	def parse(self, string, file, issue_handler):
		"""
		@param string: LaTeX source
		@param from_filename: filename from where the source is read (this is used to tag
				parts of the model)
				
		@rtype: Document
		"""
		document_node = Document(file)
		self._parse(string, document_node, file, issue_handler)
		
		return document_node
	
	# TODO: rename methods from "command()" to "_on_command()"
	
	def command(self, value, offset):
		top = self._stack[-1]
		
		if top.type == Node.DOCUMENT \
				or top.type == Node.MANDATORY_ARGUMENT \
				or top.type == Node.OPTIONAL_ARGUMENT \
				or top.type == Node.EMBRACED:
			node = LocalizedNode(Node.COMMAND, offset, offset + len(value) + 1, value)
			top.append(node)
			self._stack.append(node)
			
		elif top.type == Node.COMMAND \
				or top.type == Node.TEXT:
			try:
				self._stack.pop()
				self.command(value, offset)
			except IndexError:
				self._issue_handler.issue(Issue("Undefined Parse Error", offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
	
	def text(self, value, offset):
		top = self._stack[-1]

		if top.type == Node.DOCUMENT \
				or top.type == Node.MANDATORY_ARGUMENT \
				or top.type == Node.OPTIONAL_ARGUMENT \
				or top.type == Node.EMBRACED:
			node = LocalizedNode(Node.TEXT, offset, offset + len(value), value)
			top.append(node)
			self._stack.append(node)
			
		elif top.type == Node.COMMAND:
			self._stack.pop()
			self.text(value, offset)
			
		elif top.type == Node.TEXT:
			try:
				self._stack.pop()
				self.text(value, offset)
			except IndexError:
				self._issue_handler.issue(Issue("Undefined Parse Error", offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
		else:
			# TODO: possible?
			self._issue_handler.issue(Issue("Unexpected TEXT token with %s on stack" % top.type, offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
	
	def beginCurly(self, value, offset):
		top = self._stack[-1]
		
		if top.type == Node.COMMAND:
			node = LocalizedNode(Node.MANDATORY_ARGUMENT, offset, offset + 1)
			top.append(node)
			self._stack.append(node)
		
		elif top.type == Node.DOCUMENT \
				or top.type == Node.MANDATORY_ARGUMENT \
				or top.type == Node.OPTIONAL_ARGUMENT \
				or top.type == Node.EMBRACED:
			node = LocalizedNode(Node.EMBRACED, offset, offset + 1)
			top.append(node)
			self._stack.append(node)
		
		elif top.type == Node.TEXT:
			try:
				self._stack.pop()
				self.beginCurly(value, offset)
			except IndexError:
				self._issue_handler.issue(Issue("Undefined Parse Error", offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
		else:
			# TODO: possible?
			self._issue_handler.issue(Issue("Unexpected BEGIN_CURLY token with %s on stack" % top.type, offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
	
	def endCurly(self, value, offset):
		try:
			# pop from stack until MANDATORY_ARGUMENT or EMBRACED
			while True:
				top = self._stack[-1]
				if top.type == Node.MANDATORY_ARGUMENT or top.type == Node.EMBRACED:
					node = self._stack.pop()
					break
				self._stack.pop()
				
			# set end offset of MANDATORY_ARGUMENT or EMBRACED
			node.end = offset + 1
		except IndexError:
			self._issue_handler.issue(Issue("Encountered <b>}</b> without </b>{</b>", offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
			# we cannot continue after that
			raise FatalParseException
	
	def beginSquare(self, value, offset):
		top = self._stack[-1]
		if top.type == Node.COMMAND:
			node = LocalizedNode(Node.OPTIONAL_ARGUMENT, offset, offset + 1)
			top.append(node)
			self._stack.append(node)
		
		elif top.type == Node.TEXT:
			top.value += "["
		
		elif top.type == Node.MANDATORY_ARGUMENT:
			node = LocalizedNode(Node.TEXT, offset, offset + 1, "[")
			top.append(node)
			self._stack.append(node)
		
		else:
			self._issue_handler.issue(Issue("Unexpected BEGIN_SQUARE token with %s on stack" % top.type, offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
	
	def endSquare(self, value, offset):
		try:
			node = [node for node in self._stack if node.type == Node.OPTIONAL_ARGUMENT][-1]
			
			# open optional argument found 
			# this square closes it, so pop stack until there
			
			while self._stack[-1].type != Node.OPTIONAL_ARGUMENT:
				self._stack.pop()
			node = self._stack.pop()
			node.end = offset + 1
			
		except IndexError:
			# no open optional argument, so this "]" is TEXT
			
			top = self._stack[-1]
			if top.type == Node.TEXT:
				top.value += "]"
				
			elif top.type == Node.COMMAND:
				try:
					self._stack.pop()
					self.endSquare(value, offset)
				except IndexError:
					self._issue_handler.issue(Issue("Undefined Parse Error", offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
			
			elif top.type == Node.MANDATORY_ARGUMENT or top.type == Node.DOCUMENT or top.type == Node.OPTIONAL_ARGUMENT:
				node = LocalizedNode(Node.TEXT, offset, offset + 1, "]")
				top.append(node)
				self._stack.append(node)
			
			else:
				self._issue_handler.issue(Issue("Unexpected END_SQUARE token with %s on stack and no optional argument" % top.type, offset, offset + 1, self._file, Issue.SEVERITY_ERROR))
	
	def comment(self, value, offset):
		# TODO: this should go to the model
		
		self.comments.append([value, offset])
		
	def verbatim(self, value, offset):
		pass


class PrefixParser(object):
	"""
	A light-weight LaTeX parser used for parsing just a prefix in
	the code completion.
	
	The differences between the full parser and this one include:
	 * we don't collect issues (we just raise an exception)
	 * we don't store node offsets
	 * we indicate whether the last argument is closed or not
	"""
	
	# TODO: use another Lexer here that doesn't count offsets (faster)
	
	def parse(self, string, documentNode):
		
		self._stack = [documentNode]
		
		callables = {Token.COMMAND : self.command, Token.TEXT : self.text, Token.BEGIN_CURLY : self.beginCurly,
				Token.END_CURLY : self.endCurly, Token.BEGIN_SQUARE : self.beginSquare, Token.END_SQUARE : self.endSquare,
				Token.COMMENT : self.comment, Token.VERBATIM : self.verbatim}
		
		try:
			for token in Lexer(string, skipWs=False, skipComment=False):
				callables[token.type].__call__(token.value)
		except FatalParseException:
			return
		
	def command(self, value):
		top = self._stack[-1]
		
		if top.type == Node.DOCUMENT \
				or top.type == Node.MANDATORY_ARGUMENT \
				or top.type == Node.OPTIONAL_ARGUMENT \
				or top.type == Node.EMBRACED:
			node = Node(Node.COMMAND, value)
			top.append(node)
			self._stack.append(node)
			
		elif top.type == Node.COMMAND \
				or top.type == Node.TEXT:
			try:
				self._stack.pop()
				self.command(value)
			except IndexError:
				raise FatalParseException
	
	def text(self, value):
		top = self._stack[-1]

		if top.type == Node.DOCUMENT \
				or top.type == Node.MANDATORY_ARGUMENT \
				or top.type == Node.OPTIONAL_ARGUMENT \
				or top.type == Node.EMBRACED:
			node = Node(Node.TEXT, value)
			top.append(node)
			self._stack.append(node)
			
		elif top.type == Node.COMMAND:
			self._stack.pop()
			self.text(value)
			
		elif top.type == Node.TEXT:
			try:
				self._stack.pop()
				self.text(value)
			except IndexError:
				raise FatalParseException
		else:
			# TODO: possible?
			raise FatalParseException
	
	def beginCurly(self, value):
		top = self._stack[-1]
		
		if top.type == Node.COMMAND:
			node = Node(Node.MANDATORY_ARGUMENT)
			top.append(node)
			self._stack.append(node)
		
		elif top.type == Node.DOCUMENT \
				or top.type == Node.MANDATORY_ARGUMENT \
				or top.type == Node.OPTIONAL_ARGUMENT \
				or top.type == Node.EMBRACED:
			node = Node(Node.EMBRACED)
			top.append(node)
			self._stack.append(node)
		
		elif top.type == Node.TEXT:
			try:
				self._stack.pop()
				self.beginCurly(value)
			except IndexError:
				raise FatalParseException
		else:
			# TODO: possible?
			raise FatalParseException
	
	def endCurly(self, value):
		try:
			# pop from stack until MANDATORY_ARGUMENT or EMBRACED
			while True:
				top = self._stack[-1]
				if top.type == Node.MANDATORY_ARGUMENT or top.type == Node.EMBRACED:
					node = self._stack.pop()
					break
				self._stack.pop()
				
			node.closed = True
		except IndexError:
			raise FatalParseException
	
	def beginSquare(self, value):
		top = self._stack[-1]
		if top.type == Node.COMMAND:
			node = Node(Node.OPTIONAL_ARGUMENT)
			top.append(node)
			self._stack.append(node)
		
		elif top.type == Node.TEXT:
			top.value += "["
		
		elif top.type == Node.MANDATORY_ARGUMENT:
			node = Node(Node.TEXT, "[")
			top.append(node)
			self._stack.append(node)
		
		else:
			raise FatalParseException
	
	def endSquare(self, value):
		try:
			# check whether an optional argument is open at all
			#
			# for this we address the top OPTIONAL_ARGUMENT node on the stack, if it doesn't
			# exist an IndexError is thrown
			node = [node for node in self._stack if node.type == Node.OPTIONAL_ARGUMENT][-1]
			
			# open optional argument found 
			# this square closes it, so pop stack until there
			
			while self._stack[-1].type != Node.OPTIONAL_ARGUMENT:
				self._stack.pop()
			node = self._stack.pop()
			node.closed = True
			
		except IndexError:
			# no open optional argument, so this "]" is TEXT
			
			top = self._stack[-1]
			if top.type == Node.TEXT:
				top.value += "]"
				
			elif top.type == Node.COMMAND:
				try:
					self._stack.pop()
					self.endSquare(value)
				except IndexError:
					raise FatalParseException
			
			elif top.type == Node.MANDATORY_ARGUMENT or top.type == Node.DOCUMENT or top.type == Node.OPTIONAL_ARGUMENT:
				node = Node(Node.TEXT, "]")
				top.append(node)
				self._stack.append(node)
			
			else:
				raise FatalParseException
	
	def comment(self, value):
		pass
		
	def verbatim(self, value):
		pass


# TODO: we should extract tasks when calling comment() and add them as an Issue


class TaskExtractor(object):
	"""
	This extracts TODO and FIXME comments and creates Issue objects of
	type TASK
	"""
	
	# TODO: this should walk through a document model
	
	_PATTERN = compile("(TODO|FIXME)\w?\:?(?P<text>.*)")
	
	def extract(self, comments):
		issues = []
		
		for value, offset in comments:
			match = self._PATTERN.search(value)
			if match:
				text = match.group("text").strip()
				
				# TODO: +1 ?
				issues.append(Issue("<i>%s</i>" % text, Issue.TASK, offset + match.start(), offset + match.end() + 1))
		
		return issues


class Validator(object):
	"""
	This validates the following aspects by walking the document model 
	and using the outline:
	
	 * unused labels
	 * unclosed environments, also "\[" and "\]"
	"""
	
	def __init__(self):
		self._environment = Environment()
	
	def validate(self, documentNode, outline, baseDir=None):
		self._outline = outline
		
		# prepare structures
		
		self._labels = {}
		for label in outline.labels:
			self._labels[label.value] = [label, False]	
		
		self._issues = []
		self._envionStack = []
		
		self._checkRefs = bool(baseDir)
		self._baseDir = baseDir
		
		self._run(documentNode, documentNode.value)
		
		# evaluate structures
		
		for label, used in self._labels.values():
			if not used:
				self._issue_handler.issue(Issue("Label <b>%s</b> is never used" % label.value, Issue.VALIDATE_WARNING, 
												label.start, label.end, documentNode.value))
		
		return self._issues
		
	def _run(self, parentNode, filename):
		for node in parentNode:
			recurse = True
			if node.type == Node.DOCUMENT:
				filename = node.value
				
			elif node.type == Node.COMMAND:
				if node.value == "begin":
					# push environment on stack
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					self._envionStack.append((environ, node.start, node.lastEnd))
					
				elif node.value == "end":
					# check environment
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					try:
						tEnviron, tStart, tEnd = self._envionStack.pop()
						if tEnviron != environ:
							self._issue_handler.issue(Issue("Environment <b>%s</b> has to be ended before <b>%s</b>" % (tEnviron, environ), 
													Issue.VALIDATE_ERROR, node.start, node.lastEnd, filename))
					except IndexError:
						self._issue_handler.issue(Issue("Environment <b>%s</b> has no beginning" % environ, Issue.VALIDATE_ERROR, 
												node.start, node.lastEnd, filename))
				
				elif node.value == "[":
					# push eqn env on stack
					self._envionStack.append(("[", node.start, node.end))
				
				elif node.value == "]":
					try:
						tEnviron, tStart, tEnd = self._envionStack.pop()
						if tEnviron != "[":
							self._issue_handler.issue(Issue("Environment <b>%s</b> has to be ended before <b>]</b>" % tEnviron, 
													Issue.VALIDATE_ERROR, node.start, node.end, filename))
					except IndexError:
						self._issue_handler.issue(Issue("Environment <b>%s</b> has no beginning" % environ, Issue.VALIDATE_ERROR, 
												node.start, node.end, filename))
				
				elif node.value == "ref" or node.value == "eqref" or node.value == "pageref":
					# mark label as used
					label = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					try:
						self._labels[label][1] = True
					except KeyError:
						self._issue_handler.issue(Issue("Label <b>%s</b> has not been defined" % label, Issue.VALIDATE_ERROR, 
												node.start, node.lastEnd, filename))
				
				elif self._checkRefs and (node.value == "includegraphics"):
					# check referenced image file
					target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					if target[0] == "/":
						filename = target
					else:
						filename = "%s/%s" % (self._baseDir, target)
					
					if not exists(filename):
						self._issue_handler.issue(Issue("Image <b>%s</b> could not be found" % target, Issue.VALIDATE_WARNING, 
												node.start, node.lastEnd, filename))
				
				elif self._checkRefs and (node.value == "include" or node.value == "input"):
					# check referenced tex file
					target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					if len(target):
						if target[0] == "/":
							filename = "%s.tex" % target
						else:
							filename = "%s/%s.tex" % (self._baseDir, target)
						
						if not exists(filename):
							self._issue_handler.issue(Issue("Document <b>%s</b> could not be found" % target, Issue.VALIDATE_WARNING, 
													node.start, node.lastEnd, filename))
				
				elif self._checkRefs and node.value == "bibliography":
					# check referenced BibTeX file(s)
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					for target in value.split(","):
						if target[0] == "/":
							filename = target + ".bib"
						else:
							filename = "%s/%s.bib" % (self._baseDir, target)
						
						if not exists(filename):
							self._issue_handler.issue(Issue("Bibliography <b>%s</b> could not be found" % filename, Issue.VALIDATE_WARNING, 
													node.start, node.lastEnd, filename))
				
				elif node.value == "newcommand":
					# don't validate in newcommand definitions
					recurse = False
				
				elif node.value == "bibliographystyle":
					# check if style exists
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					
					if not self._environment.fileExists("%s.bst" % value):
						self._issue_handler.issue(Issue("Bibliography style <b>%s</b> could not be found" % value, Issue.VALIDATE_WARNING, 
													node.start, node.lastEnd, filename))
				
				
			if recurse:
				self._run(node, filename)


from ..base import File


class LaTeXReferenceExpander(object):
	"""
	This expands '\include' and '\input' commands by parsing the referenced child
	documents. The resulting trees may be attached to the parent tree.
	"""
	
	# TODO: embed this into parser so that we don't need to walk the document again
	
	_log = getLogger("ReferenceExpander")
	
	def expand(self, documentNode, master_file, issue_handler):
		#self._baseDir = baseDir
		self._master_file = master_file
		self._issue_handler = issue_handler
		self._parser = LaTeXParser()
		self._expand(documentNode)
		
	def _expand(self, parentNode):
		"""
		Recursively walk all nodes in the document model and check for \input or \include
		commands. Extract the filename from the command and parse the referenced file.
		Attach its model as a DOCUMENT node to the master model and hold its filename as
		the value of that DOCUMENT node, so that the Validator may differ between issue
		sources.
		"""
		for node in parentNode:
			if node.type == Node.COMMAND and (node.value == "input" or node.value == "include"):
				try:
					# build child filename
					target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					if target[0] == "/":
						filename = "%s.tex" % target
					else:
						filename = "%s/%s.tex" % (self._master_file.dirname, target)
					
					self._log.debug("Expanding %s" % filename)
					
					# parse child
					try:
						fragment = self._parser.parse(open(filename).read(), File(filename), self._issue_handler)
						node.append(fragment)
					except IOError, e:
						self._log.error("Referenced file not found: %s" % filename)
				except IndexError:
					self._log.error("Malformed reference command at %s" % node.start)
			
			self._expand(node)


		