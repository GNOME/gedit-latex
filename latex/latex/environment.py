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
latex.environment
"""

from gi.repository import Gdk
import os
from os import popen, system
#from Gtk.gdk import screen_width, screen_height, screen_width_mm, screen_height_mm
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
    "utf8"       : "UTF-8 (Unicode)",
    "ascii"       : "US-ASCII",
    "next"     : "ASCII (NeXT)",
    "ansinew"  : "ASCII (Windows)",
    "applemac" : "ASCII (Apple)",
    "macce"    : "MacCE (Apple Central European)",
    "latin1"   : "Latin-1 (Western European)",
    "latin2"   : "Latin-2 (Danubian European)",
    "latin3"   : "Latin-3 (South European)",
    "latin4"   : "Latin-4 (North European)",
    "latin5"   : "Latin-5 (Turkish)",
    "latin6"   : "Latin-6 (Nordic)",
    "latin7"   : "Latin-7 (Baltic)",
    "latin8"   : "Latin-8 (Celtic)",
    "latin9"   : "Latin-9 (extended Latin-1)",
    "latin10"  : "Latin-10 (South-Eastern European)",
    "cp1250"   : "CP1250 (Windows Central European)",
    "cp1252"   : "CP1252 (Windows Western European)",
    "cp1257"   : "CP1257 (Windows Baltic)",
    "cp437"    : "CP437 (DOS US with β)",
    "cp437de"  : "CP437 (DOS US with ß)",
    "cp850"    : "CP850 (DOS Latin-1)",
    "cp852"    : "CP852 (DOS Central European)",
    "cp858"    : "CP858 (DOS Western European)",
    "cp865"    : "CP865 (DOS Nordic)",
    "decmulti" : "DEC Multinational Character Set"
}

_BABEL_PACKAGES = {
    "albanian"     : "Albanian",
    "afrikaans"     : "Afrikaans", #dutch dialect
    "austrian"     : "Austrian",
    "naustrian"     : "Austrian (new spelling)",
    "bahasai"       : "Bahasa Indonesia",
    "bahasam"     : "Bahasa Malaysia",
    "basque"      : "Basque",
    "breton"     : "Breton",
    "bulgarian"     : "Bulgarian",
    "catalan"     : "Catalan",
    "croatian"     : "Croatian",
    "czech"         : "Czech",
    "danish"     : "Danish",
    "dutch"         : "Dutch",
    "australian"     : "English (AU)",
    "canadian"     : "English (CA)",
    "newzealand"     : "English (NZ)",
    "UKenglish"     : "English (UK)",
    "english"     : "English (US)",
    "esperanto"     : "Esperanto",
    "estonian"     : "Estonian",
    "finnish"     : "Finnish",
    "frenchb"     : "French",
    "acadian"     : "French (Acadian)",
    "canadien"     : "French (CA)",
    "galician"     : "Galician",
    "germanb"     : "German",
    "ngermanb"     : "German (new spelling)",
    "greek"         : "Greek",
    "polutonikogreek" : "Greek (polytonic)",
#    "athnum"     : "Greek (Athens numbering)",
    "hebrew"     : "Hebrew",
    "magyar"     : "Hungarian",
    "icelandic"     : "Icelandic",
    "interlingua"     : "Interlingua",
    "irish"         : "Irish Gaelic",
    "italian"     : "Italian",
    "latin"         : "Latin",
    "lsorbian"     : "Lower Sorbian",
    "norsk"         : "Norwegian Bokmål",
    "nynorsk"     : "Norwegian Nynorsk",
    "polish"     : "Polish",
    "portuges"     : "Portuguese (PT)",
    "brazilian"     : "Portuguese (BR)",
    "romanian"     : "Romanian",
    "russianb"     : "Russian",
    "samin"         : "North Sami",
    "scottish"     : "Scottish Gaelic",
    "serbian"     : "Serbian",
    "slovak"     : "Slovak",
    "slovene"     : "Slovene",
    "spanish"     : "Spanish",
    "swedish"     : "Swedish",
    "turkish"     : "Turkish",
    "ukraineb"     : "Ukraine",
    "usorbian"     : "Upper Sorbian",
    "welsh"         : "Welsh"
}

_DOCUMENT_CLASSES = {
    "abstbook"    : _("Book of abstracts"),
    "article"     : _("Article"),
    "amsart"    : _("Article (AMS)"),
    "amsbook"    : _("Book (AMS)"),
    "amsdtx"    : _("AMS Documentation"),
    "amsproc"    : _("Proceedings (AMS)"),
    "report"     : _("Report"),
    "beamer"     : _("Beamer slides"),
    "beletter"    : _("Belgian letter"),
    "book"         : _("Book"),
    "flashcard"    : _("Flashcard"),
    "iagproc"    : _("Proceedings (IAG)"),
    "letter"     : _("Letter"),
    "ltnews"    : _("LaTeX News"),
    "ltxdoc"    : _("LaTeX Documentation"),
    "ltxguide"    : _("LaTeX Guide"),
    "proc"        : _("Proceedings"),
    "scrartcl"     : _("Article (KOMA-Script)"),
    "scrreport"    : _("Report (KOMA-Script)"),
    "scrbook"     : _("Book (KOMA-Script)"),
    "scrlettr"     : _("Letter (KOMA-Script)"),
    "scrlttr2"     : _("Letter 2 (KOMA-Script)"),
    "scrreprt"    : _("Report (KOMA-Script)"),
    "slides"    : _("Slides")
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


from os.path import expanduser

from ..file import File


class Environment(object):

    _DEFAULT_TEXMF_DIR = "/usr/share/texlive/texmf-dist"
    _DEFAULT_TEXMF_DIR_HOME = "~/texmf"

    """
    This encapsulates the user's LaTeX distribution and provides methods
    for searching it
    """

    _log = getLogger("Environment")

    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

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
            default_search_paths = [self._DEFAULT_TEXMF_DIR, expanduser(self._DEFAULT_TEXMF_DIR_HOME)]

            if self.kpsewhich_installed:
                for key in ["TEXMFMAIN", "TEXMFDIST", "TEXMFHOME"]:
                    found = popen("kpsewhich -var-value %s" % key).read().splitlines()
                    exists = bool(len(found))
                    self._search_paths.append(found[0])
            else:
                self._log.error("Command \"kpsewhich\" not found, using default search paths %s" % (self._CONFIG_FILENAME, default_search_paths))
                self._search_paths = default_search_paths

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
        files = []

        for search_path in self._search_paths:
            dir_path = "%s%s" % (search_path, relative)
            if not os.path.exists(dir_path):
                continue
            files += [File(f) for f in popen("find %s -name '*%s'" % (dir_path, extension)).readlines()]

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

        for name, label in labels.items():
            found = False
            for resource in resources:
                if resource.name == name:
                    found = True
            if not found:
                resources.append(TeXResource(None, name, label))

        return resources

    @property
    def screen_dpi(self):
        if not self._screen_dpi:
            display = Gdk.Display.get_default()
            # FIXME: find most appropriate monitor, not first (0):
            monitor = display.get_monitor(0)
            geometry = monitor.get_geometry()
            try:
                dpi_x = geometry.width / monitor.get_width_mm() * 25.4
                dpi_y = geometry.height / monitor.get_height_mm() * 25.4
            except ZeroDivisionError:
                # Happens inside qemu virtual machines. Entirely arbitrary value:
                dpi_x = dpi_y = 5

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


# ex:ts=4:et:
