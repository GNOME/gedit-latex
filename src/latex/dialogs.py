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

from ..preferences import Preferences
from ..util import GladeInterface
from ..base.resources import find_resource
from ..base import Template, File


class AbstractProxy(object):
	"""
	This may simplify the use of a widget and it serves for state saving
	using the plugins preferences.
	"""
	def __init__(self, widget, key):
		"""
		@param widget: the widget to proxy
		@param key: a preferences key to use for state saving
		"""
		self._widget = widget
		self._key = key
		self._preferences = Preferences()
	
	def restore(self, default):
		"""
		Restore the last state of the proxied widget
		
		@param default: a default value if no state is found
		"""
		raise NotImplementedError
	
	def save(self):
		"""
		Save the state of the proxied widget
		"""
		self._preferences.set(self._key, self.value)
	
	@property
	def value(self):
		"""
		@return: the current value of the proxied widget
		"""
		raise NotImplementedError


class ComboBoxProxy(AbstractProxy):
	"""
	This proxies a ComboBox widget:
	
	p = ComboBoxProxy(self.find_widget("myCombo"), "SomeSetting")
	p.add_option("thing_1", "First Thing")
	p.add_option("thing_2", "Second Thing")
	p.restore("thing_1")
	...
	"""
	def __init__(self, widget, key):
		AbstractProxy.__init__(self, widget, key)
		
		self._store = gtk.ListStore(str, str)			# value, label
		self._widget.set_model(self._store)
		cell = gtk.CellRendererText()
		self._widget.pack_start(cell, True)
		self._widget.add_attribute(cell, "markup", 1)
		
		self._options = []
	
	def restore(self, default):
		restored_value = self._preferences.get(self._key, default)
		i = 0
		for value, label in self._options:
			if value == restored_value:
				restored_index = i
				break
			i += 1
		self._widget.set_active(restored_index)
		
		self._widget.connect("changed", self._on_changed)
	
	def _on_changed(self, combobox):
		self.save()
	
	def add_option(self, value, label, show_value=True):
		"""
		Add an option to the widget
		
		@param value: a unique value
		@param label: a label text that may contain markup
		"""
		self._options.append((value, label))
		if show_value:
			if not value is None and len(value) > 0:
				label_markup = "%s <span color='%s'>%s</span>" % (value, self._preferences.get("LightForeground"), label)
			else:
				label_markup = "<span color='%s'>%s</span>" % (self._preferences.get("LightForeground"), label)
		else:
			label_markup = label
		self._store.append([value, label_markup])
	
	@property
	def value(self):
		index = self._widget.get_active()
		return self._options[index][0]
	
	
