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

from uuid import uuid1
from gi.repository import Gtk, GdkPixbuf, Gio

from .file import File
from .resources import Resources

class GeditLaTeXPlugin_MenuToolAction(Gtk.Action):
    __gtype_name__ = "GeditLaTeXPlugin_MenuToolAction"

    def do_create_tool_item(self):
        return Gtk.MenuToolButton()


class Action(object):
    """
    """

    menu_tool_action = False    # if True a MenuToolAction is created and hooked for this action
                                # instead of Gtk.Action

    extensions = [None]         # a list of file extensions for which this action should be enabled
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
    
    # Hooks a Gio.SimpleAction to a given window.
    def simplehook(self, window, window_context):
        self._simple_internal_action = Gio.SimpleAction(name=self.__class__.__name__)
        self._simplehandler = self._simple_internal_action.connect("activate", lambda action, param: self.activate(window_context))
        window.add_action(self._simple_internal_action)
        
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


class IconAction(Action):
    """
    A utility class for creating actions with a custom icon instead of
    a gtk stock id.

    The subclass must provide a field 'icon'.
    """

    icon_name = None   
    __stock_id = None

    def __init__(self, *args, **kwargs):
        self.__icon_factory = kwargs["icon_factory"]
        self.__icon = None

    @property
    def icon(self):
        """
        Return a File object for the icon to use
        """
        if not self.__icon:
            assert(self.icon_name)
            self.__icon = File(Resources().get_icon("%s.png" % self.icon_name)) 
        return self.__icon

    def __init_stock_id(self):
        #
        # generate a new stock id
        #
        self.__stock_id = str(uuid1())
        self.__icon_factory.add(
                self.__stock_id,
                Gtk.IconSet.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file(self.icon.path)))

    @property
    def stock_id(self):
        if self.icon:
            if not self.__stock_id:
                self.__init_stock_id()
            return self.__stock_id
        else:
            return None

# ex:ts=4:et:
