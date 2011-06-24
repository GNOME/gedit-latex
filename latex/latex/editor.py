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
latex.editor
"""

BENCHMARK = True

#from ..typecheck import accepts, returns

from gi.repository import Gtk
from gi.repository import Gdk
from logging import getLogger

if BENCHMARK: import time

from ..base import Editor, File
from completion import LaTeXCompletionHandler
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


class LaTeXEditor(Editor, IIssueHandler, IPreferencesMonitor):
	
	_log = getLogger("LaTeXEditor")
	
	#extensions = [".tex"]
	extensions = Preferences().get("LatexExtensions", ".tex").split(" ")
	
	dnd_extensions = [".png", ".pdf", ".bib", ".tex"]
	
	@property
	def completion_handlers(self):
		self.__latex_completion_handler = LaTeXCompletionHandler()
		
		return [ self.__latex_completion_handler ]
	
	def init(self, file, context):
		"""
		@param file: base.File
		@param context: base.WindowContext
		"""
		self._log.debug("init(%s)" % file)
		
		self._file = file
		self._context = context
		
		self._preferences = Preferences()
		self._preferences.register_monitor(self)	# listen to 'Show...InOutline' settings

		self.register_marker_type("latex-error", self._preferences.get("ErrorBackgroundColor"))
		self.register_marker_type("latex-warning", self._preferences.get("WarningBackgroundColor"))
		
		self._issue_view = context.find_view(self, "IssueView")
		self._outline_view = context.find_view(self, "LaTeXOutlineView")

		self._parser = LaTeXParser()
		self._outline_generator = LaTeXOutlineGenerator()
		self._validator = LaTeXValidator()
		self._document = None
		
		self._document_dirty = True
		
		# if the document is no master we display an info message on the packages to
		# include - _ensured_packages holds the already mentioned packages to not
		# annoy the user
		self._ensured_packages = []
		
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
		elif key == "ShowLatexToolbar":
			show_toolbar = self._preferences.get_bool("ShowLatexToolbar", True)
			if show_toolbar:
				self._window_context._window_decorator._toolbar.show()
			else:
				self._window_context._window_decorator._toolbar.hide()
	
	def _ctrl_left_clicked(self, it):
		"""
		For synchronization by synctex
		"""
		# Editor._ctrl_left_clicked
		
		tab = self.tab_decorator.tab
		line = it.get_line() + 1
		column = it.get_line_offset() + 1
		source_file = "%s/%s" % (self._file.dirname, self._file.basename)
		# We use self.file and not self._file here, to get the 
		# master document, because the output file will have the 
		# name of the master document
		try:
			output_file = "%s.pdf" % self.file.shortname
		except:
			# Is this due to a bug ? Or is there a method I 
			# don't know to check wether a file has/is a 
			# master file or doesn't/couldn't have one ?
			self.__log.debug("Error while trying to get the output file path. No master document ?")
			return
		
		from livepreview import LaTeXPreviews
		
		if self._window_context.latex_previews == None:
			self._window_context.latex_previews = LaTeXPreviews(self._window_context)
			
		latex_previews = self._window_context.latex_previews
		latex_previews.sync_view(tab, source_file, line, column, output_file)
	
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
			
			# reset highlight
			self.remove_markers("latex-error")
			self.remove_markers("latex-warning")
			
			# reset issues
			self._issue_view.clear()
			
			if BENCHMARK: t = time.clock()
			
			# parse document
			if self._document != None:
				self._document.destroy()
				del self._document
			self._document = self._parser.parse(self.content, self._file, self)
			
			if BENCHMARK: self._log.info("LaTeXParser.parse: %f" % (time.clock() - t))
			
			# create a copy that won't be expanded (e.g. for spell check)
			#self._local_document = deepcopy(self._document)
			
			self._log.debug("Parsed %s bytes of content" % len(self.content))
			
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
	#@returns(File)
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
		# stop listening preferences
		self._preferences.remove_monitor(self)

		# unreference the window context
		del self._context
		
		# destroy the cached document
		self._document.destroy()
		del self._document

		Editor.destroy(self)
		
	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)
	
