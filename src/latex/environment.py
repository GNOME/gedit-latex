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
latex.environment
"""

from os import popen, system
from os.path import splitext, basename
from gtk.gdk import screen_width, screen_height, screen_width_mm, screen_height_mm
from pwd import getpwnam
from getpass import getuser
from locale import getdefaultlocale, nl_langinfo, D_FMT
from logging import getLogger


class CnfFile(dict):
	"""
	This parses a .cnf file and provides its contents as a dictionary
	"""
	def __init__(self, filename):
		"""
		@raise IOError: if file is not found
		"""
		for line in open(filename).readlines():
			if not line.startswith("%"):
				try:
					key, value = line.split("=")
					self[key.strip()] = value.strip()
				except:
					pass


_INPUT_ENCODINGS = {
	"utf8" : "UTF-8 (Unicode)",
	"ascii" : "US-ASCII",
	"next" : "ASCII (NeXT)",
	"ansinew" : "ASCII (Windows)",
	"applemac" : "ASCII (Apple)",
	"macce" : "MacCE (Apple Central European)",
	"latin1" : "Latin-1",
	"latin2" : "Latin-2",
	"latin3" : "Latin-3 (South European)",
	"latin4" : "Latin-4 (North European)",
	"latin5" : "Latin-5 (Turkish)",
	"latin6" : "Latin-6 (Nordic)",
	"latin7" : "Latin-7 (Baltic)",
	"latin8" : "Latin-8 (Celtic)",
	"latin9" : "Latin-9 (extended Latin-1)",
	"latin10" : "Latin-10 (South-Eastern European)",
	"cp1250" : "CP1250 (Windows Central European)",
	"cp1252" : "CP1252 (Windows Western European)",
	"cp1257" : "CP1257 (Windows Baltic)",
	"cp437" : "CP437 (DOS US)",
	"cp850" : "CP850 (DOS Latin-1)",
	"cp852" : "CP852 (DOS Central European)",
	"cp858" : "CP858 (DOS Western European)",
	"cp865" : "CP865 (DOS Nordic)"
}

_BABEL_PACKAGES = {
	"acadian" : "Acadian French",
	"albanian" : "Albanian",
	"afrikaans" : "Afrikaans",
	"american" : "American",
	"australian" : "Australian",
	"austrian" : "Austrian",
	"naustrian" : "Austrian (new spelling)",
	"bahasa" : "Bahasa Indonesia",
	"bahasai" : "Bahasa Indonesia",
	"indon" : "Bahasa Indonesia",
	"indonesian" : "Bahasa Indonesia",
	"malay" : "Bahasa Malaysia",
	"meyalu" : "Bahasa Malaysia",
	"bahasam" : "Bahasa Malaysia",
	"basque" : "Basque",
	"brazil" : "Brazilian Portuguese",
	"brazilian" : "Brazilian Portugese",
	"breton" : "Breton",
	"british" : "British",
	"bulgarian" : "Bulgarian",
	"canadian" : "Canadian English",
	"canadien" : "Canadian French",
	"catalan" : "Catalan",
	"croatian" : "Croatian",
	"czech" : "Czech",
	"danish" : "Danish",
	"dutch" : "Dutch",
	"english" : "English",
	"UKenglish" : "English (UK)",
	"USenglish" : "English (US)",
	"esperanto" : "Esperanto",
	"estonian" : "Estonian",
	"finnish" : "Finnish",
	"francais" : "French",
	"french" : "French",
	"frenchb" : "French",
	"galician" : "Galician",
	"german" : "German",
	"germanb" : "German",
	"ngerman" : "German (new spelling)",
	"ngermanb" : "German (new spelling)",
	"greek" : "Greek",
	"polutonikogreek" : "Greek (polytonic)",
#	"athnum" : "Greek (Athens numbering)",
	"hebrew" : "Hebrew",
	"hungarian" : "Hungarian",
	"icelandic" : "Icelandic",
	"interlingua" : "Interlingua",
	"irish" : "Irish Gaelic",
	"italian" : "Italian",
	"kannada" : "Kannada",
	"latin" : "Latin",
	"lsorbian" : "Lower Sorbian",
	"magyar" : "Magyar",
	"nagari" : "Nagari",
	"norsk" : "Norwegian Bokmål",
	"nynorsk" : "Norwegian Nynorsk",
	"polish" : "Polish",
	"portuges" : "Portuguese",
	"portuguese" : "Portugese",
	"romanian" : "Romanian",
	"russianb" : "Russian",
	"samin" : "Samin",
	"sanskrit" : "Sanskrit",
	"scottish" : "Scottish Gaelic",
	"serbian" : "Serbian",
	"slovak" : "Slovak",
	"slovene" : "Slovene",
	"spanish" : "Spanish",
	"swedish" : "Swedish",
	"tamil" : "Tamil",
	"turkish" : "Turkish",
	"ukraineb" : "Ukraine",
	"usorbian" : "Upper Sorbian",
	"welsh" : "Welsh"
}

_DOCUMENT_CLASSES = {
	"article" 	: _("Article"),
	"report" 	: _("Report"),
	"book" 		: _("Book"),
	"beamer" 	: _("Beamer slides"),
	"letter" 	: _("Letter"),
	"scrartcl" 	: _("Article (KOMA-Script)"),
	"scrreport" : _("Report (KOMA-Script)"),
	"scrbook" 	: _("Book (KOMA-Script)"),
	"scrlettr" 	: _("Letter (KOMA-Script)"),
	"scrlttr2" 	: _("Letter 2 (KOMA-Script)"),
	"scrreprt"	: _("Report (KOMA-Script)")
}


class TeXResource(object):
	def __init__(self, file, name, label):
		"""
		@param file: a File object
		@param name: the identifier of this resource (e.g. 'ams' for 'ams.bib')
		@param label: a descriptive label
		"""
		self.file = file
		self.name = name
		self.label = label


from ..base import File


class Environment(object):
	
	_CONFIG_FILENAME = "/etc/texmf/texmf.cnf"
	_DEFAULT_TEXMF_DIR = "/usr/share/texmf-texlive"
	
	"""
	This encapsulates the user's LaTeX distribution and provides methods
	for searching it
	"""
	
	_log = getLogger("Environment")
	
	def __new__(type):
		if not '_instance' in type.__dict__:
			type._instance = object.__new__(type)
		return type._instance
	
	def __init__(self):
		if not '_ready' in dir(self):
			self._bibtex_styles = None
			self._classes = None
			self._language_definitions = None
			self._input_encodings = None
			self._screen_dpi = None
			self._kpsewhich_checked = False
			self._kpsewhich_installed = None
			self._file_exists_cache = {}
			
			self._search_paths = []
			
			try:
				cnf_file = CnfFile(self._CONFIG_FILENAME)

				path_found = False
				
				for key in ["TEXMFMAIN", "TEXMFDIST"]:
					try:
						self._search_paths.append(cnf_file[key])
						path_found = True
					except KeyError:
						# config key not found
						self._log.error("Key %s not found in %s" % (key, self._CONFIG_FILENAME))
				
				if not path_found:
					self._log.error("No search paths found in %s, using default search path %s" % (key, self._CONFIG_FILENAME, self._DEFAULT_TEXMF_DIR))
					self._search_paths = [self._DEFAULT_TEXMF_DIR]
				
			except IOError:
				# file _CONFIG_FILENAME not found - use default path
				self._log.error("%s not found, using default search path %s" % (self._CONFIG_FILENAME, self._DEFAULT_TEXMF_DIR))
				self._search_paths = [self._DEFAULT_TEXMF_DIR]
			
			self._ready = True
	
	@property
	def kpsewhich_installed(self):
		"""
		Return whether kpsewhich is installed
		"""
		if not self._kpsewhich_checked:
			self._kpsewhich_installed = bool(system("kpsewhich --version $2>/dev/null") == 0)
			self._kpsewhich_checked = True
		return self._kpsewhich_installed
	
	def file_exists(self, filename):
		"""
		Uses kpsewhich to check if a TeX related file (.bst, .sty etc.) exists. The result
		is cached to minimize 'kpsewhich' calls. 
		"""
		if not self.kpsewhich_installed:
			return True
		
		try:
			return self._file_exists_cache[filename]
		except KeyError:
			found = popen("kpsewhich %s" % filename).read().splitlines()
			exists = bool(len(found))
			self._file_exists_cache[filename] = exists
			return exists
	
	@property
	def bibtex_styles(self):
		"""
		Return the available .bst files
		"""
		if not self._bibtex_styles:
			self._bibtex_styles = self._find_resources("", ".bst", {})
		return self._bibtex_styles
	
	@property
	def document_classes(self):
		"""
		Return the available document classes
		"""
		if not self._classes:
			self._classes = self._find_resources("", ".cls", _DOCUMENT_CLASSES)
		return self._classes
	
	@property
	def language_definitions(self):
		if not self._language_definitions:
			self._language_definitions = self._find_resources("/tex/generic/babel/", ".ldf", _BABEL_PACKAGES)
		return self._language_definitions
	
	@property
	def input_encodings(self):
		"""
		Return a list of all available input encodings
		"""
		if not self._input_encodings:
			self._input_encodings = self._find_resources("/tex/latex/base/", ".def", _INPUT_ENCODINGS)
		return self._input_encodings
	
	def _find_resources(self, relative, extension, labels):
		"""
		Find TeX resources
		
		@param relative: a path relative to TEXMF... search path, e.g. '/tex/latex/base/'
		@param extension: the file extension of the resources, e.g. '.bst'
		@param labels: the dictionary to be searched for labels  
		"""
		resources = []
		
		for search_path in self._search_paths:
			files = [File(f) for f in popen("find %s%s -name '*%s'" % (search_path, relative, extension)).readlines()]
			if len(files) > 0:
				for file in files:
					name = file.shortbasename
					try:
						label = labels[name]
					except KeyError:
						label = ""
					resources.append(TeXResource(file, name, label))
			else:
				# no files found
				self._log.error("No %s-files found in %s%s" % (extension, search_path, relative))
				for name, label in labels.iteritems():
					resources.append(TeXResource(None, name, label))
					
		return resources
	
	@property
	def screen_dpi(self):
		if not self._screen_dpi:
			dpi_x = screen_width() / (screen_width_mm() / 25.4)
			dpi_y = screen_height() / (screen_height_mm() / 25.4)
			
			self._screen_dpi = (dpi_x + dpi_y) / 2.0
			
		return self._screen_dpi
	
	@property
	def username(self):
		"""
		Return user name derived from pwd entry
		"""
		record = getpwnam(getuser()) # get pwd entry
		
		self._log.debug("Found user pw entry: " + str(record))
		
		if len(record[4]):
			return record[4].split(",")[0]
		else:
			return record[0].title()
	
	@property
	def date_format(self):
		"""
		Return localized date format for use in strftime()
		"""
		return nl_langinfo(D_FMT)
	
	@property
	def language_code(self):
		"""
		Return language code like 'de'
		"""
		return getdefaultlocale()[0]

