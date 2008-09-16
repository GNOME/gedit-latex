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
latex.environment
"""

# TODO: The file
# /usr/share/texmf/web2c/texmf.cnf
# should always contain TEXMFMAIN. We could run a
# find /usr/share/texmf-texlive/ -name '*.bst'
# then.
# find /usr/share/texmf-texlive/ -name '*.cls'

from os import popen, system
from os.path import splitext, basename
from gtk.gdk import screen_width, screen_height, screen_width_mm, screen_height_mm
from pwd import getpwnam
from getpass import getuser
from locale import getdefaultlocale, nl_langinfo, D_FMT
from logging import getLogger


class Environment(object):
	
	_TEXMFMAIN = "/usr/share/texmf-texlive/"
	
	"""
	This encapsulates the user's LaTeX distribution and provides methods
	for searching it.
	
	It is implemented as a signleton to be able to share caches.
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
			self._screen_dpi = None
			self._kpsewhich_checked = False
			self._kpsewhich_installed = None
			self._file_exists_cache = {}
			
			self._ready = True
	
	@property
	def kpsewhich_installed(self):
		"""
		Return whether kpsewhich is installed
		"""
		if not self._kpsewhichChecked:
			self._kpsewhichInstalled = bool(system("kpsewhich --version $2>/dev/null") == 0)
			self._kpsewhichChecked = True
		return self._kpsewhichInstalled
	
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
			self._bibtex_styles = [splitext(basename(f))[0] for f in popen("find %s -name '*.bst'" % self._TEXMFMAIN).readlines()]
			self._bibtex_styles.sort()
		return self._bibtex_styles
	
	@property
	def document_classes(self):
		"""
		Return the available document classes
		"""
		if not self._classes:
			self._classes = [splitext(basename(f))[0] for f in popen("find %s -name '*.cls'" % self._TEXMFMAIN).readlines()]
			self._classes.sort()
		return self._classes
	
	@property
	def screen_dpi(self):
		if not self._screenDpi:
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

