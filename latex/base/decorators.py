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

from logging import getLogger
from gi.repository import Gedit, Gtk, Gio
import string

from config import UI, WINDOW_SCOPE_VIEWS, EDITOR_SCOPE_VIEWS, EDITORS, ACTIONS
from . import File, SideView, BottomView, WindowContext
from ..preferences import Preferences, IPreferencesMonitor

# TODO: maybe create ActionDelegate for GeditWindowDecorator
		
class GeditWindowDecorator(IPreferencesMonitor):
	"""
	This class
	 - manages the GeditTabDecorators
	 - hooks the plugin actions as menu items
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
		
		# the order is important!
		self._init_actions()
		self._init_views()
		self._init_tab_decorators()
		
		# FIXME: find another way to save a document
		self._save_action = self._ui_manager.get_action("/MenuBar/FileMenu/FileSaveMenu")
		
		#
		# listen to tab signals
		#
		self._signal_handlers = [
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
		
		# update window context
		self._window_context.window_scope_views = self._views
	
	def _init_actions(self):
		"""
		Merge the plugin's UI definition with the one of Gedit and hook the actions
		"""
		self._ui_manager = self._window.get_ui_manager()
		self._action_group = Gtk.ActionGroup("LaTeXPluginActions")
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
		
		self._main_box = self._window.get_children()[0]
		self._main_box.pack_start(self._toolbar, False, True, 0)
		self._main_box.reorder_child(self._toolbar, 2)
		
	def _init_tab_decorators(self):
		"""
		Look for already open tabs and create decorators for them
		"""
		self._tab_decorators = {}
		self._active_tab_decorator = None
		active_view = self._window.get_active_view()
		views = self._window.get_views()

		for view in views:
			tab = Gedit.Tab.get_from_document(view.get_buffer())
			decorator = self._create_tab_decorator(tab, init=True)
			if view is active_view:
				self._active_tab_decorator = decorator
		
		self._log.debug("_init_tab_decorators: initialized %s decorators" % len(views))
		
		if len(views) > 0 and not self._active_tab_decorator:
			self._log.warning("_init_tab_decorators: no active decorator found")
	
	def save_file(self):
		"""
		Trigger the 'Save' action
		
		(used by ToolAction before tool run)
		"""
		self._save_action.activate()
	
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

		uri = file.uri
		gfile = Gio.file_new_for_uri(uri)

		if Gedit.utils_is_valid_location(gfile):
			self._log.debug("GeditWindow.create_tab_from_uri(%s)" % uri)
			self._window.create_tab_from_location(
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
			
		# remove all side views
		side_views = self._window_side_views + self._side_views
		for view in side_views:
			self._window.get_side_panel().remove_item(view)
			if view in self._side_views: self._side_views.remove(view)
			if view in self._window_side_views: self._window_side_views.remove(view)
			
		# remove all bottom views
		bottom_views = self._window_bottom_views + self._bottom_views
		for view in bottom_views:
			self._window.get_bottom_panel().remove_item(view)
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
		
		
		#
		# save selection state
		#
		self._selected_bottom_views[tab_decorator] = self._get_selected_bottom_view()
		self._selected_side_views[tab_decorator] = self._get_selected_side_view()
		
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
			self._window.get_side_panel().remove_item(view)
			self._side_views.remove(view)
		
		for view in before_bottom_views.difference(after_bottom_views):
			self._window.get_bottom_panel().remove_item(view)
			self._bottom_views.remove(view)
		
		# add AFTER.difference(BEFORE)
		i = 1
		for view in after_side_views.difference(before_side_views):
			i+=1
			self._window.get_side_panel().add_item(view, "after_side_view_id" + str(i), view.label, view.icon)
			self._side_views.append(view)
		i = 1	
		for view in after_bottom_views.difference(before_bottom_views):
			i+=1
			print view.label, view.icon
			self._window.get_bottom_panel().add_item(view, "bottom_view_id" + str(i),view.label, view.icon)
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
			self._window.get_side_panel().remove_item(view)
			self._window_side_views.remove(view)
		
		for view in before_window_bottom_views.difference(after_window_bottom_views):
			self._window.get_bottom_panel().remove_item(view)
			self._window_bottom_views.remove(view)
			
		# add AFTER.difference(BEFORE)
		i = 1
		for view in after_window_side_views.difference(before_window_side_views):
			i += 1
			self._window.get_side_panel().add_item(view,"WHATView"+ str(i), view.label, view.icon)
			self._window_side_views.append(view)
			
		for view in after_window_bottom_views.difference(before_window_bottom_views):
			self._window.get_bottom_panel().add_item(view, view.label, view.icon)
			self._window_bottom_views.append(view)
		
		#
		# update window context
		#
		self._window_context.window_scope_views = self._views
		
		#
		# restore selection state
		#
		self._set_selected_bottom_view(self._selected_bottom_views[tab_decorator])
		self._set_selected_side_view(self._selected_side_views[tab_decorator])

	def _get_selected_bottom_view(self):
		notebook = self._window.get_bottom_panel().get_children()[0].get_children()[0]
		assert type(notebook) is Gtk.Notebook
		
		return notebook.get_current_page()
	
	def _get_selected_side_view(self):
		notebook = self._window.get_side_panel().get_children()[1]
		assert type(notebook) is Gtk.Notebook
		
		return notebook.get_current_page()
	
	def _set_selected_bottom_view(self, view):
		notebook = self._window.get_bottom_panel().get_children()[0].get_children()[0]
		assert type(notebook) is Gtk.Notebook
		
		self._log.debug("_set_selected_bottom_view: %s" % view)
		
		notebook.set_current_page(view)
	
	def _set_selected_side_view(self, view):
		notebook = self._window.get_side_panel().get_children()[1]
		assert type(notebook) is Gtk.Notebook
		
		self._log.debug("_set_selected_side_view: %s" % view)
		
		notebook.set_current_page(view)
	
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
	
	def _on_window_destroyed(self, object):
		"""
		The Gtk.Window received the 'destroy' signal as a Gtk.Object
		"""
		self._log.debug("received 'destroy'")
		
		self.destroy()
	
	def destroy(self):
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
			self._window.disconnect(id)
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
		
		# remove actions
		self._ui_manager.remove_ui(self._ui_id)
		for clazz in self._action_objects:
			self._action_objects[clazz].unhook(self._action_group)
		self._ui_manager.remove_action_group(self._action_group)

		# unreference the Gedit window
		del self._window
		
		# destroy the window context
		self._window_context.destroy()
		del self._window_context
		
	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)
		

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
		self._signals_handlers = [
				self._text_buffer.connect("loaded", self._on_load),
				self._text_buffer.connect("saved", self._on_save)
		]
		
		self._log.debug("Created %s" % self)
		
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
		location = self._text_buffer.get_location()
		if location is None:
			# this happends when the plugin is activated in a running Gedit
			# and this decorator is created for the empty file
			
			self._log.debug("No file loaded")
			
			if self._window_decorator._window.get_active_view() == self._text_view:
				self._window_decorator.adjust(self)
			
		else:
			file = File(location.get_uri())
			
			if file == self._file:		# FIXME: != doesn't work for File...
				return False
			else:
				self._log.debug("_adjust_editor: URI has changed")
				
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
					self._log.warning("No editor class found for extension %s" % extension)
				
				# tell WindowDecorator to adjust actions
				# but only if this tab is the active tab
				if self._window_decorator._window.get_active_view() == self._text_view:
					self._window_decorator.adjust(self)
	
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

	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)
