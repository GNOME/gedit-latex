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

import logging

from gi.repository import Gtk, GdkPixbuf

from ..resources import Resources
from ..panelview import PanelView
from ..issues import Issue, IStructuredIssueHandler
from ..gldefs import _

LOG = logging.getLogger(__name__)

class ToolView(PanelView, IStructuredIssueHandler):
    """
    """

    def __init__(self, context, editor):
        PanelView.__init__(self, context)
        self._handlers = {}

        self._ICON_RUN = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("run.png"))
        self._ICON_FAIL = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("error.png"))
        self._ICON_SUCCESS = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("okay.png"))
        self._ICON_ERROR = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("error.png"))
        self._ICON_WARNING = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("warning.png"))
        self._ICON_ABORT = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("abort.png"))

        grid = Gtk.Grid()
        self.add(grid)

        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_shadow_type(Gtk.ShadowType.IN)

        self._store = Gtk.TreeStore(GdkPixbuf.Pixbuf, str, str, str, object)    # icon, message, file, line, Issue object

        self._view = Gtk.TreeView(model=self._store)

        column = Gtk.TreeViewColumn(_("Job"))

        pixbuf_renderer = Gtk.CellRendererPixbuf()
        column.pack_start(pixbuf_renderer, False)
        column.add_attribute(pixbuf_renderer, "pixbuf", 0)

        text_renderer = Gtk.CellRendererText()
        column.pack_start(text_renderer, True)
        column.add_attribute(text_renderer, "markup", 1)

        self._view.append_column(column)
        self._view.append_column(Gtk.TreeViewColumn(_("File"), Gtk.CellRendererText(), text=2))
        self._view.append_column(Gtk.TreeViewColumn(_("Line"), Gtk.CellRendererText(), text=3))

        self._handlers[self._view] = self._view.connect("row-activated", self._on_row_activated)

        self._scroll.add(self._view)
        self._scroll.set_hexpand(True)

        grid.add(self._scroll)

        # toolbar

        self._button_cancel = Gtk.ToolButton(stock_id=Gtk.STOCK_STOP)
        self._button_cancel.set_sensitive(False)
        self._button_cancel.set_tooltip_text(_("Abort Job"))
        self._handlers[self._button_cancel] = self._button_cancel.connect("clicked", self._on_abort_clicked)

        self._button_details = Gtk.ToolButton(stock_id=Gtk.STOCK_INFO)
        self._button_details.set_sensitive(False)
        self._button_details.set_tooltip_text(_("Show Detailed Output"))
        self._handlers[self._button_details] = self._button_details.connect("clicked", self._on_details_clicked)

        self._toolbar = Gtk.Toolbar()
        self._toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        self._toolbar.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)
        self._toolbar.set_orientation(Gtk.Orientation.VERTICAL)
        self._toolbar.insert(self._button_cancel, -1)
        self._toolbar.insert(self._button_details, -1)
        self._toolbar.set_vexpand(True)

        grid.add(self._toolbar)

        # theme like gtk3
        ctx = self._scroll.get_style_context()
        ctx.set_junction_sides(Gtk.JunctionSides.RIGHT)

        ctx = self._toolbar.get_style_context()
        ctx.set_junction_sides(Gtk.JunctionSides.LEFT | Gtk.JunctionSides.RIGHT)
        ctx.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        self.show_all()

    def get_label(self):
        return _("Tools")

    def get_icon(self):
        return Gtk.Image.new_from_stock(Gtk.STOCK_CONVERT, Gtk.IconSize.MENU)

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
                LOG.error("No Editor object for calling select_lines")

    def clear(self):
        self._store.clear()

    def set_abort_enabled(self, enabled, method):
        # see issues.IStructuredIssueHandler.set_abort_enabled

        self._abort_method = method
        self._button_cancel.set_sensitive(enabled)

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

        self._store.set_value(partition_id, 0, icon)

    def append_issues(self, partition_id, issues):
        for issue in issues:
            icon = None
            if issue.severity == Issue.SEVERITY_WARNING:
                icon = self._ICON_WARNING
            elif issue.severity == Issue.SEVERITY_ERROR:
                icon = self._ICON_ERROR
            self._store.append(partition_id, [icon, issue.message, issue.file.basename, str(issue.start), issue])

            LOG.debug("Issue: %s" % issue)

        self._view.expand_all()

# ex:ts=4:et:
