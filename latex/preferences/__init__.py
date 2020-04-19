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
import configparser

from ..util import singleton
from ..resources import Resources

LOG = logging.getLogger(__name__)

class _DocumentConfigParser(configparser.RawConfigParser):

    SECTION = "LATEX"

    def __init__(self, filename):
        configparser.RawConfigParser.__init__(self)
        self._filename = filename
        self.read(filename)
        try:
            self.add_section(self.SECTION)
        except configparser.DuplicateSectionError:
            pass

    def __getitem__(self, key):
        try:
            return configparser.RawConfigParser.get(self,self.SECTION, key)
        except configparser.NoOptionError:
            raise KeyError

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def set(self, key, value):
        configparser.RawConfigParser.set(self, self.SECTION, key, value)

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

        if Resources().from_source:
            schema_source = Gio.SettingsSchemaSource.new_from_directory(
                                        Resources().systemdir,
                                        Gio.SettingsSchemaSource.get_default(),
                                        False)
            schema = schema_source.lookup("org.gnome.gedit.plugins.latex",
                                          False)
            self._settings = Gio.Settings.new_full(schema, None, None)

        elif "org.gnome.gedit.plugins.latex" not in Gio.Settings.list_schemas():
            logging.critical("Could not find GSettings schema: org.gnome.gedit.plugins.latex")
            raise Exception("Plugin schema not installed")
        else:
            self._settings = Gio.Settings("org.gnome.gedit.plugins.latex")
        
        LOG.debug("Pref singleton constructed")

    def get(self, key):
        LOG.debug("Get pref: %s" % key)
        return self._settings[key]

    def set(self, key, value):
        LOG.debug("Set pref: %s = %s" % (key,value))
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

        LOG.debug("Document preferences for %s" % file.basename)

    def _on_prefs_changed(self, p, key, value):
        self.emit("preferences-changed", key, value)

    def parse_content(self, content, max_lines=100):
        """ Parses txt content from the document looking for modelines """
        self._modelines = {}

        i = 0
        for l in content.splitlines():
            if i > max_lines:
                break
            try:
                key,val = self._re.match(l).groups()
                LOG.debug("Document %s prefs modeline: %s = %s" % (self._file.basename,key,val))
                self._modelines[key.strip()] = val
            except AttributeError:
                pass
            i = i+1

    def get(self, key):
        try:
            val = self._modelines[key]
            method = "modeline"
        except KeyError:
            try:
                val = self._cp[key]
                method = "configfile"
            except KeyError:
                try:
                    val = self._sysprefs.get(key)
                    method = "system"
                except KeyError:
                    val = None
                    method = "none"

        LOG.debug("Get doc %s pref: %s = %s (from: %s)" % (self._file.basename,key,val,method))

        return val

    def set(self, key, value):
        try:
            self._sysprefs.set(key, value)
            method = "system"
        except KeyError:
            self._cp.set(key,value)
            self._cp.save()
            self.emit("preferences-changed", key, value)
            method = "configfile"

        LOG.debug("Set doc %s pref: %s = %s (from: %s)" % (self._file.basename,key,value,method))
            

# ex:ts=4:et:
