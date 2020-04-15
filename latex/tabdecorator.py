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
base.decorators

These classes are 'attached' to the according Gedit objects. They form the
extension point.
"""

import logging

from gi.repository import GObject

from .config import EDITORS
from .file import File

# TODO: maybe create ActionDelegate for GeditWindowDecorator

LOG = logging.getLogger(__name__)

class GeditTabDecorator(object):
    """
    This monitors the opened file and manages the Editor objects
    according to the current file extension
    """

    def __init__(self, window_decorator, tab, init=False):
        """
        Construct a GeditTabDecorator

        @param window_decorator: the parent GeditWindowDecorator
        @param tab: the GeditTab to create this for
        @param init: has to be True if this is created on plugin init to decorate
                        already opened files
        """
        self._window_decorator = window_decorator
        self._tab = tab
        self._text_buffer = tab.get_document()
        self._text_view = tab.get_view()

        self._editor = None
        self._file = None

        # initially check the editor instance
        #
        # this needs to be done, because when we init for already opened files
        # (when plugin is activated in config) we get no "loaded" signal
        if init:
            self._adjust_editor()

        # listen to GeditDocument signals
        self._signals_handlers = [
                self._text_buffer.connect("loaded", self._on_load),
                self._text_buffer.connect("saved", self._on_save)
        ]

        LOG.debug("created %s" % self)

    @property
    def tab(self):
        return self._tab

    def _on_load(self, document):
        """
        A file has been loaded
        """
        LOG.debug("file loaded")

        self._adjust_editor()

    def _on_save(self, document):
        """
        The file has been saved
        """
        LOG.debug("saved")

        if not self._adjust_editor():
            # if the editor has not changed
            if self._editor:
                self._editor.on_save()

    def _adjust_editor(self):
        """
        Check if the URI has changed and manage Editor object according to
        file extension

        @return: True if the editor has changed
        """
        location = self._text_buffer.get_file().get_location()
        if location is None:
            # this happends when the plugin is activated in a running Gedit
            # and this decorator is created for the empty file

            LOG.debug("no file loaded")

            if self._window_decorator.window.get_active_view() == self._text_view:
                GObject.idle_add(self._window_decorator.adjust, self)

        else:
            file = File(location.get_uri())

            if file == self._file:        # FIXME: != doesn't work for File...
                return False
            else:
                LOG.debug("adjust_editor: URI has changed")

                self._file = file

                # URI has changed - manage the editor instance
                if self._editor:
                    # editor is present - destroy editor
                    self._editor.destroy()
                    self._editor = None

                # FIXME: comparing file extensions should be case-INsensitive...
                extension = file.extension

                # find Editor class for extension
                editor_class = None
                for clazz in EDITORS:
                    if extension in clazz.extensions:
                        editor_class = clazz
                        break

                if not editor_class is None:
                    # create instance
                    self._editor = editor_class.__new__(editor_class)
                    editor_class.__init__(self._editor, self, file)

                    # The following doesn't work because the right expression is evaluated
                    # and then assigned to the left. This means that Editor.__init__ is
                    # running and reading _editor while _editor is None. That leads to
                    #
                    # Traceback (most recent call last):
                    #   File "/home/michael/.gnome2/Gedit/plugins/GeditLaTeXPlugin/src/base/decorators.py", line 662, in _on_load
                    #     self._adjust_editor()
                    #   File "/home/michael/.gnome2/Gedit/plugins/GeditLaTeXPlugin/src/base/decorators.py", line 716, in _adjust_editor
                    #     self._editor = editor_class(self, file)
                    #   File "/home/michael/.gnome2/Gedit/plugins/GeditLaTeXPlugin/src/base/__init__.py", line 353, in __init__
                    #     self.init(file, self._window_context)
                    #   File "/home/michael/.gnome2/Gedit/plugins/GeditLaTeXPlugin/src/latex/editor.py", line 106, in init
                    #     self.__parse()
                    #   File "/home/michael/.gnome2/Gedit/plugins/GeditLaTeXPlugin/src/latex/editor.py", line 279, in __parse
                    #     self._outline_view.set_outline(self._outline)
                    #   File "/home/michael/.gnome2/Gedit/plugins/GeditLaTeXPlugin/src/latex/views.py", line 228, in set_outline
                    #     OutlineConverter().convert(self._store, outline, self._offset_map, self._context.active_editor.edited_file)

                    #self._editor = editor_class(self, file)
                else:
                    LOG.info("No editor class found for extension %s" % extension)

                # tell WindowDecorator to adjust actions
                # but only if this tab is the active tab
                if self._window_decorator.window.get_active_view() == self._text_view:
                    GObject.idle_add(self._window_decorator.adjust,self)

                # notify that URI has changed
                return True

    @property
    def file(self):
        return self._file

    @property
    def editor(self):
        return self._editor

    @property
    def extension(self):
        """
        @return: the extension of the currently opened file
        """
        if self._file is None:
            return None
        else:
            return self._file.extension

    def destroy(self):
        # disconnect from signals
        for handler in self._signals_handlers:
            self._text_buffer.disconnect(handler)

        # unreference the window decorator
        del self._window_decorator

        # destroy Editor instance
        if not self._editor is None:
            self._editor.destroy()

# ex:ts=4:et:
