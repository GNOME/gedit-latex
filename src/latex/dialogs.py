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
latex.dialogs
"""

from logging import getLogger

from ..util import GladeInterface
from ..base.resources import find_resource
from ..base import Template, File


class ChooseMasterDialog(GladeInterface):
	"""
	Dialog for choosing a master file to a LaTeX fragment file
	"""
	filename = find_resource("glade/choose_master_dialog.glade")
	
	def run(self, folder):
		"""
		Runs the dialog and returns the selected filename
		
		@param folder: a folder to initially place the file chooser
		"""
		dialog = self.find_widget("dialogSelectMaster")
		file_chooser_button = self.find_widget("filechooserbutton")
		file_chooser_button.set_current_folder(folder)
		
		if dialog.run() == 1:
			filename = file_chooser_button.get_filename()
		else:
			filename = None
		dialog.hide()
		
		return filename


import gtk
from time import strftime

from ..base.preferences import Preferences
from environment import Environment


class NewDocumentDialog(GladeInterface):
	"""
	Dialog for creating the body of a new LaTeX document
	"""
	filename = find_resource("glade/new_document_dialog.glade")
	
	_log = getLogger("NewDocumentWizard")
	
	_PAPER_SIZES = (
		("a4paper", "A4"),
		("a5paper", "A5"),
		("b5paper", "B5"),
		("executivepaper", "US-Executive"),
		("legalbl_paper", "US-Legal"),
		("letterpaper", "US-Letter") )
	
	_LOCALE_MAPPINGS = {
		"en_US" : "american",
		"en_AU" : "english",
		"fr" : "french",
		"it" : "italian",
		"ru" : "russian",
		"de_DE" : "ngerman",
		"de_AU" : "naustrian"
	}
	
	dialog = None
	
	def get_dialog(self):
		"""
		Build and return the dialog
		"""
		if self.dialog == None:
			preferences = Preferences()
			environment = Environment()
			
			self.dialog = self.find_widget("dialogNewDocument")
		
			lightForeground = preferences.get("LightForeground")
			
			# file
			self._entryName = self.find_widget("entryName")
			self._buttonDirectory = self.find_widget("buttonDirectory")
			self._buttonDirectory.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
			
			# meta
			self._entry_title = self.find_widget("entryTitle")
			self._entry_author = self.find_widget("entryAuthor")
			self._entry_author.set_text(preferences.get("RecentAuthor", environment.username))
			self._radio_date_custom = self.find_widget("radioCustom")
			self._entry_date = self.find_widget("entryDate")
			
			#
			# document classes
			#
			self._store_classes = gtk.ListStore(str, str)	# class, label
			
			for cls in environment.document_classes:
				self._store_classes.append([cls.name, "%s <span color='%s'>%s</span>" % (cls.name, lightForeground, cls.label)])
			
			# get index of recent class
#			recentClass = preferences.get("RecentDocumentClass", "article")
#			try:
#				recentClassIndex = classes.index(recentClass)
#			except ValueError:
#				self._log.error("Unknown recent document class: %s" % recentClass)
#				recentClassIndex = 0
			
			self._comboClasses = self.find_widget("comboClass")
			self._comboClasses.set_model(self._store_classes)
			cell = gtk.CellRendererText()
			self._comboClasses.pack_start(cell, True)
			self._comboClasses.add_attribute(cell, "markup", 1)
#			self._comboClasses.set_active(recentClassIndex)
			
			
			# paper
			recentPaperSize = preferences.get("RecentPaperSize", "")
			if len(recentPaperSize) == 0:
				recentPaperSizeIndex = 0
			
			self._storePaperSize = gtk.ListStore(str, str)  # size, label
			
			self._storePaperSize.append(["", "<span color='%s'>Default</span>" % lightForeground])
			i = 1
			for size, label in self._PAPER_SIZES:
				l = "%s <span color='%s'>%s</span>" % (size, lightForeground, label)
				self._storePaperSize.append([size, l])
				
				if recentPaperSize == size:
					recentPaperSizeIndex = i
				i += 1
			
			self._comboPaperSize = self.find_widget("comboPaperSize")
			self._comboPaperSize.set_model(self._storePaperSize)
			cell = gtk.CellRendererText()
			self._comboPaperSize.pack_start(cell, True)
			self._comboPaperSize.add_attribute(cell, "markup", 1)
			
			self._comboPaperSize.set_active(recentPaperSizeIndex)
			
			
			self._checkLandscape = self.find_widget("checkLandscape")
			self._checkLandscape.set_active(preferences.get_bool("RecentPaperLandscape", False))
			
			
			# font size
			self._radioFontUser = self.find_widget("radioFontUser")
			self._spinFontSize = self.find_widget("spinFontSize")
			self._labelFontSize = self.find_widget("labelFontSize")
			
			#
			# input encodings
			#
			self._storeEncoding = gtk.ListStore(str, str)	# encoding, label
			
			for encoding in environment.input_encodings:
				self._storeEncoding.append([encoding.name, "%s <span color='%s'>%s</span>" % (encoding.name, 
																		lightForeground, encoding.label)])
			
			self._comboEncoding = self.find_widget("comboEncoding")
			self._comboEncoding.set_model(self._storeEncoding)
			cell = gtk.CellRendererText()
			self._comboEncoding.pack_start(cell, True)
			self._comboEncoding.add_attribute(cell, "markup", 1)
			
			# get index of recent encoding
			# TODO: try to guess default from editor
			
#			recentEncoding = preferences.get("RecentInputEncoding", "utf8")
#			try:
#				recentEncodingIndex = encodings.index(recentEncoding)
#			except ValueError:
#				self._log.error("Unknown recent input encoding: %s" % recentEncoding)
#				recentEncodingIndex = 0
#			
#			self._comboEncoding.set_active(recentEncodingIndex)
			
			#
			# babel packages
			#
			self._storeBabel = gtk.ListStore(str, str) # package, label
			
			for ldf in environment.language_definitions:
				self._storeBabel.append([ldf.name, "%s <span color='%s'>%s</span>" % (ldf.name, 
																		lightForeground, ldf.label)])
			
			self._comboBabel = self.find_widget("comboBabel")
			self._comboBabel.set_model(self._storeBabel)
			cell = gtk.CellRendererText()
			self._comboBabel.pack_start(cell, True)
			self._comboBabel.add_attribute(cell, "markup", 1)
			
			# get index of recent babel package
			# TODO: try to map locale to babel package as default value
			
#			try:
#				defaultBabel = self._LOCALE_MAPPINGS[environment.language_code]
#			except Exception, e:
#				self._log.error("Failed to guess babel package: %s" % e)
#				defaultBabel = "english"
#			
#			recentBabel = preferences.get("RecentBabelPackage", defaultBabel)
#			try:
#				recentBabelIndex = babelPackages.index(recentBabel)
#			except ValueError:
#				self._log.error("Unknown recent babel package: %s" % recentBabel)
#				recentBabelIndex = 0
#			self._comboBabel.set_active(recentBabelIndex)
			
			
			# connect signals
#			self.connect_signals({ "on_radioCustom_toggled" : self._on_custom_date_toggled,
#								   "on_radioFontUser_toggled" : self._on_user_font_toggled })

		return self.dialog
	
	@property
	def source(self):
		"""
		Compose the source
		"""
		# document class options
		documentOptions = []
		
		if self._radioFontUser.get_active():
			documentOptions.append("%spt" % self._spinFontSize.get_value_as_int())
		
		paperSize = self._storePaperSize[self._comboPaperSize.get_active()][0]
		if len(paperSize) > 0:
			documentOptions.append(paperSize)
		
		if self._checkLandscape.get_active():
			documentOptions.append("landscape")
		
		if len(documentOptions) > 0:
			documentOptions = "[" + ",".join(documentOptions) + "]"
		else:
			documentOptions = ""
		
		
		documentClass = self._store_classes[self._comboClasses.get_active()][0]
		title = self._entry_title.get_text()
		author = self._entry_author.get_text()
		babelPackage = self._storeBabel[self._comboBabel.get_active()][0]
		inputEncoding = self._storeEncoding[self._comboEncoding.get_active()][0]
		
		if self._radio_date_custom.get_active():
			date = self._entry_date.get_text()
		else:
			date = "\\today"
		
		if self.find_widget("checkPDFMeta").get_active():
			ifpdf = "\n\\usepackage{ifpdf}"
			pdfinfo = """
\\ifpdf
	\\pdfinfo {
		/Author (%s)
		/Title (%s)
		/Subject (SUBJECT)
		/Keywords (KEYWORDS)
		/CreationDate (D:%s)
	}
\\fi""" % (author, title, strftime('%Y%m%d%H%M%S'))
		else:
			ifpdf = ""
			pdfinfo = ""
		
		s = """\\documentclass%s{%s}
\\usepackage[%s]{inputenc}
\\usepackage[%s]{babel}%s
\\title{%s}
\\author{%s}
\\date{%s}%s
\\begin{document}
	
\\end{document}""" % (documentOptions, documentClass, inputEncoding, babelPackage, ifpdf, title, author, date, pdfinfo)
		
		return s
	
	@property
	def file(self):
		return File("%s/%s.tex" % (self._buttonDirectory.get_filename(), self._entryName.get_text()))
	
	def run(self):
		"""
		Runs the dialog and returns a Template object
		"""
		dialog = self.get_dialog()
		r = dialog.run()
		dialog.hide()
		return r


from tempfile import NamedTemporaryFile
from os.path import basename, splitext

from ..base import File
from preview import PreviewRenderer

		
class UseBibliographyDialog(GladeInterface, PreviewRenderer):
	"""
	Dialog for inserting a reference to a bibliography
	"""
	filename = find_resource("glade/use_bibliography_dialog.glade")
	
	_log = getLogger("UseBibliographyWizard")
	
	
	# sample bibtex content used for rendering the preview
	_BIBTEX = """@book{ dijkstra76,
	title={{A Discipline of Programming}},
	author={Edsger W. Dijkstra},
	year=1976 }
