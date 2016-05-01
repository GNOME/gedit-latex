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
util

Utility classes, functions and decorators used at various places across
the project
"""

import logging

def singleton(cls):
    """
    Singleton decorator that works with GObject derived types. The 'recommended'
    python one - http://wiki.python.org/moin/PythonDecoratorLibrary#Singleton
    does not (interacts badly with GObjectMeta
    """
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

from gi.repository import Gtk
import traceback
from xml.sax import saxutils


class StringReader(object):
    """
    A simple string reader that is able to push back one character
    """
    def __init__(self, string):
        self._iter = iter(string)
        self.offset = 0
        self._pushbackChar = None
        self._pushbackFlag = False

    def read(self):
        if self._pushbackFlag:
            self._pushbackFlag = False
            return self._pushbackChar
        else:
            self.offset += 1
            return next(self._iter)

    def unread(self, char):
        #assert not self._pushbackFlag

        self._pushbackChar = char
        self._pushbackFlag = True


def escape(string, remove_newlines=True):
    """
    Prepares a string for inclusion in Pango markup and error messages
    """
    s = saxutils.escape(string)
    s = s.replace("\n", " ")
    s = s.replace("\"", "&quot;")
    return s


def open_error(message, secondary_message=None):
    """
    Popup an error dialog window
    """
    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, message)
    if secondary_message:
        # TODO: why not use markup?
        dialog.format_secondary_text(secondary_message)
    dialog.run()
    dialog.destroy()


def open_info(message, secondary_message=None):
    """
    Popup an info dialog window
    """
    dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            Gtk.MessageType.INFO, Gtk.ButtonsType.OK, message)
    if secondary_message:
        dialog.format_secondary_markup(secondary_message)
    dialog.run()
    dialog.destroy()


def verbose(function):
    """
    'verbose'-decorator. This runs the decorated method in a try-except-block
    and shows an error dialog on exception.
    """
    def decorated_function(*args, **kw):
        try:
            return function(*args, **kw)
        except Exception as e:
            stack = traceback.format_exc(limit=10)
            open_error(str(e), stack)
    return decorated_function


class GladeInterface(object):
    """
    Utility base class for interfaces loaded from a Glade definition
    """

    __log = logging.getLogger("GladeInterface")

    def __init__(self):
        self.__tree = None
        self.filename = None

    def __get_tree(self):
        if not self.__tree:
            self.__tree = Gtk.Builder()
            self.__tree.set_translation_domain('gedit-latex')
            self.__tree.add_from_file(self.filename)
        return self.__tree

    def find_widget(self, name):
        """
        Find a widget by its name
        """
        widget = self.__get_tree().get_object(name)
        if widget is None:
            self.__log.error("Widget '%s' could not be found in interface description '%s'" % (name, self.filename))
        return widget

    def connect_signals(self, mapping):
        """
        Auto-connect signals
        """
        self.__get_tree().connect_signals(mapping)

# ex:ts=4:et:
