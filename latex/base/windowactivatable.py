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
This is searched by gedit for a class extending gedit.Plugin
"""

from gi.repository import Gedit, GObject, Gio, Gtk, PeasGtk
import logging
import string

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s	%(name)s - %(message)s")

from ..preferences import Preferences, IPreferencesMonitor
from ..preferences.dialog import PreferencesDialog
from ..tools import ToolAction
from ..tools.views import ToolView
from config import UI, WINDOW_SCOPE_VIEWS, EDITOR_SCOPE_VIEWS, ACTIONS
from . import File, SideView, BottomView, WindowContext
from decorators import GeditTabDecorator

class LaTeXWindowActivatable(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable, IPreferencesMonitor):
	__gtype_name__ =  "LaTeXWindowActivatable"

	"""
	This class
	 - manages the GeditTabDecorators
	 - hooks the actions as menu items and tool items
	 - installs side and bottom panel views
	"""

	window = GObject.property(type=Gedit.Window)

	_log = logging.getLogger("LaTeXWindowActivatable")

	# ui definition template for hooking tools in Gedit's ui
	_tool_ui_template = string.Template("""<ui>
			<menubar name="MenuBar">
				<menu name="ToolsMenu" action="Tools">
					<placeholder name="ToolsOps_1">$items</placeholder>
				</menu>
			</menubar>
		</ui>""")

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		"""
		Called when the window extension is activated
		"""
		self._preferences = Preferences()
		self._preferences.register_monitor(self)
		
		#
		# initialize context object
		#
		self._window_context = WindowContext(self, EDITOR_SCOPE_VIEWS)
		
		# the order is important!
		self._init_actions()
		self._init_tool_actions()
		self._init_views()
		self._init_tab_decorators()
		
		# FIXME: find another way to save a document
		self._save_action = self._ui_manager.get_action("/MenuBar/FileMenu/FileSaveMenu")
		
		#
		# listen to tab signals
		#
		self._signal_handlers = [
				self.window.connect("tab_added", self._on_tab_added),
				self.window.connect("tab_removed", self._on_tab_removed),
				self.window.connect("active_tab_changed", self._on_active_tab_changed),
				self.window.connect("destroy", self._on_window_destroyed) ]

	def do_deactivate(self):
		"""
		Called when the window extension is deactivated
		"""
		# save preferences and stop listening
		self._preferences.save()
		self._preferences.remove_monitor(self)
		
		# destroy tab decorators
		self._active_tab_decorator = None
		for tab in self._tab_decorators:
			self._tab_decorators[tab].destroy()
		self._tab_decorators = {}

		# disconnect from tab signals
		for id in self._signal_handlers:
			self.window.disconnect(id)
		del self._signal_handlers

		# remove all views
		self.disable()
		
		# destroy all window scope views
		# (the editor scope views are destroyed by the editor)
		for i in self._window_context.window_scope_views:
			self._window_context.window_scope_views[i].destroy()
		self._window_context.window_scope_views = {}
		
		# remove toolbar
		self._toolbar.destroy()
		
		# remove tool actions
		self._ui_manager.remove_ui(self._tool_ui_id)
		for gtk_action in self._action_handlers:
			gtk_action.disconnect(self._action_handlers[gtk_action])
			self._tool_action_group.remove_action(gtk_action)
		self._ui_manager.remove_action_group(self._tool_action_group)
		
		# remove actions
		self._ui_manager.remove_ui(self._ui_id)
		for clazz in self._action_objects:
			self._action_objects[clazz].unhook(self._action_group)
		self._ui_manager.remove_action_group(self._action_group)
		
		# destroy the window context
		self._window_context.destroy()
		del self._window_context

	def do_create_configure_widget(self):
		return PreferencesDialog().dialog

	def _init_views(self):
		"""
		"""
		
		# selection states for each TabDecorator
		self._selected_bottom_views = {}
		self._selected_side_views = {}
		
		# currently hooked editor-scope views
		self._side_views = []
		self._bottom_views = []
		
		# currently hooked window-scope views
		self._window_side_views = []
		self._window_bottom_views = []
	
		# caches window-scope View instances
		self._views = {}
		
		#
		# init the ToolView, it's always present
		#
		# TODO: position is ignored
		# 
		tool_view = ToolView(self._window_context)
		self._views["ToolView"] = tool_view
		#fixme put the id!
		bottom_panel = self.window.get_bottom_panel()
		bottom_panel.add_item(tool_view, "ToolViewid", tool_view.label, tool_view.icon)
		#self._window_bottom_views.append(tool_view)
		
		# update window context
		self._window_context.window_scope_views = self._views

	def _init_actions(self):
		"""
		Merge the plugin's UI definition with the one of Gedit and hook the actions
		"""
		self._ui_manager = self.window.get_ui_manager()
		self._action_group = Gtk.ActionGroup("LaTeXWindowActivatableActions")
		self._icon_factory = Gtk.IconFactory()
		self._icon_factory.add_default()
		
		# create action instances, hook them and build up some
		# hash tables
		
		self._action_objects = {}		# name -> Action object
		self._action_extensions = {}	# extension -> action names
		
		for clazz in ACTIONS:
			action = clazz(icon_factory=self._icon_factory)
			action.hook(self._action_group, self._window_context)
			
			self._action_objects[clazz.__name__] = action
			
			for extension in action.extensions:
				if extension in self._action_extensions.keys():
					self._action_extensions[extension].append(clazz.__name__)
				else:
					self._action_extensions[extension] = [clazz.__name__]
		
		# merge ui
		self._ui_manager.insert_action_group(self._action_group, -1)
		self._ui_id = self._ui_manager.add_ui_from_string(UI)
		
		# hook the toolbar
		self._toolbar = self._ui_manager.get_widget("/LaTeXToolbar")
		self._toolbar.set_style(Gtk.ToolbarStyle.BOTH_HORIZ)
		
		self._main_box = self.window.get_children()[0]
		self._main_box.pack_start(self._toolbar, False, True, 0)
		self._main_box.reorder_child(self._toolbar, 2)
		
	def _init_tab_decorators(self):
		"""
		Look for already open tabs and create decorators for them
		"""
		self._tab_decorators = {}
		self._active_tab_decorator = None
		active_view = self.window.get_active_view()
		views = self.window.get_views()

		for view in views:
			tab = Gedit.Tab.get_from_document(view.get_buffer())
			decorator = self._create_tab_decorator(tab, init=True)
			if view is active_view:
				self._active_tab_decorator = decorator
		
		self._log.debug("_init_tab_decorators: initialized %s decorators" % len(views))
		
		if len(views) > 0 and not self._active_tab_decorator:
			self._log.warning("_init_tab_decorators: no active decorator found")
	
	def _init_tool_actions(self):
		"""
		 - Load defined Tools
		 - create and init ToolActions from them
		 - hook them in the window UI
		 - create a map from extensions to lists of ToolActions
		"""
		
		# add a MenuToolButton with the tools menu to the toolbar afterwards
		# FIXME: this is quite hacky
		menu = Gtk.Menu()
		
		# this is used for enable/disable actions by name
		# None stands for every extension
		self._tool_action_extensions = { None : [] }
		
		self._tool_action_group = Gtk.ActionGroup("LaTeXPluginToolActions")
			
		items_ui = ""
		
		self._action_handlers = {}
		
		i = 1					# counting tool actions
		accel_counter = 1		# counting tool actions without custom accel
		for tool in self._preferences.tools:
			# hopefully unique action name
			name = "Tool%sAction" % i
			
			# update extension-tool mapping
			for extension in tool.extensions:
				try:
					self._tool_action_extensions[extension].append(name)
				except KeyError:
					# extension not yet mapped
					self._tool_action_extensions[extension] = [name]
			
			# create action
			action = ToolAction(tool)
			gtk_action = Gtk.Action(name, action.label, action.tooltip, action.stock_id)
			self._action_handlers[gtk_action] = gtk_action.connect("activate", lambda gtk_action, action: action.activate(self._window_context), action)
			
			if not tool.accelerator is None and len(tool.accelerator) > 0:
				# TODO: validate accelerator!
				self._tool_action_group.add_action_with_accel(gtk_action, tool.accelerator)
			else:
				self._tool_action_group.add_action_with_accel(gtk_action, "<Ctrl><Alt>%s" % accel_counter)
				accel_counter += 1
			
			# add to MenuToolBar menu
			# FIXME: GtkWarning: gtk_accel_label_set_accel_closure: assertion `gtk_accel_group_from_accel_closure (accel_closure) != NULL' failed
			menu.add(gtk_action.create_menu_item())
			
			# add UI definition
			items_ui += """<menuitem action="%s" />""" % name
			
			i += 1
		
		tool_ui = self._tool_ui_template.substitute({"items" : items_ui})
		
		self._ui_manager.insert_action_group(self._tool_action_group, -1)
		self._tool_ui_id = self._ui_manager.add_ui_from_string(tool_ui)
		
		# add a MenuToolButton with the tools menu to the toolbar
		self._menu_tool_button = Gtk.MenuToolButton.new_from_stock(Gtk.STOCK_CONVERT)
		self._menu_tool_button.set_menu(menu)
		self._menu_tool_button.show_all()
		self._toolbar.insert(self._menu_tool_button, -1)
	
	def save_file(self):
		"""
		Trigger the 'Save' action
		
		(used by ToolAction before tool run)
		"""
		self._save_action.activate()
	
	def _on_tools_changed(self):
		# FIXME: tools reload doesn't work
		# UPDATE: should work now
		
		# see IPreferencesMonitor._on_tools_changed
		self._log.debug("_on_tools_changed")
		
		# remove tool actions and ui
		self._ui_manager.remove_ui(self._tool_ui_id)
		for gtk_action in self._action_handlers:
			gtk_action.disconnect(self._action_handlers[gtk_action])
			self._tool_action_group.remove_action(gtk_action)
		self._ui_manager.remove_action_group(self._tool_action_group)

		# remove MenuToolButton
		self._toolbar.remove(self._menu_tool_button)
		
		# re-init tool actions
		self._init_tool_actions()
		
		# re-adjust action states
		self.adjust(self._active_tab_decorator)
	
	def activate_tab(self, file):
		"""
		Activate the GeditTab containing the given File or open a new
		tab for it (this is called by the WindowContext)
		
		@param file: a File object
		"""
		for tab, tab_decorator in self._tab_decorators.iteritems():
			if tab_decorator.file and tab_decorator.file == file:
				self.window.set_active_tab(tab)
				return
		
		# not found, open file in a new tab...

		uri = file.uri
		gfile = Gio.file_new_for_uri(uri)

		if Gedit.utils_is_valid_location(gfile):
			self._log.debug("GeditWindow.create_tab_from_uri(%s)" % uri)
			self.window.create_tab_from_location(
							gfile, Gedit.encoding_get_current(),
							1, 1, False, True)
		else:
			self._log.error("Gedit.utils.uri_is_valid(%s) = False" % uri)
	
	def disable(self):
		"""
		Called if there are no more tabs after tab_removed
		"""
		self._toolbar.hide()
		
		# disable all actions
		for name in self._action_objects.iterkeys():
			self._action_group.get_action(name).set_visible(False)
			
		# disable all tool actions
		for l in self._tool_action_extensions.values():
			for name in l:
				self._tool_action_group.get_action(name).set_sensitive(False)
				
		# remove all side views
		side_views = self._window_side_views + self._side_views
		for view in side_views:
			self.window.get_side_panel().remove_item(view)
			if view in self._side_views: self._side_views.remove(view)
			if view in self._window_side_views: self._window_side_views.remove(view)
			
		# remove all bottom views
		bottom_views = self._window_bottom_views + self._bottom_views
		for view in bottom_views:
			self.window.get_bottom_panel().remove_item(view)
			if view in self._bottom_views: self._bottom_views.remove(view)
			if view in self._window_bottom_views: self._window_bottom_views.remove(view)
	
	def adjust(self, tab_decorator):
		"""
		Adjust actions and views according to the currently active TabDecorator
		(the file type it contains)
		
		Called by 
		 * _on_active_tab_changed()
		 * GeditTabDecorator when the Editor instance changes 
		"""

		# TODO: improve and simplify this!
		
		extension = tab_decorator.extension
		
		self._log.debug("---------- ADJUST: %s" % (extension))
		
		# FIXME: a hack again...
		# the toolbar should hide when it doesn't contain any visible items
		latex_extensions = self._preferences.get("LatexExtensions", ".tex").split(" ")
		show_toolbar = self._preferences.get_bool("ShowLatexToolbar", True)
		if show_toolbar and extension in latex_extensions:
			self._toolbar.show()
		else:
			self._toolbar.hide()
		
		#
		# adjust actions
		#
		# FIXME: we always get the state of the new decorator after tab change
		# but we need to save the one of the old decorator
		#
		# FIXME: we are dealing with sets so saving the index as selection state
		# is nonsense
		#
		
		# disable all actions
		for name in self._action_objects:
			self._action_group.get_action(name).set_visible(False)
		
		# disable all tool actions
		for l in self._tool_action_extensions.values():
			for name in l:
				self._tool_action_group.get_action(name).set_sensitive(False)
		
		
		# enable the actions for all extensions
		for name in self._action_extensions[None]:
			self._action_group.get_action(name).set_visible(True)
		
		# enable the actions registered for the extension
		if extension:
			try:
				for name in self._action_extensions[extension]:
					self._action_group.get_action(name).set_visible(True)
			except KeyError:
				pass
		
		
		# enable the tool actions that apply for all extensions
		for name in self._tool_action_extensions[None]:
			self._tool_action_group.get_action(name).set_sensitive(True)
		
		# enable the tool actions that apply for this extension
		if extension:
			try:
				for name in self._tool_action_extensions[extension]:
					self._tool_action_group.get_action(name).set_sensitive(True)
			except KeyError:
				pass
		
		#
		# adjust editor-scope views
		#
		
		# determine set of side/bottom views BEFORE
		
		before_side_views = set(self._side_views)
		before_bottom_views = set(self._bottom_views)
		
		# determine set of side/bottom views AFTER
		
		after_side_views = set()
		after_bottom_views = set()
		
		if tab_decorator.editor:
			editor_views = self._window_context.editor_scope_views[tab_decorator.editor]
			for id, view in editor_views.iteritems():
				if isinstance(view, BottomView):
					after_bottom_views.add(view)
				elif isinstance(view, SideView):
					after_side_views.add(view)
				else:
					raise RuntimeError("Invalid view type: %s" % view)
		
		# remove BEFORE.difference(AFTER)
		for view in before_side_views.difference(after_side_views):
			self.window.get_side_panel().remove_item(view)
			self._side_views.remove(view)
		
		for view in before_bottom_views.difference(after_bottom_views):
			self.window.get_bottom_panel().remove_item(view)
			self._bottom_views.remove(view)
		
		# add AFTER.difference(BEFORE)
		i = 1
		for view in after_side_views.difference(before_side_views):
			i+=1
			self.window.get_side_panel().add_item(view, "after_side_view_id" + str(i), view.label, view.icon)
			self._side_views.append(view)
		i = 1	
		for view in after_bottom_views.difference(before_bottom_views):
			i+=1
			print view.label, view.icon
			self.window.get_bottom_panel().add_item(view, "bottom_view_id" + str(i),view.label, view.icon)
			self._bottom_views.append(view)
			
		
		#
		# adjust window-scope views
		#
		
		# determine set of side/bottom views BEFORE
		
		before_window_side_views = set(self._window_side_views)
		before_window_bottom_views = set(self._window_bottom_views)
		
		# determine set of side/bottom views AFTER
		
		after_window_side_views = set()
		after_window_bottom_views = set()
		
		try:
			for id, clazz in WINDOW_SCOPE_VIEWS[extension].iteritems():
				
				# find or create View instance
				view = None
				try:
					view = self._views[id]
				except KeyError:
					view = clazz.__new__(clazz)
					clazz.__init__(view, self._window_context)
					self._views[id] = view
				
				if isinstance(view, BottomView):
					after_window_bottom_views.add(view)
				elif isinstance(view, SideView):
					after_window_side_views.add(view)
				else:
					raise RuntimeError("Invalid view type: %s" % view)
		except KeyError:
			self._log.debug("No window-scope views for this extension")
			
		# remove BEFORE.difference(AFTER)
		for view in before_window_side_views.difference(after_window_side_views):
			self.window.get_side_panel().remove_item(view)
			self._window_side_views.remove(view)
		
		for view in before_window_bottom_views.difference(after_window_bottom_views):
			self.window.get_bottom_panel().remove_item(view)
			self._window_bottom_views.remove(view)
			
		# add AFTER.difference(BEFORE)
		i = 1
		for view in after_window_side_views.difference(before_window_side_views):
			i += 1
			self.window.get_side_panel().add_item(view,"WHATView"+ str(i), view.label, view.icon)
			self._window_side_views.append(view)
			
		for view in after_window_bottom_views.difference(before_window_bottom_views):
			self.window.get_bottom_panel().add_item(view, view.label, view.icon)
			self._window_bottom_views.append(view)
		
		#
		# update window context
		#
		self._window_context.window_scope_views = self._views
	
	def _on_tab_added(self, window, tab):
		"""
		A new tab has been added
		
		@param window: Gedit.Window object
		@param tab: Gedit.Tab object
		"""
		self._log.debug("tab_added")
		
		if tab in self._tab_decorators:
			self._log.warning("There is already a decorator for tab %s" % tab)
			return
		
		self._create_tab_decorator(tab)
			
	def _on_tab_removed(self, window, tab):
		"""
		A tab has been closed
		
		@param window: GeditWindow
		@param tab: the closed GeditTab
		"""
		self._log.debug("tab_removed")
		
		# As we don't call GeditWindowDecorator.adjust() if the new 
		# tab is not the active one (for example, when opening several 
		# files at once, see GeditTabDecorator._adjust_editor()), 
		# it may happen that self._selected_side_views[tab] is not set.
		if self._tab_decorators[tab] in self._selected_side_views:
			del self._selected_side_views[self._tab_decorators[tab]]
		if self._tab_decorators[tab] in self._selected_bottom_views:
			del self._selected_bottom_views[self._tab_decorators[tab]]
		
		self._tab_decorators[tab].destroy()
		if self._active_tab_decorator == self._tab_decorators[tab]:
			self._active_tab_decorator = None

		del self._tab_decorators[tab]
		
		if len(self._tab_decorators) == 0:
			# no more tabs
			self.disable()
	
	def _on_active_tab_changed(self, window, tab):
		"""
		The active tab has changed
		
		@param window: the GeditWindow
		@param tab: the activated GeditTab
		"""
		self._log.debug("active_tab_changed")
		
		if tab in self._tab_decorators.keys():
			decorator = self._tab_decorators[tab]
		else:
			# (on Gedit startup 'tab-changed' comes before 'tab-added')
			# remember: init=True crashes the plugin here!
			decorator = self._create_tab_decorator(tab)
		
		self._active_tab_decorator = decorator
		
		# adjust actions and views
		self.adjust(decorator)
	
	def _create_tab_decorator(self, tab, init=False):
		"""
		Create a new GeditTabDecorator for a GeditTab
		"""
		decorator = GeditTabDecorator(self, tab, init)
		self._tab_decorators[tab] = decorator
		return decorator