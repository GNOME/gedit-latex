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

from ..latex.actions import LaTeXMenuAction, LaTeXNewAction, LaTeXCommentAction, LaTeXSpellCheckAction


# TODO: extensions and UI path should be asked from Action objects
# (build UI like for tool actions)


# FIXME: there is no 'active_tab_changed' after the last 'tab_removed'!

# TODO: maybe create ActionDelegate for WindowDecorator


ACTION_OBJECTS = { "LaTeXMenuAction" : LaTeXMenuAction(), 
				   "LaTeXNewAction" : LaTeXNewAction(),
				   "LaTeXCommentAction" : LaTeXCommentAction(),
				   "LaTeXSpellCheckAction" : LaTeXSpellCheckAction() }

ACTION_EXTENSIONS = { None : ["LaTeXNewAction"],
					  ".tex" : ["LaTeXMenuAction", "LaTeXCommentAction", "LaTeXSpellCheckAction"] }


from ..tools import Tool, Job, ToolAction


# TODO: this should come from configuration

TOOLS = [ Tool("LaTeX → PDF", [".tex"], [Job("rubber --inplace --maxerr -1 --pdf --short --force --warn all \"$filename\"", True), Job("gnome-open $shortname.pdf", True)], "Create a PDF from LaTeX source"),
		  Tool("Cleanup LaTeX Build", [".tex"], [Job("rm -f $directory/*.aux $directory/*.log", True)], "Remove LaTeX build files") ]


from . import View, WindowContext
from ..latex.views import LaTeXSymbolMapView


WINDOW_SCOPE_VIEWS = { ".tex" : {"LaTeXSymbolMapView" : LaTeXSymbolMapView } }


from views import ToolView


class GeditWindowDecorator(object):
	"""
	This class
	 - manages the GeditTabDecorators
	 - hooks the plugin actions as menu items and tool items
	 - installs side and bottom panel views
	"""
	
	_log = getLogger("GeditWindowDecorator")
	
	_ui = """
		<ui>
			<menubar name="MenuBar">
				<menu name="FileMenu" action="File">
					<placeholder name="FileOps_1">
						<menuitem action="LaTeXNewAction" />
					</placeholder>
				</menu>
				<placeholder name="ExtraMenu_1">
					<menu action="LaTeXMenuAction">
						<menuitem action="LaTeXCommentAction" />
						<menuitem action="LaTeXSpellCheckAction" />
					</menu>
				</placeholder>
			</menubar>
			<toolbar name="LaTeXToolbar">
				<toolitem action="LaTeXNewAction" />
			</toolbar>
		</ui>"""
	
	def __init__(self, window):
		self._window = window
		
		#
		# initialize context object
		#
		self._window_context = WindowContext()
		
		
		self._init_actions()
		self._load_tool_actions()
		
		self._init_tab_decorators()
		
		self._init_views()
		
		#
		# listen to tab signals
		#
		self._tab_signal_handlers = [
				self._window.connect("tab_added", self._on_tab_added),
				self._window.connect("tab_removed", self._on_tab_removed),
				self._window.connect("active_tab_changed", self._on_active_tab_changed) ]
	
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
		
		# update context
		self._window_context.views = self._views
	
	def _init_actions(self):
		"""
		Merge the plugin's UI definition with the one of gedit and hook the actions
		"""
		self._ui_manager = self._window.get_ui_manager()
		self._action_group = gtk.ActionGroup("LaTeXPluginActions")
		
		# add plugin actions
		
		for name, action in ACTION_OBJECTS.iteritems():
			 gtk_action = gtk.Action(name, action.label, action.tooltip, action.stock_id)
			 gtk_action.connect("activate", self._on_action_activated, action)
			 self._action_group.add_action_with_accel(gtk_action, action.accelerator)
		
		# merge
		self._ui_manager.insert_action_group(self._action_group, -1)
		self._ui_id = self._ui_manager.add_ui_from_string(self._ui)
		
		# TODO: hook toolbar
	
	def _load_tool_actions(self):
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
		for tool in TOOLS:
			# hopefully unique action name
			name = "Tool%sAction" % i
			
			# create mapping
			if tool.extensions:
				for extension in tool.extensions:
					try:
						self._tool_action_extensions[extension].append(name)
					except KeyError:
						# extension not yet mapped
						self._tool_action_extensions[extension] = [name]
			else:
				self._tool_action_extensions[None].append(name)
			
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
			decorator = self._create_tab_decorator(tab)
			if view is active_view:
				self._active_tab_decorator = decorator
		
		self._log.debug("_init_tab_decorators: initialized %s decorators" % len(views))
		
		if len(views) > 0 and not self._active_tab_decorator:
			self._log.warning("_init_tab_decorators: no active decorator found")
	
	def _on_action_activated(self, gtk_action, action):
		"""
		An action has been activated - propagate to action object
		
		@param gtk_action: the activated gtk.Action
		@param action: a base.Action object for the activated action (not a gtk.Action)
		"""
		action.activate(self._window_context)
	
	def activate_tab(self, file):
		"""
		Activate the GeditTab containing the given File (this is called through the WindowContext)
		
		@param file: a File object
		@raise KeyError: if no matching tab could be found
		"""
		self._log.debug("activate_tab: %s" % file)
		
		for tab, tab_decorator in self._tab_decorators.iteritems():
			self._log.debug("activate_tab: found %s" % tab_decorator.file)
			
			if tab_decorator.file == file:
				self._window.set_active_tab(tab)
				return
			
		raise KeyError
	
	def adjust(self, tab_decorator):
		"""
		Enable/disable action according to the extension of the currently
		active file
		"""
		
		# TODO: improve and simplify this!
		
		extension = tab_decorator.extension
		
		self._log.debug("adjust: %s, %s" % (tab_decorator, extension))
		
		#
		# adjust actions
		#
		# FIXME: we always get the state of the new decorator after tab change
		# but we need to save the one of the old decorator
		#
		
		# disable all actions
		for name in ACTION_OBJECTS.keys():
			self._action_group.get_action(name).set_sensitive(False)
		
		# disable all tool actions
		for l in self._tool_action_extensions.values():
			for name in l:
				self._tool_action_group.get_action(name).set_sensitive(False)
		
		
		# enable the actions for all extensions
		for name in ACTION_EXTENSIONS[None]:
			self._action_group.get_action(name).set_sensitive(True)
		
		# enable the actions registered for the extension
		if extension:
			try:
				for name in ACTION_EXTENSIONS[extension]:
					self._action_group.get_action(name).set_sensitive(True)
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
			
		# show given views
		if tab_decorator.editor:
			for id, view in tab_decorator.editor.views.iteritems():
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
		
		#
		# restore selection state
		#
		self._set_selected_bottom_view(self._selected_bottom_views[tab_decorator])
		self._set_selected_side_view(self._selected_side_views[tab_decorator])
		
		#
		# update context object
		#
		self._window_context.active_editor = self._active_tab_decorator.editor
	
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
		
		if not tab in self._tab_decorators.keys():
			self._create_tab_decorator(tab)
			
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
			decorator = self._create_tab_decorator(tab)
		
		self._active_tab_decorator = decorator
		
		# enable/disable the right actions
		self.adjust(decorator)
	
	def _create_tab_decorator(self, tab):
		"""
		Create a new GeditTabDecorator for a GeditTab
		"""
		decorator = GeditTabDecorator(self, tab)
		self._tab_decorators[tab] = decorator
		return decorator 
	
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


