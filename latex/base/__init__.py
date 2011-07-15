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
base

These classes form the interface exposed by the plugin base layer.
"""

from logging import getLogger
from gi.repository import Gtk, Gdk
from .file import File

#FIXME: this should probably be just a Gtk.Orientable iface
# HORIZONTAL: means Bottom Panel
# VERTICAL: means Side Panel
class PanelView(Gtk.Box):
    """
    Base class for a View
    """

    _log = getLogger("PanelView")

    SCOPE_WINDOW = 0
    SCOPE_EDITOR = 1

    def __init__(self, context):
        Gtk.Box.__init__(self)
        self._context = context

    # these should be overriden by subclasses

    # a label string used for this view
    def get_label(self):
        raise NotImplementedError

    # an icon for this view (Gtk.Image or a stock_id string)
    def get_icon(self):
        return None

    # FIXME: this doesn't seems to be used, should we remove it?
    # the scope of this PanelView:
    #    SCOPE_WINDOW: the View is created with the window and the same instance is passed to every Editor
    #    SCOPE_EDITOR: the View is created with the Editor and destroyed with it
    def get_scope(self):
        return self.SCOPE_WINDOW

    def __del__(self):
        self._log.debug("Properly destroyed %s" % self)

class Template(object):
    """
    This one is exposed and should be used by the 'real' plugin code
    """
    def __init__(self, expression):
        self._expression = expression

    @property
    def expression(self):
        return self._expression

    def __str__(self):
        return self._expression


from gi.repository import GObject


class GeditLaTeXPlugin_MenuToolAction(Gtk.Action):
    __gtype_name__ = "GeditLaTeXPlugin_MenuToolAction"

    def do_create_tool_item(self):
        return Gtk.MenuToolButton()


class Action(object):
    """
    """

    menu_tool_action = False    # if True a MenuToolAction is created and hooked for this action
                                # instead of Gtk.Action

    extensions = [None]            # a list of file extensions for which this action should be enabled
                                # [None] indicates that this action is to be enabled for all extensions

    def __init__(self, *args, **kwargs):
        pass

    def hook(self, action_group, window_context):
        """
        Create an internal action object (Gtk.Action or MenuToolAction), listen to it and
        hook it in an action group

        @param action_group: a Gtk.ActionGroup object
        @param window_context: a WindowContext object to pass when this action is activated
        """
        if self.menu_tool_action:
            action_clazz = GeditLaTeXPlugin_MenuToolAction
        else:
            action_clazz = Gtk.Action
        self._internal_action = action_clazz(self.__class__.__name__, self.label, self.tooltip, self.stock_id)
        self._handler = self._internal_action.connect("activate", lambda gtk_action, action: action.activate(window_context), self)
        action_group.add_action_with_accel(self._internal_action, self.accelerator)

    @property
    def label(self):
        raise NotImplementedError

    @property
    def stock_id(self):
        raise NotImplementedError

    @property
    def accelerator(self):
        raise NotImplementedError

    @property
    def tooltip(self):
        raise NotImplementedError

    def activate(self, context):
        """
        @param context: the current WindowContext instance
        """
        raise NotImplementedError

    def unhook(self, action_group):
        self._internal_action.disconnect(self._handler)
        action_group.remove_action(self._internal_action)

    #~ def __del__(self):
        #~ print "Properly destroyed Action %s" % self


class WindowContext(object):
    """
    The WindowContext is passed to Editors and is used to
     * retrieve View instances
     * activate a specific Editor instance
     * retrieve the currently active Editor

    This also creates and destroys the View instances.
    """

    _log = getLogger("WindowContext")

    def __init__(self, window_decorator, editor_scope_view_classes):
        """
        @param window_decorator: the GeditWindowDecorator this context corresponds to
        @param editor_scope_view_classes: a map from extension to list of View classes
        """
        self._window_decorator = window_decorator
        self._editor_scope_view_classes = editor_scope_view_classes

        self.window_scope_views = {}    # maps view ids to View objects
        self.editor_scope_views = {}    # maps Editor object to a map from ID to View object

        self._log.debug("init")

    def create_editor_views(self, editor, file):
        """
        Create instances of the editor specific Views for a given Editor instance
        and File

        Called by Editor base class
        """
        self.editor_scope_views[editor] = {}
        try:
            for id, clazz in self._editor_scope_view_classes[file.extension].iteritems():
                # create View instance and add it to the map
                self.editor_scope_views[editor][id] = clazz(self, editor)

                self._log.debug("Created view " + id)
        except KeyError:
            self._log.debug("No views for %s" % file.extension)

    ###
    # public interface

    @property
    def active_editor(self):
        """
        Return the active Editor instance
        """
        return self._window_decorator._active_tab_decorator.editor

    def activate_editor(self, file):
        """
        Activate the Editor containing a given File or open a new tab for it

        @param file: a File object

        @raise AssertError: if the file is no File object
        """
        assert type(file) is File

        self._window_decorator.activate_tab(file)

    def find_view(self, editor, view_id):
        """
        Return a View object
        """
        print self.editor_scope_views, editor, view_id
        try:
            return self.editor_scope_views[editor][view_id]
        except KeyError:
            return self.window_scope_views[view_id]

    def set_action_enabled(self, action_id, enabled):
        """
        Enable/disable an IAction object
        """
        self._window_decorator._action_group.get_action(action_id).set_sensitive(enabled)

    def destroy(self):
        # unreference the window decorator
        del self._window_decorator

    def __del__(self):
        self._log.debug("Properly destroyed %s" % self)

# ex:ts=4:et:
