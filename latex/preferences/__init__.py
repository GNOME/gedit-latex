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
preferences
"""

from gi.repository import GObject, Gio, GLib

import re
import os.path
import logging
import ConfigParser

from ..util import singleton

LOG = logging.getLogger(__name__)

class _DocumentConfigParser(ConfigParser.RawConfigParser):

    SECTION = "LATEX"

    def __init__(self, filename):
        ConfigParser.RawConfigParser.__init__(self)
        self._filename = filename
        self.read(filename)
        try:
            self.add_section(self.SECTION)
        except ConfigParser.DuplicateSectionError:
            pass

    def get(self, key):
        try:
            return ConfigParser.RawConfigParser.get(self,self.SECTION, key)
        except ConfigParser.NoOptionError:
            return None

    def set(self,key,value):
        ConfigParser.RawConfigParser.set(self, self.SECTION, key, value)

    def save(self):
        f = open(self._filename,'w')
        self.write(f)
        f.close()

class _Preferences(GObject.GObject):

    __gsignals__ = {
        "preferences-changed": (
            GObject.SignalFlags.RUN_LAST, None, [str, str]),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

    def get(self, key, default=None):
        raise NotImplementedError

    def set(self, key, value):
        pass

@singleton
class Preferences(_Preferences):
    """
    A simple map storing preferences as key-value-pairs
    """

    TEMPLATE_DIR = os.path.join(GLib.get_user_data_dir(), "gedit", "latex", "templates")

    def __init__(self):
        _Preferences.__init__(self)
        self._settings = Gio.Settings("org.gnome.gedit.plugins.latex")
        
        LOG.debug("Prefs singleton constructed")

    def get(self, key):
        LOG.debug("Prefs get: %s" % key)
        return self._settings[key]

    def set(self, key, value):
        LOG.debug("Prefs set: %s = %s" % (key,value))
        self._settings[key] = value
        self.emit("preferences-changed", str(key), str(value))

class DocumentPreferences(_Preferences):
    """
    Similar to @Preferences, but first tries to **GET** keys from the current
    document. Searches for lines of the following

    % gedit:key-name = value

    If that fails, it also looks in a .filename.ini file for key-name = value
    lines. If that fails, look in the system settings.

    When **SETTING** keys, they do not persist if they were previously defined in
    the document text, otherwise, they are set in the .ini file.
    """

    def __init__(self, file):
        _Preferences.__init__(self)
        self._sysprefs = Preferences()
        self._sysprefs.connect("preferences-changed", self._on_prefs_changed)
        self._file = file
        self._cp = _DocumentConfigParser(
                        "%s/.%s.ini" % (file.dirname, file.basename))

        self._re = re.compile("^\s*%+\s*gedit:(.*)\s*=\s*(.*)")
        self._modelines = {}

    def _on_prefs_changed(self, p, key, value):
        self.emit("preferences-changed", key, value)

    def _is_docpref(self,key):
        return key in self._modelines

    def parse_content(self, content, max_lines=100):
        """ Parses txt content from the document looking for modelines """
        self._modelines = {}

        i = 0
        for l in content.splitlines():
            if i > max_lines:
                break
            try:
                key,val = self._re.match(l).groups()
                LOG.debug("Detected preference modeline: %s = %s" % (key,val))
                self._modelines[key.strip()] = val
            except AttributeError:
                pass
            i = i+1

    def get(self, key):
        if self._is_docpref(key):
            LOG.debug("Get document pref: %s (modelines: %s)" % (key,",".join(self._modelines.keys())))
            return self._modelines.get(key, self._cp.get(key))
        else:
            return self._sysprefs.get(key)

    def set(self, key, value):
        if self._is_docpref(key):
            LOG.debug("Set document pref")
            self._cp.set(key,value)
            self._cp.save()
            self.emit("preferences-changed", key, value)
        else:
            self._sysprefs.set(key, value)

# ex:ts=4:et:
