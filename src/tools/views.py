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
base.views
"""

from logging import getLogger

#from Gtk.gdk import Pixbuf, pixbuf_new_from_file
from gi.repository import Gtk, GdkPixbuf


from ..base.resources import find_resource
from ..base import View, BottomView
from ..issues import Issue, IStructuredIssueHandler


class ToolView(BottomView, IStructuredIssueHandler):
	"""
	"""
	
	_log = getLogger("ToolView")
	
	label = "Tools"
	icon = Gtk.STOCK_CONVERT
	scope = View.SCOPE_WINDOW
	
	_ICON_RUN = GdkPixbuf.Pixbuf.new_from_file(find_resource("icons/run.png"))
	_ICON_FAIL = GdkPixbuf.Pixbuf.new_from_file(find_resource("icons/error.png"))
	_ICON_SUCCESS = GdkPixbuf.Pixbuf.new_from_file(find_resource("icons/okay.png"))
	_ICON_ERROR = GdkPixbuf.Pixbuf.new_from_file(find_resource("icons/error.png"))
	_ICON_WARNING = GdkPixbuf.Pixbuf.new_from_file(find_resource("icons/warning.png"))
	_ICON_ABORT = GdkPixbuf.Pixbuf.new_from_file(find_resource("icons/abort.png"))
	
	def __init__(self, context):
		BottomView.__init__(self, context)
		self._handlers = {}
		
	def init(self, context):
		self._log.debug("init")
		
		self._context = context
		
		self._scroll = Gtk.ScrolledWindow()
		self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scroll.set_shadow_type(Gtk.ShadowType.IN)
		
		self._store = Gtk.TreeStore(GdkPixbuf.Pixbuf, str, str, str, object)	# icon, message, file, line, Issue object
		
		self._view = Gtk.TreeView(self._store)
		
		column = Gtk.TreeViewColumn("Job")

		pixbuf_renderer = Gtk.CellRendererPixbuf()
		column.pack_start(pixbuf_renderer, False)
		column.add_attribute(pixbuf_renderer, "pixbuf", 0)
		
		text_renderer = Gtk.CellRendererText()
		column.pack_start(text_renderer, True)
		column.add_attribute(text_renderer, "markup", 1)
		
		self._view.append_column(column)
		self._view.append_column(Gtk.TreeViewColumn("File", Gtk.CellRendererText(), text=2))
		self._view.append_column(Gtk.TreeViewColumn("Line", Gtk.CellRendererText(), text=3))
		
		self._handlers[self._view] = self._view.connect("row-activated", self._on_row_activated)
		
		self._scroll.add(self._view)
		
		self.pack_start(self._scroll, True)
		
		# toolbar
		
		self._buttonCancel = Gtk.ToolButton(Gtk.STOCK_STOP)
		self._buttonCancel.set_sensitive(False)
		self._buttonCancel.set_tooltip_text("Abort Job")
		self._handlers[self._buttonCancel] = self._buttonCancel.connect("clicked", self._on_abort_clicked)
		
		self._buttonDetails = Gtk.ToolButton(Gtk.STOCK_INFO)
		self._buttonDetails.set_sensitive(False)
		self._buttonDetails.set_tooltip_text("Show Detailed Output")
		self._handlers[self._buttonDetails] = self._buttonDetails.connect("clicked", self._on_details_clicked)

		self._toolbar = Gtk.Toolbar()
		self._toolbar.set_style(Gtk.TOOLBAR_ICONS)
		self._toolbar.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)		# FIXME: deprecated???
		self._toolbar.set_orientation(Gtk.ORIENTATION_VERTICAL)
		self._toolbar.insert(self._buttonCancel, -1)
		self._toolbar.insert(self._buttonDetails, -1)

		self.pack_start(self._toolbar, False)
	
	def _on_abort_clicked(self, button):
		self._abort_method.__call__()
	
	def _on_details_clicked(self, button):
		"""
		The details button has been clicked
		"""
	
	def _on_row_activated(self, view, path, column):
		issue = self._store.get(self._store.get_iter(path), 4)[0]
		if issue:
			self._context.activate_editor(issue.file)
			if self._context.active_editor:
				self._context.active_editor.select_lines(issue.start)
			else:
				self._log.error("No Editor object for calling select_lines")
	
	def clear(self):
		self.assure_init()
		self._store.clear()
	
	def set_abort_enabled(self, enabled, method):
		# see issues.IStructuredIssueHandler.set_abort_enabled
		
		self._abort_method = method
		self._buttonCancel.set_sensitive(enabled)
	
	def add_partition(self, label, state, parent_partition_id=None):
		"""
		Add a new partition
		
		@param label: a label used in the UI
		@return: a unique id for the partition (here a Gtk.TreeIter)
		"""
		icon = None
		if state == "running":
			icon = self._ICON_RUN
		elif state == "succeeded":
			icon = self._ICON_SUCCESS
		elif state == "failed":
			icon = self._ICON_FAIL
		elif state == "aborted":
			icon = self._ICON_ABORT
			
		self._view.expand_all()
		
		return self._store.append(parent_partition_id, [icon, label, "", "", None])
	
	def set_partition_state(self, partition_id, state):
		# see IStructuredIssueHandler.set_partition_state
		
		icon = None
		if state == "running":
			icon = self._ICON_RUN
		elif state == "succeeded":
			icon = self._ICON_SUCCESS
		elif state == "failed":
			icon = self._ICON_FAIL
		elif state == "aborted":
			icon = self._ICON_ABORT
			
		self._store.set(partition_id, 0, icon)
	
	def append_issues(self, partition_id, issues):
		for issue in issues:
			icon = None
			if issue.severity == Issue.SEVERITY_WARNING:
				icon = self._ICON_WARNING
			elif issue.severity == Issue.SEVERITY_ERROR:
				icon = self._ICON_ERROR
			self._store.append(partition_id, [icon, issue.message, issue.file.basename, issue.start, issue])
			
			self._log.debug(str(issue))
			
		self._view.expand_all()
	
	def destroy(self):
		for obj in self._handlers:
			obj.disconnect(self._handlers[obj])
		BottomView.destroy(self)
	
