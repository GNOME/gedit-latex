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
views
"""

import gtk
from gtk.gdk import Pixbuf, pixbuf_new_from_file
from logging import getLogger

from preferences import Preferences, IPreferencesMonitor
from base.resources import find_resource
from base import View, BottomView
from issues import Issue
from util import escape


class IssueView(BottomView, IPreferencesMonitor):
	"""
	"""
	
	_log = getLogger("IssueView")
	
	label = "Issues"
	icon = gtk.STOCK_DIALOG_INFO
	scope = View.SCOPE_EDITOR
	
	def init(self, context):
		self._log.debug("init")
		
		self._preferences = Preferences()
		self._show_tasks = self._preferences.get_bool("IssuesShowTasks", True)
		self._show_warnings = self._preferences.get_bool("IssuesShowWarnings", True)
		
		self._context = context
		
		self._icons = { Issue.SEVERITY_WARNING : pixbuf_new_from_file(find_resource("icons/warning.png")), 
						Issue.SEVERITY_ERROR : pixbuf_new_from_file(find_resource("icons/error.png")), 
			   			Issue.SEVERITY_INFO : None,
			   			Issue.SEVERITY_TASK : pixbuf_new_from_file(find_resource("icons/task.png")) }
		
		self._store = gtk.ListStore(Pixbuf, str, str, object)
		
		self._view = gtk.TreeView(self._store)
		
		column = gtk.TreeViewColumn()
		column.set_title("Message")
		
		pixbuf_renderer = gtk.CellRendererPixbuf()
		column.pack_start(pixbuf_renderer, False)
		column.add_attribute(pixbuf_renderer, "pixbuf", 0)
		
		text_renderer = gtk.CellRendererText()
		column.pack_start(text_renderer, True)
		column.add_attribute(text_renderer, "markup", 1)
		
		self._view.append_column(column)
		self._view.insert_column_with_attributes(-1, "File", gtk.CellRendererText(), markup=2)
		self._view.connect("row-activated", self._on_row_activated)
		
		self._scr = gtk.ScrolledWindow()
		
		self._scr.add(self._view)
		self._scr.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self._scr.set_shadow_type(gtk.SHADOW_IN)
		
		self.pack_start(self._scr, True)
		
		# toolbar
		
		self._button_warnings = gtk.ToggleToolButton()
		self._button_warnings.set_tooltip_text("Show/Hide Warnings")
		image = gtk.Image()
		image.set_from_file(find_resource("icons/warning.png"))
		self._button_warnings.set_icon_widget(image)
		self._button_warnings.set_active(self._show_warnings)
		self._button_warnings.connect("toggled", self.__on_warnings_toggled)
		
		self._button_tasks = gtk.ToggleToolButton()
		self._button_tasks.set_tooltip_text("Show/Hide Tasks")
		imageTask = gtk.Image()
		imageTask.set_from_file(find_resource("icons/task.png"))
		self._button_tasks.set_icon_widget(imageTask)
		self._button_tasks.set_active(self._show_tasks)
		self._button_tasks.connect("toggled", self.__on_tasks_toggled)
		
		toolbar = gtk.Toolbar()
		toolbar.set_orientation(gtk.ORIENTATION_VERTICAL)
		toolbar.set_style(gtk.TOOLBAR_ICONS)
		toolbar.set_icon_size(gtk.ICON_SIZE_MENU)
		toolbar.insert(self._button_warnings, -1)
		toolbar.insert(self._button_tasks, -1)
		
		self.pack_start(toolbar, False)
		
		self._issues = []
		self._preferences.register_monitor(self)
	
	def _on_row_activated(self, view, path, column):
		"""
		A row has been double-clicked on
		"""
		it = self._store.get_iter(path)
		issue = self._store.get(self._store.get_iter(path), 3)[0]
		
		self._context.activate_editor(issue.file)
		
		# TODO:
	
	def _on_value_changed(self, key, value):
		if key == "IssuesShowWarnings" or key == "IssuesShowTasks":
			# update filter
			self._store.clear()
			for issue, local in self._issues:
				self.__append_issue_filtered(issue, local)
	
	def __on_tasks_toggled(self, togglebutton):
		self._show_tasks = togglebutton.get_active()
		self._preferences.set("IssuesShowTasks", self._show_tasks)
		
	def __on_warnings_toggled(self, togglebutton):
		self._show_warnings = togglebutton.get_active()
		self._preferences.set("IssuesShowWarnings", self._show_warnings)
	
	def clear(self):
		"""
		Remove all issues from the view
		"""
		self.assure_init()
		self._store.clear()
		self._issues = []
	
	def append_issue(self, issue, local=True):
		"""
		Append a new Issue to the view
		
		@param issue: the Issue object
		@param local: indicates whether the Issue occured in the edited file or not
		"""
		self.assure_init()
		self._issues.append((issue, local))
		self.__append_issue_filtered(issue, local)
	
	def __append_issue_filtered(self, issue, local):
		if issue.severity == Issue.SEVERITY_WARNING:
			if self._show_warnings:
				self.__do_append_issue(issue, local)
		elif issue.severity == Issue.SEVERITY_TASK:
			if self._show_tasks:
				self.__do_append_issue(issue, local)
		else:
			self.__do_append_issue(issue, local)
	
	def __do_append_issue(self, issue, local):
		if local:
			message = issue.message
			filename = escape(issue.file.basename)
		else:
			message = "<span color='%s'>%s</span>" % (self._preferences.get("LightForeground", "#7f7f7f"), issue.message)
			filename = "<span color='%s'>%s</span>" % (self._preferences.get("LightForeground", "#7f7f7f"), issue.file.basename)
		self._store.append([self._icons[issue.severity], message, filename, issue])
		
		
		
		