from ..latex.editor import LaTeXEditor
from . import File


EDITORS = {".tex" : LaTeXEditor}


class GeditTabDecorator(object):
	"""
	This monitors the opened file and manages the Editor objects
	according to the current file extension
	"""
	
	_log = getLogger("GeditTabDecorator")
	
	def __init__(self, window_decorator, tab):
		self._window_decorator = window_decorator
		self._tab = tab
		self._text_buffer = tab.get_document()
		self._text_view = tab.get_view()
		
		self._editor = None
		self._editor_uri = None
		
		# initially check the editor instance
		#
		# this needs to be done, because when we init for already opened files
		# (when plugin is activated in config) we get no "loaded" signal
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
		self._adjust_editor()
	
	def _on_save(self, document, param):
		"""
		The file has been saved
		"""
		if not self._adjust_editor():
			# if the editor has not changed
			if self._editor:
				self._editor.save()
	
	def _adjust_editor(self):
		"""
		Check if the URI has changed and manage Editor object according to
		file extension
		
		@return: True if the editor has changed
		"""
		uri = self._text_buffer.get_uri()
		if uri != self._editor_uri:
			# URI has changed - manage the editor instance
			if self._editor:
				# editor is present - destroy it
				self._editor.destroy()
				self._editor = None
			f = File(uri)
			ext = f.extension.lower()

			# create new editor instance
			if ext in EDITORS.keys():
				editor_class = EDITORS[ext]
				
				self._editor = editor_class.__new__(editor_class)
				editor_class.__init__(self._editor, self, f)
				
				self._editor_uri = uri
			
			# tell WindowDecorator to adjust actions
			self._window_decorator.adjust(self)
			
			# URI has changed
			return True
		else:
			return False
	
	@property
	def file(self):
		"""
		Return the File contained in the decorated tab
		"""
		
		# TODO: manage a File object, not the editor's URI
		
		if self._editor_uri:
			return File(self._editor_uri)
		else:
			return None
	
	@property
	def editor(self):
		return self._editor
	
	@property
	def extension(self):
		"""
		@return: the extension of the currently opened file
		"""
		uri = self._text_buffer.get_uri()
		if uri:
			f = File(uri)
			return f.extension.lower()
		return None
	
	def destroy(self):
		if self._editor:
			self._editor.destroy()
	
	