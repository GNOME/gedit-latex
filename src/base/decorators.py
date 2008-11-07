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
base.decorators

These classes are 'attached' to the according gedit objects. They form the
extension point.
"""

from logging import getLogger
import gedit
import gtk
import gobject

from config import UI, ACTION_OBJECTS, ACTION_EXTENSIONS, WINDOW_SCOPE_VIEWS, EDITOR_SCOPE_VIEWS, EDITORS
from views import ToolView
from . import File, View, WindowContext
from ..tools import ToolAction
from ..preferences import Preferences, IPreferencesMonitor


# FIXME: there is no 'active_tab_changed' after the last 'tab_removed'!

# TODO: maybe create ActionDelegate for GeditWindowDecorator


#
# workaround for MenuToolItem
# see http://library.gnome.org/devel/pygtk/stable/class-gtkaction.html#method-gtkaction--set-tool-item-type
#
class MenuToolAction(gtk.Action):
	__gtype_name__ = "MenuToolAction"

gobject.type_register(MenuToolAction)
# needs PyGTK 2.10
MenuToolAction.set_tool_item_type(gtk.MenuToolButton)
		

class GeditWindowDecorator(IPreferencesMonitor):
	"""
	This class
	 - manages the GeditTabDecorators
	 - hooks the plugin actions as menu items and tool items
	 - installs side and bottom panel views
	"""
	
	_log = getLogger("GeditWindowDecorator")
	
	def __init__(self, window):
		self._window = window
		
		self._preferences = Preferences()
		self._preferences.register_monitor(self)
		
		#
		# initialize context object
		#
		self._window_context = WindowContext(self, EDITOR_SCOPE_VIEWS)
		
		
		self._init_actions()
		self._init_tool_actions()
		
		self._init_tab_decorators()
		
		self._init_views()
		
		
		# create the DBUS service for inverse search
		# FIXME: there should be some interface for decoupling this from the base layer
		try:
			from ..latex.inversesearch import InverseSearchService
			self._inverse_search_service = InverseSearchService(self._window_context)
		except Exception, e:
			self._log.error("Failed to create InverseSearchService: %s" % e)
		
		
		#
		# listen to tab signals
		#
		self._tab_signal_handlers = [
				self._window.connect("tab_added", self._on_tab_added),
				self._window.connect("tab_removed", self._on_tab_removed),
				self._window.connect("active_tab_changed", self._on_active_tab_changed),
				self._window.connect("destroy", self._on_window_destroyed) ]
	
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
		self._window.get_bottom_panel().add_item(tool_view, tool_view.label, tool_view.icon)
		#self._window_bottom_views.append(tool_view)
		
		# update window context
		self._window_context.set_window_views(self._views)
	
	def _init_actions(self):
		"""
		Merge the plugin's UI definition with the one of gedit and hook the actions
		"""
		self._ui_manager = self._window.get_ui_manager()
		self._action_group = gtk.ActionGroup("LaTeXPluginActions")
		
		# add plugin actions
		
		for name, action in ACTION_OBJECTS.iteritems():
			
			# FIXME: this is quite hacky
			
			if name in ["LaTeXFontFamilyAction", "LaTeXStructureAction", "LaTeXMathAction"]:
				gtk_action = MenuToolAction(name, action.label, action.tooltip, action.stock_id)
			else:
				gtk_action = gtk.Action(name, action.label, action.tooltip, action.stock_id)
			
			gtk_action.connect("activate", self._on_action_activated, action)
			self._action_group.add_action_with_accel(gtk_action, action.accelerator)
		
		# merge
		self._ui_manager.insert_action_group(self._action_group, -1)
		self._ui_id = self._ui_manager.add_ui_from_string(UI)
		
		#
		# hook the toolbar
		#
		self._toolbar = self._ui_manager.get_widget("/LaTeXToolbar")
		self._toolbar.set_style(gtk.TOOLBAR_BOTH_HORIZ)
		
		self._main_box = self._window.get_children()[0]
		self._main_box.pack_start(self._toolbar, False)
		self._main_box.reorder_child(self._toolbar, 2)
		
		self._toolbar.show()
	
	def _init_tab_decorators(self):
		"""
		Look for already open tabs and create decorators for them
		"""
		self._tab_decorators = {}
		self._active_tab_decorator = None
		active_view = self._window.get_active_view()
		views = self._window.get_views()
		for view in views:
			tab = gedit.tab_get_from_document(view.get_buffer())
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
		
		# TODO: unload first, for now this may just init
		
		# this is used for enable/disable actions by name
		# None stands for every extension
		self._tool_action_extensions = { None : [] }
		
		self._tool_action_group = gtk.ActionGroup("LaTeXPluginToolActions")
		
		
		tool_ui = """<ui>
			<menubar name="MenuBar">
				<menu name="ToolsMenu" action="Tools">
					<placeholder name="ToolsOps_1">"""
					
		
		i = 1
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
			action = ToolAction()
			action.init(tool)
			gtk_action = gtk.Action(name, action.label, action.tooltip, action.stock_id)
			gtk_action.connect("activate", self._on_action_activated, action)
			
			# TODO: allow custom accelerator
			self._tool_action_group.add_action_with_accel(gtk_action, "<Ctrl><Alt>%s" % i)
			
			# add UI definition
			tool_ui += """<menuitem action="%s" />""" % name
			
			i += 1
		
		
		tool_ui += """</placeholder>
					</menu>
				</menubar>
			</ui>"""
		
		self._ui_manager.insert_action_group(self._tool_action_group, -1)
		self._tool_ui_id = self._ui_manager.add_ui_from_string(tool_ui)
	
	def _on_tools_changed(self):
		# see IPreferencesMonitor._on_tools_changed
		self._log.debug("_on_tools_changed")
		
		# remove actions and ui
		self._ui_manager.remove_action_group(self._tool_action_group)
		self._ui_manager.remove_ui(self._tool_ui_id)
		
		# re-init tool actions
		self._init_tool_actions()
		
		# re-adjust action states
		self.adjust(self._active_tab_decorator)
	
	def _on_action_activated(self, gtk_action, action):
		"""
		An action has been activated - propagate to action object
		
		@param gtk_action: the activated gtk.Action
		@param action: a base.Action object for the activated action (not a gtk.Action)
		"""
		action.activate(self._window_context)
	
	def activate_tab(self, file):
		"""
		Activate the GeditTab containing the given File or open a new
		tab for it (this is called by the WindowContext)
		
		@param file: a File object
		"""
		for tab, tab_decorator in self._tab_decorators.iteritems():
			if tab_decorator.file and tab_decorator.file == file:
				self._window.set_active_tab(tab)
				return
		
		# not found, open file in a new tab...
		
		self._window.create_tab_from_uri(file.uri, gedit.encoding_get_current(), 1, False, True)
	
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
		
		self._log.debug("adjust: %s" % (extension))
		
		# FIXME: a hack again...
		# the toolbar should hide when it doesn't contain any visible items
		if extension == ".tex":
			self._toolbar.show()
		else:
			self._toolbar.hide()
		
		#
		# adjust actions
		#
		# FIXME: we always get the state of the new decorator after tab change
		# but we need to save the one of the old decorator
		#
		
		# disable all actions
		for name in ACTION_OBJECTS.keys():
			self._action_group.get_action(name).set_visible(False)
		
		# disable all tool actions
		for l in self._tool_action_extensions.values():
			for name in l:
				self._tool_action_group.get_action(name).set_sensitive(False)
		
		
		# enable the actions for all extensions
		for name in ACTION_EXTENSIONS[None]:
			self._action_group.get_action(name).set_visible(True)
		
		# enable the actions registered for the extension
		if extension:
			try:
				for name in ACTION_EXTENSIONS[extension]:
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
		# save selection state
		#
		self._selected_bottom_views[tab_decorator] = self._get_selected_bottom_view()
		self._selected_side_views[tab_decorator] = self._get_selected_side_view()
		
		#
		# adjust editor-scope views
		#
		
		# hide all
		for view in self._side_views:
			self._window.get_side_panel().remove_item(view)
			self._side_views.remove(view)
		
		for view in self._bottom_views:
			self._window.get_bottom_panel().remove_item(view)
			self._bottom_views.remove(view)
			
		# show editor scope views
		if tab_decorator.editor:
			editor_views = self._window_context.get_editor_views(tab_decorator.editor)
			for id, view in editor_views.iteritems():
				panel = None
				if view.position == View.POSITION_BOTTOM:
					self._window.get_bottom_panel().add_item(view, view.label, view.icon)
					self._bottom_views.append(view)
				elif view.position == View.POSITION_SIDE:
					self._window.get_side_panel().add_item(view, view.label, view.icon)
					self._side_views.append(view)
					
				else:
					raise RuntimeError("Invalid position: %s" % view.position)
		
		#
		# adjust window-scope views
		#
		
		# hide all
		for view in self._window_side_views:
			self._window.get_side_panel().remove_item(view)
			self._window_side_views.remove(view)
		
		for view in self._window_bottom_views:
			self._window.get_bottom_panel().remove_item(view)
			self._window_bottom_views.remove(view)
			
		# show given views
		try:
			for id, clazz in WINDOW_SCOPE_VIEWS[extension].iteritems():
				
				view = None
				try:
					view = self._views[id]
				except KeyError:
					# create instance
					view = clazz.__new__(clazz)
					clazz.__init__(view, self._window_context)
					self._views[id] = view
				
				panel = None
				if view.position == View.POSITION_BOTTOM:
					self._window.get_bottom_panel().add_item(view, view.label, view.icon)
					self._window_bottom_views.append(view)
				elif view.position == View.POSITION_SIDE:
					self._window.get_side_panel().add_item(view, view.label, view.icon)
					self._window_side_views.append(view)
					
				else:
					raise RuntimeError("Invalid position: %s" % view.position)
		except KeyError:
			self._log.debug("No window-scope views for this extension")
		
		# update window context
		self._window_context.set_window_views(self._views)
		
		#
		# restore selection state
		#
		self._set_selected_bottom_view(self._selected_bottom_views[tab_decorator])
		self._set_selected_side_view(self._selected_side_views[tab_decorator])
	
	def _get_selected_bottom_view(self):
		notebook = self._window.get_bottom_panel().get_children()[0].get_children()[0]
		assert type(notebook) is gtk.Notebook
		
		return notebook.get_current_page()
	
	def _get_selected_side_view(self):
		notebook = self._window.get_side_panel().get_children()[1]
		assert type(notebook) is gtk.Notebook
		
		return notebook.get_current_page()
	
	def _set_selected_bottom_view(self, view):
		notebook = self._window.get_bottom_panel().get_children()[0].get_children()[0]
		assert type(notebook) is gtk.Notebook
		
		self._log.debug("_set_selected_bottom_view: %s" % view)
		
		notebook.set_current_page(view)
	
	def _set_selected_side_view(self, view):
		notebook = self._window.get_side_panel().get_children()[1]
		assert type(notebook) is gtk.Notebook
		
		self._log.debug("_set_selected_side_view: %s" % view)
		
		notebook.set_current_page(view)
	
	def _on_tab_added(self, window, tab):
		self._log.debug("tab_added")
		
#		if not tab in self._tab_decorators.keys():
#			self._create_tab_decorator(tab)
			
	def _on_tab_removed(self, window, tab):
		"""
		A tab has been closed
		
		@param window: GeditWindow
		@param tab: the closed GeditTab
		"""
		self._log.debug("tab_removed")
		
		self._tab_decorators[tab].destroy()
		del self._tab_decorators[tab]
	
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
			# on gedit startup 'tab-changed' comes before 'tab-added'
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
	
	def _on_window_destroyed(self, object):
		"""
		The gtk.Window received the 'destroy' signal as a gtk.Object
		"""
		self._log.debug("received 'destroy'")
		
		self._preferences.save()
	
	def destroy(self):
		#
		# disconnect from tab signals
		#
		for id in self._tab_signal_handlers:
			self._window.disconnect(id)
		#
		# destroy tab decorators
		#
		for decorator in self._tab_decorators:
			decorator.destroy()


class GeditTabDecorator(object):
	"""
	This monitors the opened file and manages the Editor objects
	according to the current file extension
	"""
	
	_log = getLogger("GeditTabDecorator")
	
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
		self._text_buffer.connect("loaded", self._on_load)
		self._text_buffer.connect("saved", self._on_save)
	
	@property
	def tab(self):
		return self._tab
	
	def _on_load(self, document, param):
		"""
		A file has been loaded
		"""
		self._log.debug("loaded")
		
		self._adjust_editor()
	
	def _on_save(self, document, param):
		"""
		The file has been saved
		"""
		self._log.debug("saved")
		
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
		file = File(self._text_buffer.get_uri())
		if file != self._file:
			self._file = file
			
			# URI has changed - manage the editor instance
			if self._editor:
				# editor is present - destroy it
				self._editor.destroy()
				self._editor = None

			extension = file.extension.lower()

			# create new editor instance
			if extension in EDITORS.keys():
				editor_class = EDITORS[extension]
				
				self._editor = editor_class.__new__(editor_class)
				editor_class.__init__(self._editor, self, file)
			
			# tell WindowDecorator to adjust actions
			self._window_decorator.adjust(self)

			# URI has changed
			return True
		else:
			return False
	
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
		if self._file:
			return self._file.extension.lower()
		else:
			return None
	
	def destroy(self):
		if self._editor:
			self._editor.destroy()
	
	