class EntryProxy(AbstractProxy):
	def __init__(self, widget, key):
		AbstractProxy.__init__(self, widget, key)
	
	def restore(self, default):
		self._widget.set_text(self._preferences.get(self._key, default))
	
	@property
	def value(self):
		return self._widget.get_text()
	

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
	
	_DEFAULT_FONT_FAMILIES =  (
		("\\rmdefault", "Default Roman"),
		("\\sfdefault", "Default Sans Serif"),
		("\\ttdefault", "Default Typewrite") )
	
	# TODO: extend this
	_LOCALE_MAPPINGS = {
		"en_US" : "american",
		"en_AU" : "english",
		"fr" : "french",
		"it" : "italian",
		"ru" : "russian",
		"de_DE" : "ngermanb",
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
			
			#
			# file
			#
			self._entry_name = self.find_widget("entryName")
			self._button_dir = self.find_widget("buttonDirectory")
			self._button_dir.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
			
			#
			# metadata
			#
			self._entry_title = self.find_widget("entryTitle")
			self._entry_author = self.find_widget("entryAuthor")
			self._entry_author.set_text(preferences.get("RecentAuthor", environment.username))
			self._radio_date_custom = self.find_widget("radioCustom")
			self._entry_date = self.find_widget("entryDate")
			
			#
			# document classes
			#
			self._proxy_document_class = ComboBoxProxy(self.find_widget("comboClass"), "RecentDocumentClass")
			for c in environment.document_classes:
				self._proxy_document_class.add_option(c.name, c.label)
			self._proxy_document_class.restore("article")
				
			#
			# paper
			#
			self._proxy_paper_size = ComboBoxProxy(self.find_widget("comboPaperSize"), "RecentPaperSize")
			self._proxy_paper_size.add_option("", "Default")
			for size, label in self._PAPER_SIZES:
				self._proxy_paper_size.add_option(size, label)
			self._proxy_paper_size.restore("")
			
			
			self._check_landscape = self.find_widget("checkLandscape")
			self._check_landscape.set_active(preferences.get_bool("RecentPaperLandscape", False))
			
			#
			# font size
			#
			self._radio_font_user = self.find_widget("radioFontUser")
			self._spin_font_size = self.find_widget("spinFontSize")
			self._labelFontSize = self.find_widget("labelFontSize")
			
			#
			# font family
			#
			self._proxy_font_family = ComboBoxProxy(self.find_widget("comboFontFamily"), "RecentDefaultFontFamily")
			for command, label in self._DEFAULT_FONT_FAMILIES:
				self._proxy_font_family.add_option(command, label, False)
			self._proxy_font_family.restore("\\rmdefault")
			
			
			#
			# input encodings
			#
			self._proxy_encoding = ComboBoxProxy(self.find_widget("comboEncoding"), "RecentInputEncoding")
			for e in environment.input_encodings:
				self._proxy_encoding.add_option(e.name, e.label)
			self._proxy_encoding.restore("utf8")
			
			#
			# babel packages
			#
			self._proxy_babel = ComboBoxProxy(self.find_widget("comboBabel"), "RecentBabelPackage")
			for l in environment.language_definitions:
				self._proxy_babel.add_option(l.name, l.label)
			try:
				self._proxy_babel.restore(self._LOCALE_MAPPINGS[environment.language_code])
			except Exception, e:
				self._log.error("Failed to guess babel package: %s" % e)
				self._proxy_babel.restore("english")
			
			#
			# connect signals
			#
			self.connect_signals({ "on_radioCustom_toggled" : self._on_custom_date_toggled,
								   "on_radioFontUser_toggled" : self._on_user_font_toggled })

		return self.dialog
	
	def _on_custom_date_toggled(self, toggle_button):
		self._entry_date.set_sensitive(toggle_button.get_active())
		
	def _on_user_font_toggled(self, toggle_button):
		self._spin_font_size.set_sensitive(toggle_button.get_active())
		self._labelFontSize.set_sensitive(toggle_button.get_active())
	
	@property
	def source(self):
		"""
		Compose and return the source resulting from the dialog
		"""
		# document class options
		documentOptions = []
		
		if self._radio_font_user.get_active():
			documentOptions.append("%spt" % self._spin_font_size.get_value_as_int())
		
#		paperSize = self._store_paper_size[self._combo_paper_size.get_active()][0]
#		if len(paperSize) > 0:
#			documentOptions.append(paperSize)
		paperSize = self._proxy_paper_size.value
		if paperSize != "":
			documentOptions.append(paperSize)
		
		if self._check_landscape.get_active():
			documentOptions.append("landscape")
		
		if len(documentOptions) > 0:
			documentOptions = "[" + ",".join(documentOptions) + "]"
		else:
			documentOptions = ""
		
		
#		documentClass = self._store_class[self._combo_class.get_active()][0]
		documentClass = self._proxy_document_class.value

		title = self._entry_title.get_text()
		author = self._entry_author.get_text()
#		babelPackage = self._store_babel[self._combo_babel.get_active()][0]
#		inputEncoding = self._store_encoding[self._combo_encoding.get_active()][0]
		babelPackage = self._proxy_babel.value
		inputEncoding = self._proxy_encoding.value
		
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
		"""
		Return the File object
		"""
		return File("%s/%s.tex" % (self._button_dir.get_filename(), self._entry_name.get_text()))
	
	def run(self):
		"""
		Runs the dialog
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
		
		self._file_chooser_button.set_current_folder(edited_file.dirname)
		
		if dialog.run() == 1:		# TODO: use gtk constant
			# get selected filenames
			#files = [File(row[1]) for row in self._storeFiles if row[0]]
			
			# relativize them
			base_dir = edited_file.dirname
#			relative_shortnames = [file.relativize_shortname(base_dir) for file in files]
#			
#			source = "\\bibliography{%s}\n\\bibliographystyle{%s}" % (",".join(relative_shortnames), 
#																	self._storeStyle[self._comboStyle.get_active()][0])

			file = File(self._file_chooser_button.get_filename())
			source = "\\bibliography{%s}\n\\bibliographystyle{%s}" % (file.relativize_shortname(base_dir), 
																	self._storeStyle[self._comboStyle.get_active()][0])
		
		dialog.hide()
		
		return source
	
	def _get_dialog(self):
		if not self.dialog:
			
			self.dialog = self.find_widget("dialogUseBibliography")
			
			# bib file
			
			self._file_chooser_button = self.find_widget("filechooserbutton")
			
			
#			self._storeFiles = gtk.ListStore(bool, str)	 # checked, filename
#			
##			for b in Settings().bibliographies:
##				self._storeFiles.append([False, b.filename])
#				
#			self._viewFiles = self.find_widget("TreeViewFiles")
#			self._viewFiles.set_model(self._storeFiles)
#			rendererToggle = gtk.CellRendererToggle()
#			rendererToggle.connect("toggled", self._on_use_toggled)
#			self._viewFiles.insert_column_with_attributes(-1, "Use", rendererToggle, active=0)
#			self._viewFiles.insert_column_with_attributes(-1, "Filename", gtk.CellRendererText(), text=1)
			
			# styles
			
			self._storeStyle = gtk.ListStore(str)
			
			styles = Environment().bibtex_styles
			for style in styles:
				self._storeStyle.append([style.name])
			
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
			
			
			self.connect_signals({ #"on_buttonAddFile_clicked" : self._on_add_clicked,
									#"on_buttonRemoveFile_clicked" : self._on_remove_clicked,
									"on_buttonRefresh_clicked" : self._on_refresh_clicked })
			
		return self.dialog
	
#	def _on_use_toggled(self, renderer, path):
#		"""
#		Toggle "Use" cell
#		"""
#		value = self._storeFiles.get(self._storeFiles.get_iter_from_string(path), 0)[0]
#		self._storeFiles.set(self._storeFiles.get_iter_from_string(path), 0, not value)
	
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
	
#	def _on_add_clicked(self, button):
#		"""
#		Add BibTeX files
#		"""
#		filter = gtk.FileFilter()
#		filter.set_name("BibTeX Bibliography")
#		filter.add_pattern("*.bib")
#		
#		fileChooser = gtk.FileChooserDialog("Add Bibliography", buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, 
#																		gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
#		fileChooser.set_filter(filter)
#		fileChooser.set_select_multiple(True)
#		
#		if fileChooser.run() == gtk.RESPONSE_ACCEPT:
#			filenames = [row[1] for row in self._storeFiles]
#			
#			for filename in fileChooser.get_filenames():
#				if not filename in filenames:
#					self._storeFiles.append([True, filename])
#					
#					# store in settings
#					#Settings().addBibliography(filename)
#			
#		fileChooser.hide()
#
#	def _on_remove_clicked(self, button):
#		"""
#		Remove selected file
#		"""
#		
#		# TODO: remove from settings
#		
#		model, iter = self._viewFiles.get_selection().get_selected()
#		if iter:
#			# remove from settings
#			filename = model.get_value(iter, 1)
#			Settings().deleteBibliography(filename)
#			
#			model.remove(iter)
			
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


from . import LaTeXSource


class InsertGraphicsDialog(GladeInterface):
	
	_PREVIEW_WIDTH, _PREVIEW_HEIGHT = 128, 128
	filename = find_resource("glade/insert_graphics_dialog.glade")
	_dialog = None
	
	def run(self, edited_file):
		"""
		@param edited_file: the File currently edited
		"""
		dialog = self.__get_dialog()
		
		source = None
		
		if dialog.run() == 1:
			#filename = self._fileChooser.get_filename()
			
			file = File(self._fileChooser.get_filename())
			relative_filename = file.relativize(edited_file.dirname)
			
			width = "%.2f" % round(self.find_widget("spinbuttonWidth").get_value() / 100.0, 2)
			caption = self.find_widget("entryCaption").get_text()
			label = self.find_widget("entryLabel").get_text()
			floating = self.find_widget("checkbuttonFloat").get_active()
			spread = self.find_widget("checkbuttonSpread").get_active()
			relativeTo = self._comboRelative.get_active()
			rotate = self.find_widget("spinRotate").get_value()
			flip = self.find_widget("checkFlip").get_active()
			
			source = ""
			packages = ["graphicx"]
			
			if relativeTo == 0:		# relative to image size
				options = "scale=%s" % width
			else:		# relative to text width
				options = "width=%s\\textwidth" % width
			
			if rotate != 0:
				options += ", angle=%s" % rotate
			
			includegraphics = "\\includegraphics[%s]{%s}" % (options, relative_filename)
			
			if flip:
				includegraphics = "\\reflectbox{%s}" % includegraphics
			
			if floating:
				if spread:
					ast = "*"
				else:
					ast = ""
				source += "\\begin{figure%s}[ht]\n\t\\centering\n\t%s" % (ast, includegraphics)
				if len(caption):
					source += "\n\t\\caption{%s}" % caption
				if len(label) and label != "fig:":
					source += "\n\t\\label{%s}" % label
				source += "\n\\end{figure%s}" % ast
			else:
				source += "\\begin{center}\n\t%s" % includegraphics
				if len(caption):
					source += "\n\t\\captionof{figure}{%s}" % caption
					packages.append("caption")
				if len(label) and label != "fig:":
					source += "\n\t\\label{%s}" % label
				source += "\n\\end{center}"
				
#			viewAdapter.insertText(source)
#			viewAdapter.ensurePackages(packages)

			source = LaTeXSource(source, packages)
		
		dialog.hide()
		
		return source
	
	def __get_dialog(self):
		if not self._dialog:
			
			# setup the dialog
			
			self._dialog = self.find_widget("dialogInsertGraphics")
			
			previewImage = gtk.Image()
			self._fileChooser = self.find_widget("FileChooser")
			self._fileChooser.set_preview_widget(previewImage)
			self._fileChooser.connect("update-preview", self.__update_preview, previewImage)
			
			#self._fileChooser.get_property("dialog").connect("response", self._fileChooserResponse)	# FIXME: not readable
			#self._fileChooser.connect("file-activated", self._fileActivated)							# FIXME: doesn't work
			
			self._okayButton = self.find_widget("buttonOkay")
			
			self._comboRelative = self.find_widget("comboRelative")
			self._comboRelative.set_active(0)
			
		return self._dialog
	
	def __update_preview(self, fileChooser, previewImage):
		""" 
		Update the FileChooser's preview image 
		"""
		filename = fileChooser.get_preview_filename()
		
		try:
			pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, self._PREVIEW_WIDTH, self._PREVIEW_HEIGHT)
			previewImage.set_from_pixbuf(pixbuf)
			fileChooser.set_preview_widget_active(True)
		except:
			fileChooser.set_preview_widget_active(False)


class InsertTableDialog(GladeInterface):
	"""
	This is used to include tables and matrices
	"""
	
	filename = find_resource("glade/insert_table_dialog.glade")
	_dialog = None
	
	def run(self):
		dialog = self.__get_dialog()
		
		source = None
		
		if dialog.run() == 1:
			floating = self.find_widget("checkbuttonFloat").get_active()
			rows = int(self.find_widget("spinbuttonRows").get_value())
			cols = int(self.find_widget("spinbuttonColumns").get_value())
			caption = self.find_widget("entryCaption").get_text()
			label = self.find_widget("entryLabel").get_text()
			
			s = ""
			
			if self.find_widget("radiobuttonTable").get_active():
				# table
				
				layout = "l" * cols
				
				if floating:
					s += "\\begin{table}[ht]\n\t\\centering\n\t\\begin{tabular}{%s}%s\n\t\\end{tabular}" % (layout, 
																						self.__build_table_body(rows, cols, "\t\t"))
					
					if len(caption):
						s += "\n\t\\caption{%s}" % caption
					
					if len(label) and label != "tab:":
						s += "\n\t\\label{%s}" % label
					
					s += "\n\\end{table}"
				
				else:
					s += "\\begin{center}\n\t\\begin{tabular}{%s}%s\n\t\\end{tabular}" % (layout, 
																						self.__build_table_body(rows, cols, "\t\t"))
					
					if len(caption):
						s += "\n\t\\captionof{table}{%s}" % caption
					
					if len(label):
						s += "\n\t\\label{%s}" % label
					
					s += "\n\\end{center}"
				packages = []
			else:
				environ = self._storeDelims[self._comboDelims.get_active()][2]
				s = "\\begin{%s}%s\n\\end{%s}" % (environ, self.__build_table_body(rows, cols, "\t\t"), environ)
				packages = ["amsmath"]
			
			source = LaTeXSource(Template(s), packages)
			
		dialog.hide()
		
		return source
	
	def __get_dialog(self):
		if not self._dialog:
			self._dialog = self.find_widget("dialogInsertTable")
			
			# delimiters
			self._storeDelims = gtk.ListStore(gtk.gdk.Pixbuf, str, str)  	# icon, label, environment
			
			self._storeDelims.append([None, "None", "matrix"])
			
			delimiters = [("parantheses", "Parantheses", "pmatrix"), 
						("brackets", "Brackets", "bmatrix"), 
						("braces", "Braces", "Bmatrix"), 
						("vbars", "Vertical Bars", "vmatrix"), 
						("dvbars", "Double Vertical Bars", "Vmatrix")]
			
			for d in delimiters:
				pixbuf = gtk.gdk.pixbuf_new_from_file(find_resource("icons/%s.png" % d[0]))
				self._storeDelims.append([pixbuf, d[1], d[2]])
			
			self._comboDelims = self.find_widget("comboDelims")
			self._comboDelims.set_model(self._storeDelims)
			
			cellPixbuf = gtk.CellRendererPixbuf()
	  		self._comboDelims.pack_start(cellPixbuf, False)
	  		self._comboDelims.add_attribute(cellPixbuf, 'pixbuf', 0)
	  		
			cellText = gtk.CellRendererText()
	  		self._comboDelims.pack_start(cellText, False)
	  		self._comboDelims.add_attribute(cellText, 'text', 1)
	  		
	  		self._comboDelims.set_active(0)
	  		
	  		self.connect_signals({ "on_radioMatrix_toggled" : self.__matrix_toggled })
			
		return self._dialog

	def __matrix_toggled(self, toggleButton):
		self._comboDelims.set_sensitive(toggleButton.get_active())

	def __build_table_body(self, rows, cols, indent):
		"""
		This builds the body of a table template according to the number of rows and
		columns.
		"""
		s = ""
		for i in range(rows):
			colList = []
			for j in range(cols):
				colList.append("${x}")
			s += "\n" + indent + " & ".join(colList) + " \\\\"
		return s


from listing import LanguagesParser


class InsertListingDialog(GladeInterface):
	"""
	"""
	
	filename = find_resource("glade/insert_listing_dialog.glade")
	_dialog = None
	
	def run(self, edited_file):
		"""
		@param edited_file: the File currently edited
		"""
		dialog = self.__get_dialog()
		
		source = None
		
		if dialog.run() == 1:
			
			lstset = ""
			options = ""
			
			language = self._storeLanguages[self._comboLanguage.get_active()][0]
			try:
				dialect = self._storeDialects[self._comboDialect.get_active()][0]
			except IndexError:
				dialect = ""
			
			if self._dialectsEnabled and len(dialect):
				# we need the lstset command
				lstset = "\\lstset{language=[%s]%s}\n" % (dialect, language)
			else:
				options = "[language=%s]" % language
			
			
			if self._checkFile.get_active():
				file = File(self._fileChooserButton.get_filename())
				relative_filename = file.relativize(edited_file.dirname)
				
				source = "%s\\lstinputlisting%s{%s}" % (lstset, options, relative_filename)
			
			else:
				source = "%s\\begin{lstlisting}%s\n\t$_\n\\end{lstlisting}" % (lstset, options)
			
			source = LaTeXSource(Template(source), ["listings"])
			
		dialog.hide()
		
		return source
	
	def __get_dialog(self):
		if not self._dialog:
			self._dialog = self.find_widget("dialogListing")
			
			self._fileChooserButton = self.find_widget("fileChooserButton")
			
			#
			# languages
			#
			self._languages = []
			parser = LanguagesParser()
			parser.parse(self._languages, find_resource("listings.xml"))
			
			recentLanguage = Preferences().get("RecentListingLanguage", "Java")
			
			self._storeLanguages = gtk.ListStore(str)
			recentLanguageIndex = 0
			i = 0
			for l in self._languages:
				self._storeLanguages.append([l.name])
				if l.name == recentLanguage:
					recentLanguageIndex = i
				i += 1
			
			self._comboLanguage = self.find_widget("comboLanguage")
			self._comboLanguage.set_model(self._storeLanguages)
			cell = gtk.CellRendererText()
			self._comboLanguage.pack_start(cell, True)
			self._comboLanguage.add_attribute(cell, "text", 0)
			
			#
			# dialects
			#
			self._labelDialect = self.find_widget("labelDialect")
			
			self._storeDialects = gtk.ListStore(str)
			
			self._comboDialect = self.find_widget("comboDialect")
			self._comboDialect.set_model(self._storeDialects)
			cell = gtk.CellRendererText()
			self._comboDialect.pack_start(cell, True)
			self._comboDialect.add_attribute(cell, "text", 0)
			
			self._checkFile = self.find_widget("checkFile")
			
			self.connect_signals({ "on_checkFile_toggled" : self._fileToggled,
								  "on_comboLanguage_changed" : self._languagesChanged })
			
			
			self._comboLanguage.set_active(recentLanguageIndex)
			
			self._dialectsEnabled = False
			
		return self._dialog
	
	def _languagesChanged(self, comboBox):
		language = self._languages[comboBox.get_active()]
		
		self._storeDialects.clear()
		
		if len(language.dialects):
			i = 0
			for dialect in language.dialects:
				self._storeDialects.append([dialect.name])
				if dialect.default:
					self._comboDialect.set_active(i)
				i += 1
			
			self._labelDialect.set_sensitive(True)
			self._comboDialect.set_sensitive(True)
			
			self._dialectsEnabled = True
		else:
			self._labelDialect.set_sensitive(False)
			self._comboDialect.set_sensitive(False)
			
			self._dialectsEnabled = False
	
	def _fileToggled(self, toggleButton):
		self._fileChooserButton.set_sensitive(toggleButton.get_active())
	
	def _specificToggled(self, toggleButton):
		self._comboLanguage.set_sensitive(toggleButton.get_active())
		self._labelDialect.set_sensitive(toggleButton.get_active() and self._dialectsEnabled)
		self._comboDialect.set_sensitive(toggleButton.get_active() and self._dialectsEnabled)
