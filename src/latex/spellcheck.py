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

from logging import getLogger

from ..preferences import Preferences, IPreferencesMonitor
from parser import Node


class IMisspelledWordHandler(object):
	"""
	
	"""
	def on_misspelled_word(self, word, position):
		"""
		A misspelled word has been recognized
		
		@param word: the misspelled word
		@param position: the start offset
		"""


class SpellCheckerBackend(IPreferencesMonitor):
	
	_log = getLogger("SpellCheckerBackend")
	
	def __init__(self):
		self._initialized = False
		self._preferences = Preferences()
		self._preferences.register_monitor(self)
	
	def _on_value_changed(self, key, new_value):
		# reset if the dictionary has changed
		if key == "SpellCheckDictionary":
			self._initialized = False
	
	def _initialize(self):
		"""
		@raise ImportError: if pyenchant is not installed
		@raise enchant.Error: if no default dictionary exists
		"""
		import enchant
		import enchant.checker
		import enchant.tokenize
	
		language = str(self._preferences.get("SpellCheckDictionary", ""))
		if len(language) > 0 and enchant.dict_exists(language):
			self._dictionary = enchant.Dict(language)
		else:
			#
			# try to use default language (may raise enchant.Error)
			#
			self._dictionary = enchant.Dict()
			language = self._dictionary.tag
			
		self._log.debug("Using dictionary '%s'" % language)
		self._checker = enchant.checker.SpellChecker(language, filters=[enchant.tokenize.EmailFilter, enchant.tokenize.URLFilter])
	
		self._initialized = True
	
	def check(self, text, handler):
		"""
		@param text: the text to be checked
		@param handler: an IErrorHandler
		
		@raise ImportError: if pyenchant is not installed
		"""
		if not self._initialized: self._initialize()
		
		self._checker.set_text(text)
		for error in self._checker:
			handler.on_error(error.word, error.wordpos)
	
	def find_suggestions(self, word):
		"""
		@param word: 
		@return: a list of suggested words
		"""
		if not self._initialized: self._initialize()
		
		return self._dictionary.suggest(word)
	
	@property
	def languages(self):
		"""
		@raise ImportError: if pyenchant is not installed
		"""
		import enchant
		
		return enchant.Broker().list_languages()
	
	def add_word(self, word):
		raise NotImplementedError


class IErrorHandler(object):
	def on_error(self, word, position):
		raise NotImplementedError

	
class SpellChecker(IErrorHandler):
	"""
	This walks the LaTeX model and calls the spell checking backend at
	every TEXT node.
	
	This is used by the LaTeXEditor
	"""
	
	_log = getLogger("SpellChecker")
	
	def __init__(self):
		self._backend = SpellCheckerBackend()
	
	def run(self, document, file, handler):
		"""
		Run the spell checker
		
		@param document: a LaTeX document model
		@param handler: an IMisspelledWordHandler
		
		@raise ImportError: if pyenchant is not installed
		"""
		self._file = file
		self._handler = handler
		self.__run(document)
	
	def __run(self, parent_node):
		"""
		@raise ImportError: if pyenchant is not installed
		"""
		for node in parent_node:
			if node.type == Node.TEXT and node.file == self._file:
				text = node.value.decode("utf8")
				self._relative_offset = node.start
				self._backend.check(text, self)
			
			self.__run(node)
	
	def find_suggestions(self, word):
		return self._backend.find_suggestions(word)
	
	def on_error(self, word, position):
		# see IErrorHandler.on_error
		self._handler.on_misspelled_word(word, self._relative_offset + position)


