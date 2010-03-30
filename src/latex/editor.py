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
latex.editor
"""

BENCHMARK = True

from ..typecheck import accepts, returns

import gtk
import gtk.gdk
from logging import getLogger

if BENCHMARK: import time

from ..base import Editor, File
from completion import LaTeXCompletionHandler
from ..snippets.completion import SnippetCompletionHandler
from ..issues import Issue, IIssueHandler
from ..util import verbose, open_error
from copy import deepcopy

from parser import LaTeXParser
from expander import LaTeXReferenceExpander
from outline import LaTeXOutlineGenerator
from validator import LaTeXValidator

from dialogs import ChooseMasterDialog

from . import LaTeXSource, PropertyFile
from ..preferences import Preferences, IPreferencesMonitor

from spellcheck import SpellChecker, IMisspelledWordHandler


class LaTeXEditor(Editor, IIssueHandler, IMisspelledWordHandler, IPreferencesMonitor):
	
	_log = getLogger("LaTeXEditor")
	
	#extensions = [".tex"]
	extensions = Preferences().get("LatexExtensions", ".tex").split(" ")
	
	dnd_extensions = [".png", ".pdf", ".bib", ".tex"]
	
	@property
	def completion_handlers(self):
		self.__latex_completion_handler = LaTeXCompletionHandler()
		self.__snippet_completion_handler = SnippetCompletionHandler()
		
		return [ self.__latex_completion_handler, self.__snippet_completion_handler ]
	
	def init(self, file, context):
		"""
		@param file: base.File
		@param content: base.WindowContext
		"""
		self._log.debug("init(%s)" % file)
		
		self._file = file
		self._context = context
		
		self._preferences = Preferences()
		self._preferences.register_monitor(self)	# listen to 'Show...InOutline' settings
		
		self.register_marker_type("latex-spell", self._preferences.get("SpellingBackgroundColor"), anonymous=False)
		self.register_marker_type("latex-error", self._preferences.get("ErrorBackgroundColor"))
		self.register_marker_type("latex-warning", self._preferences.get("WarningBackgroundColor"))
		
		self._issue_view = context.find_view(self, "IssueView")
		self._outline_view = context.find_view(self, "LaTeXOutlineView")

		self.latex_preview = None
		
		self._parser = LaTeXParser()
		self._outline_generator = LaTeXOutlineGenerator()
		self._validator = LaTeXValidator()
		
		self._connect_outline_to_editor = True	# TODO: read from config
		self._document_dirty = True
		
		# if the document is no master we display an info message on the packages to
		# include - _ensured_packages holds the already mentioned packages to not
		# annoy the user
		self._ensured_packages = []
		
		# spell checking
		self.__spell_checker = SpellChecker()
		
		#
		# initially parse
		#
		self._change_reference = self.initial_timestamp
		
		self.__parse()
		self.__update_neighbors()
	
	def _on_value_changed(self, key, new_value):
		# see preferences.IPreferencesMonitor._on_value_changed
		
		if key in ["ShowLabelsInOutline", "ShowTablesInOutline", "ShowGraphicsInOutline"]:
			# regenerate outline model
			if self._document_is_master:
				self._outline = self._outline_generator.generate(self._document, self)
				self._outline_view.set_outline(self._outline)
			else:
				# FIXME: self._document contains the full model of child and master
				# so we may not use it for regenerating the outline here
				self.__parse()
	
	def drag_drop_received(self, files):
		# see base.Editor.drag_drop_received
		
		# TODO: we need to insert the source at the drop location - so pass it here
		
		self._log.debug("drag_drop: %s" % files)
		
#		if len(files) == 1:
#			file = files[0]
#			self._log.debug("Got one file: %s, extension: %s" % (file.path, file.extension))
#			if file.extension == ".png":
#				self._log.debug("PNG image - including...")
#				source = "\\includegraphics{%s}" % file.path
#				self.insert(source)
	
	def insert(self, source):
		# see base.Editor.insert
		
		if type(source) is LaTeXSource:
			if source.packages and len(source.packages) > 0:
				self.ensure_packages(source.packages)
			
			Editor.insert(self, source.source)
		else:
			Editor.insert(self, source)
	
	POSITION_PACKAGES, POSITION_BIBLIOGRAPHY = 1, 2
	
	def insert_at_position(self, source, position):
		"""
		Insert source at a certain position in the LaTeX document:
		
		 * POSITION_PACKAGES: after the last \usepackage statement
		 * POSITION_BIBLIOGRAPHY: before \end{document}
		
		@param source: a LaTeXSource object
		@param position: POSITION_PACKAGES | POSITION_BIBLIOGRAPHY
		"""
		
		if position == self.POSITION_BIBLIOGRAPHY:
			offset = self._document.end_of_document
			Editor.insert_at_offset(self, offset, source, True)
		elif position == self.POSITION_PACKAGES:
			offset = self._document.end_of_packages
			Editor.insert_at_offset(self, offset, source, False)
		else:
			raise NotImplementedError
	
	def ensure_packages(self, packages):
		"""
		Ensure that certain packages are included
		
		@param packages: a list of package names
		"""
		self.__parse()	# ensure up-to-date document model
		
		if not self._document_is_master:
			self._log.debug("ensure_packages: document is not a master")
			
			# find the packages that haven't already been mentioned
			info_packages = [p for p in packages if not p in self._ensured_packages]
			
			if len(info_packages) > 0:
				# generate markup
				li_tags = "\n".join([" • <tt>%s</tt>" % p for p in info_packages])
				
				from ..util import open_info
				open_info("LaTeX Package Required", 
						"Please make sure that the following packages are included in the master document per <tt>\\usepackage</tt>: \n\n%s" % li_tags)
				
				# extend the already mentioned packages
				self._ensured_packages.extend(info_packages)
			
			return
		
		# find missing packages
		present_package_names = [p.value for p in self._outline.packages]
		package_names = [p for p in packages if not p in present_package_names]
		
		# insert the necessary \usepackage commands
		if len(package_names) > 0:
			source = "\n" + "\n".join(["\\usepackage{%s}" % n for n in package_names])
			self.insert_at_position(source, self.POSITION_PACKAGES)
	
	def on_save(self):
		"""
		The file has been saved
		
		Update models
		"""
		
#		from multiprocessing import Process
#		
#		p_parse = Process(target=self.__parse)
#		p_parse.start()
		
		self.__parse()
		
	def __update_neighbors(self):
		"""
		Find all files in the working directory that are relevant for LaTeX, e.g.
		other *.tex files or images.
		"""
		
		# TODO: this is only needed to feed the LaTeXCompletionHandler. So maybe it should
		# know the edited file and the Editor should call an update() method of the handler
		# when the file is saved.
		
		tex_files = self._file.find_neighbors(".tex")
		bib_files = self._file.find_neighbors(".bib")
		
		graphic_files = []
		for extension in [".ps", ".pdf", ".png", ".jpg", ".eps"]:
			graphic_files.extend(self._file.find_neighbors(extension))
		
		self.__latex_completion_handler.set_neighbors(tex_files, bib_files, graphic_files)
	
	#@verbose
	def __parse(self):
		"""
		Ensure that the document model is up-to-date
		"""
		if self.content_changed(self._change_reference):
			# content has changed so document model may be dirty
			self._change_reference = self.current_timestamp
			
			self._log.debug("Parsing document...")
			
			content = self.content
			
			# reset highlight
			self.remove_markers("latex-error")
			self.remove_markers("latex-warning")
			
			# reset issues
			self._issue_view.clear()
			
			if BENCHMARK: t = time.clock()
			
			# parse document
			self._document = self._parser.parse(content, self._file, self)
			
			if BENCHMARK: self._log.info("LaTeXParser.parse: %f" % (time.clock() - t))
			
			# create a copy that won't be expanded (e.g. for spell check)
			#self._local_document = deepcopy(self._document)
			
			self._log.debug("Parsed %s bytes of content" % len(content))
			
			# FIXME: the LaTeXChooseMasterAction enabled state has to be updated on tab change, too!
			
			if self._document.is_master:
				
				self._context.set_action_enabled("LaTeXChooseMasterAction", False)
				self._document_is_master = True
				
				# expand child documents
				expander = LaTeXReferenceExpander()
				expander.expand(self._document, self._file, self, self.charset)
				
				# generate outline from the expanded model
				self._outline = self._outline_generator.generate(self._document, self)
				
				# pass to view
				self._outline_view.set_outline(self._outline)

				# validate
				self._validator.validate(self._document, self._outline, self)
			else:
				self._log.debug("Document is not a master")
				
				self._context.set_action_enabled("LaTeXChooseMasterAction", True)
				self._document_is_master = False
				
				# the outline used by the outline view has to be created only from the child model
				# otherwise we see the outline of the master and get wrong offsets
				self._outline = self._outline_generator.generate(self._document, self)
				self._outline_view.set_outline(self._outline)
				
				# find master
				master_file = self.__master_file
				
				if master_file is None:
					return
				
				# parse master
				master_content = open(master_file.path).read()
				self._document = self._parser.parse(master_content, master_file, self)
				
				# expand its child documents
				expander = LaTeXReferenceExpander()
				expander.expand(self._document, master_file, self, self.charset)
				
				# create another outline of the expanded master model to make elements
				# from the master available (labels, colors, BibTeX files etc.)
				self._outline = self._outline_generator.generate(self._document, self)

				# validate
				self._validator.validate(self._document, self._outline, self)
			
			# pass outline to completion
			self.__latex_completion_handler.set_outline(self._outline)
			
			# pass neighbor files to completion
			self.__update_neighbors()
			
			self._log.debug("Parsing finished")
			
			#print self._document.xml
	
	@property
	@returns(File)
	def __master_file(self):
		"""
		Find the LaTeX master of this child
		
		@return: base.File
		"""
		# TODO: cache result
		
		property_file = PropertyFile(self._file)
		try:
			#return File(property_file["MasterFilename"])
			
			path = property_file["MasterFilename"]
			# the property file may contain absolute and relative paths
			# because we switched in 0.2rc2
			if File.is_absolute(path):
				self._log.debug("Path is absolute")
				return File(path)
			else:
				self._log.debug("Path is relative")
				return File.create_from_relative_path(path, self._file.dirname)
		except KeyError:		# master filename not found
			# ask user
			master_filename = ChooseMasterDialog().run(self._file.dirname)
			if master_filename:
				# relativize the master filename
				master_filename = File(master_filename).relativize(self._file.dirname, True)
				
				property_file["MasterFilename"] = master_filename
				property_file.save()
				return File(master_filename)
			else:
				# no master file chosen
				return None
	
	def issue(self, issue):
		# see IIssueHandler.issue
		
		local = (issue.file == self._file)
		
		self._issue_view.append_issue(issue, local)
		
		if issue.file == self._file:
			if issue.severity == Issue.SEVERITY_ERROR:
				self.create_marker("latex-error", issue.start, issue.end)
			elif issue.severity == Issue.SEVERITY_WARNING:
				self.create_marker("latex-warning", issue.start, issue.end)
	
	#
	# spell checking begin
	#
	# TODO: put this in a SpellCheckDelegate or so
	#
	
	def spell_check(self):
		"""
		Run a spell check on the file
		
		@raise ImportError: if pyenchant is not installed
		"""
		self.remove_markers("latex-spell")
		self.__word_markers = {}
		
		#
		# FIXME: it makes no sense to pass _document here because it contains
		# the expanded model of the document. We must keep the the not expanded
		# one, too.
		#
		try:
			self.__spell_checker.run(self._document, self.edited_file, self)
		except ImportError:
			open_error("Enchant is missing", "The enchant library and its Python bindings (package is propably called pyenchant) are needed for spell checking but could not be found")
			
	def on_misspelled_word(self, word, position):
		# see IMisspelledWordHandler.on_misspelled_word
		marker = self.create_marker("latex-spell", position, position + len(word))
		self.__word_markers[marker.id] = word
	
	def on_marker_activated(self, marker, event):
		"""
		A marker has been activated
		"""
		#self._log.debug("activate_marker(%s, %s)" % (marker, event))
		
		if marker.type == "latex-spell":
			word = self.__word_markers[marker.id]
			suggestions = self.__spell_checker.find_suggestions(word)
			
			self._log.debug(str(suggestions))
			
			# build and show the context menu
			menu = self.__get_suggestions_menu(word, suggestions, marker)
			menu.popup(None, None, None, event.button, event.time)
			
			# swallow the signal so that the original context menu
			# isn't shown
			return True
			
	def __get_suggestions_menu(self, word, suggestions, marker):
		"""
		Return the context menu for spell check suggestions
		
		@param word: the misspelled word
		@param suggestions: a list of suggested words
		@param marker: the activated Marker
		"""
		suggestions_menu = gtk.Menu()
		
		suggestions_menu.add(gtk.SeparatorMenuItem())
		
		item_add = gtk.ImageMenuItem(gtk.STOCK_ADD)
		item_add.connect("activate", self.__on_add_word_activated, marker, word)
		suggestions_menu.add(item_add)
		
		suggestions_menu.add(gtk.SeparatorMenuItem())
		
		item_abort = gtk.ImageMenuItem(gtk.STOCK_CANCEL)
		item_abort.connect("activate", self.__on_abort_spell_check_activated)
		suggestions_menu.add(item_abort)
		
		suggestions_menu.show_all()
		
		# add suggestions
		suggestions.reverse()	# we insert in reverse order, so reverse before
		
		for suggestion in suggestions:
			if suggestion.user_defined:
				item = gtk.ImageMenuItem(suggestion.word)
				item.set_image(gtk.image_new_from_stock(gtk.STOCK_FLOPPY, gtk.ICON_SIZE_MENU))
			else:
				item = gtk.MenuItem(suggestion.word)
				
			item.connect("activate", self.__on_suggestion_activated, suggestion, marker)
			suggestions_menu.insert(item, 0)
			item.show()
		
		return suggestions_menu
	
	def __on_suggestion_activated(self, menu_item, suggestion, marker):
		"""
		A suggestion from the context menu has been activated
		
		@param menu_item: the activated MenuItem
		@param suggestion: the word
		"""
		self.replace_marker_content(marker, suggestion.word)
	
	def __on_abort_spell_check_activated(self, menu_item):
		"""
		"""
		self.remove_markers("latex-spell")
	
	def __on_add_word_activated(self, menu_item, marker, word):
		"""
		Add a word to the dictionary
		
		@param marker: the marker for the word
		@param word: the checked word
		"""
		self.__spell_checker.add_word(word)
		self.remove_marker(marker)
	
	#
	# spell checking end
	#
	
	def on_cursor_moved(self, offset):
		"""
		The cursor has moved
		"""
		if self._preferences.get_bool("ConnectOutlineToEditor", True):
			self._outline_view.select_path_by_offset(offset)
		
	@property
	def file(self):
		# overrides Editor.file
		
		# we may not call self._document.is_master because _document is always
		# replaced by the master model
		if self._document_is_master:
			return self._file
		else:
			return self.__master_file
	
	@property
	def edited_file(self):
		"""
		Always returns the really edited file instead of the master
		
		This is called by the outline view to identify foreign nodes
		"""
		return self._file

	def destroy(self):
		self._preferences.remove_monitor(self)
		
		Editor.destroy(self)
	