@article{ dijkstra68,
	title={{Go to statement considered harmful}},
	author={Edsger W. Dijkstra},
	year=1968 }"""
	
	dialog = None
	
	def run_dialog(self, edited_file):
		"""
		Run the dialog
		
		@param edited_file: the File edited the active Editor
		@return: the source resulting from the dialog
		"""
		source = None
		dialog = self._get_dialog()
		
		if dialog.run() == 1:		# TODO: use gtk constant
			# get selected filenames
			files = [File(row[1]) for row in self._storeFiles if row[0]]
			
			# relativize them
			base_dir = edited_file.dirname
			relative_shortnames = [file.relativize_shortname(base_dir) for file in files]
			
			source = "\\bibliography{%s}\n\\bibliographystyle{%s}" % (",".join(relative_shortnames), 
																	self._storeStyle[self._comboStyle.get_active()][0])
		
		dialog.hide()
		
		return source
	
	def _get_dialog(self):
		if not self.dialog:
			
			self.dialog = self.find_widget("dialogUseBibliography")
			
			# bib files
			
			self._storeFiles = gtk.ListStore(bool, str)	 # checked, filename
			
#			for b in Settings().bibliographies:
#				self._storeFiles.append([False, b.filename])
				
			self._viewFiles = self.find_widget("TreeViewFiles")
			self._viewFiles.set_model(self._storeFiles)
			rendererToggle = gtk.CellRendererToggle()
			rendererToggle.connect("toggled", self._on_use_toggled)
			self._viewFiles.insert_column_with_attributes(-1, "Use", rendererToggle, active=0)
			self._viewFiles.insert_column_with_attributes(-1, "Filename", gtk.CellRendererText(), text=1)
			
			# styles
			
			self._storeStyle = gtk.ListStore(str)
			
			styles = Environment().bibtex_styles
			for style in styles:
				self._storeStyle.append([style])
			
			self._comboStyle = self.find_widget("comboboxStyle")
			self._comboStyle.set_model(self._storeStyle)
			self._comboStyle.set_text_column(0)
			
			try:
				recent = styles.index(Preferences().get("RecentBibtexStyle", "plain"))
			except ValueError:
				recent = 0
			self._comboStyle.set_active(recent)
			
			
			self._imagePreview = gtk.Image()
			self._imagePreview.show()
			
			scrollPreview = self.find_widget("scrollPreview")
			scrollPreview.add_with_viewport(self._imagePreview)
			
			
			self.connect_signals({ "on_buttonAddFile_clicked" : self._on_add_clicked,
									"on_buttonRemoveFile_clicked" : self._on_remove_clicked,
									"on_buttonRefresh_clicked" : self._on_refresh_clicked })
			
		return self.dialog
	
	def _on_use_toggled(self, renderer, path):
		"""
		Toggle "Use" cell
		"""
		value = self._storeFiles.get(self._storeFiles.get_iter_from_string(path), 0)[0]
		self._storeFiles.set(self._storeFiles.get_iter_from_string(path), 0, not value)
	
	def _on_refresh_clicked(self, widget):
		"""
		The button for refreshing the preview has been clicked
		"""
		self._imagePreview.set_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_BUTTON)
		
		# create temporary bibtex file
		self._tempFile = NamedTemporaryFile(mode="w", suffix=".bib")
		self._tempFile.write(self._BIBTEX)
		self._tempFile.flush()
		
		filename = self._tempFile.name
		self._filenameBase = splitext(basename(filename))[0]
		
		# build preview image
		style = self._storeStyle[self._comboStyle.get_active()][0]
		
		self.render("Book \\cite{dijkstra76} Article \\cite{dijkstra68} \\bibliography{%s}\\bibliographystyle{%s}" % (self._filenameBase, 
																													style))
	
	def _on_add_clicked(self, button):
		"""
		Add BibTeX files
		"""
		filter = gtk.FileFilter()
		filter.set_name("BibTeX Bibliography")
		filter.add_pattern("*.bib")
		
		fileChooser = gtk.FileChooserDialog("Add Bibliography", buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, 
																		gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
		fileChooser.set_filter(filter)
		fileChooser.set_select_multiple(True)
		
		if fileChooser.run() == gtk.RESPONSE_ACCEPT:
			filenames = [row[1] for row in self._storeFiles]
			
			for filename in fileChooser.get_filenames():
				if not filename in filenames:
					self._storeFiles.append([True, filename])
					
					# store in settings
					Settings().addBibliography(filename)
			
		fileChooser.hide()

	def _on_remove_clicked(self, button):
		"""
		Remove selected file
		"""
		
		# TODO: remove from settings
		
		model, iter = self._viewFiles.get_selection().get_selected()
		if iter:
			# remove from settings
			filename = model.get_value(iter, 1)
			Settings().deleteBibliography(filename)
			
			model.remove(iter)
			
	def _on_render_succeeded(self, pixbuf):
		# PreviewRenderer._on_render_succeeded
		
		self._imagePreview.set_from_pixbuf(pixbuf)
		# remove the temp bib file
		self._tempFile.close()
	
	def _on_render_failed(self):
		# PreviewRenderer._on_render_failed
		
		# set a default icon as preview
		self._imagePreview.set_from_stock(gtk.STOCK_STOP, gtk.ICON_SIZE_BUTTON)
		# remove the temp bib file
		self._tempFile.close()
	
	