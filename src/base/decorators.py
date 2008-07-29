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

from ..latex.actions import LaTeXMenuAction, LaTeXNewAction, LaTeXCommentAction


# TODO: extensions and UI path should be asked from Action objects
# (build UI like for tool actions)


# FIXME: there is no 'active_tab_changed' after the last 'tab_removed'!

# TODO: unify the two action types so that e.g. adjust_actions() gets simpler

# TODO: maybe create ActionDelegate for WindowDecorator


ACTION_OBJECTS = { "LaTeXMenuAction" : LaTeXMenuAction(), 
				   "LaTeXNewAction" : LaTeXNewAction(),
				   "LaTeXCommentAction" : LaTeXCommentAction() }

ACTION_EXTENSIONS = { None : ["LaTeXNewAction"],
					  ".tex" : ["LaTeXMenuAction", "LaTeXCommentAction"] }


from ..tools import Tool, ToolJob, ToolAction


# TODO: this should come from configuration

TOOLS = [ Tool("LaTeX → PDF", [".tex"], [ToolJob("rubber $filename", True)], "Create a PDF from LaTeX source") ]


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
			</menu>
		</placeholder>
	</menubar>
	<toolbar name="LaTeXToolbar">
		<toolitem action="LaTeXNewAction" />
	</toolbar>
</ui>"""
	
	def __init__(self, window):
		self._window = window
		
		self._init_actions()
		self._load_tool_actions()
		
		self._init_tab_decorators()
		
		#
		# listen to tab signals
		#
		self._handler_ids = [
				self._window.connect("tab_added", self._on_tab_added),
				self._window.connect("tab_removed", self._on_tab_removed),
				self._window.connect("active_tab_changed", self._on_active_tab_changed) ]
	
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
		for view in self._window.get_views():
			tab = gedit.tab_get_from_document(view.get_buffer())
			decorator = self._create_tab_decorator(tab)
			if view is active_view:
				self._active_tab_decorator = adapter
	
	def _on_action_activated(self, gtk_action, action):
		"""
		An action has been activated - propagate to action object
		
		@param gtk_action: the activated gtk.Action
		@param action: a base.interface.Action object for the activated action (not a gtk.Action)
		"""
		active_editor = self._active_tab_decorator.editor
		action.activate(active_editor)
	
	def adjust_actions(self, extension):
		"""
		Enable/disable action according to the extension of the currently
		active file
		"""
		self._log.debug("adjust_actions(%s)" % extension)
		
		# TODO: improve this!
		
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
	
	def _on_tab_added(self, window, tab):
		if not tab in self._tab_decorators.keys():
			self._create_tab_decorator(tab)
			
	def _on_tab_removed(self, window, tab):
		"""
		A tab has been closed
		
		@param window: GeditWindow
		@param tab: the closed GeditTab
		"""
		self._tab_decorators[tab].destroy()
		del self._tab_decorators[tab]
	
	def _on_active_tab_changed(self, window, tab):
		"""
		The active tab has changed
		
		@param window: the GeditWindow
		@param tab: the activated GeditTab
		"""
		if tab in self._tab_decorators.keys():
			decorator = self._tab_decorators[tab]
		else:
			decorator = self._create_tab_decorator(tab)
		
		self._active_tab_decorator = decorator
		
		# enable/disable the right actions
		self.adjust_actions(decorator.extension)
	
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
		for id in self._handler_ids:
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
	according to the file extension
	"""
	
	_log = getLogger("GeditTabDecorator")
	
	def __init__(self, window_decorator, tab):
		self._window_decorator = window_decorator
		self._tab = tab
		self._text_buffer = tab.get_document()
		self._text_view = tab.get_view()
		
		self._editor = None
		self._editor_uri = None
		
		#
		# listen to GeditDocument signals
		#
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
			
			# tell WindowDecorator to adjust actions
			self._window_decorator.adjust_actions(ext)
			
			# eventually create new editor instance
			if ext in EDITORS.keys():
				editor_class = EDITORS[ext]
				
				self._editor = editor_class.__new__(editor_class)
				editor_class.__init__(self._editor, self, f)
				
				self._editor_uri = uri
				
			# URI has changed
			return True
		else:
			return False
	
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
	
	