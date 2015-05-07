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
preferences.dialog
"""

from logging import getLogger
from gi.repository import Gtk

from ..resources import Resources
from ..util import GladeInterface
from ..tools import Tool, Job

from . import Preferences
from .tools import ToolPreferences

def _insert_column_with_attributes(view, pos, title, rend, **kwargs):
    tv = Gtk.TreeViewColumn(title)
    tv.pack_start(rend, True)
    for k in kwargs:
        tv.add_attribute(rend, k, kwargs[k])
    view.insert_column(tv, pos)

class PreferencesSpinButtonProxy(object):
    def __init__(self, widget, key):
        """
        @param widget: a SpinButton widget
        @param key:
        @param default_value:
        """
        self._widget = widget
        self._key = key
        self._preferences = Preferences()

        self._widget.set_value(int(self._preferences.get(key)))

        self._widget.connect("value-changed", self._on_value_changed)

    def _on_value_changed(self, spin_button):
        self._preferences.set(self._key, spin_button.get_value_as_int())

class ConfigureToolDialog(GladeInterface):
    """
    Wraps the dialog for setting up a Tool
    """

    _dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("configure_tool.ui")

    def run(self, tool):
        """
        Runs the dialog and returns the updated Tool or None on abort
        """
        dialog = self._get_dialog()

        self._tool = tool
        

        # load Tool
        self._entry_label.set_text(tool.label)
        self._entry_description.set_text(tool.description)

        self._store_job.clear()
        for job in tool.jobs:
            self._store_job.append([job.command_template, job.must_succeed, job.post_processor.name])

        self._store_extension.clear()
        for ext in tool.extensions:
            self._store_extension.append([ext])

        if tool.accelerator is None:
            self._radio_user_accel.set_active(False)
            self._entry_accel.set_text("")
        else:
            self._radio_user_accel.set_active(True)
            self._entry_accel.set_text(tool.accelerator)

        if dialog.run() == 1:
            #
            # okay clicked - update the Tool object
            #
            tool.label = self._entry_label.get_text()
            tool.description = self._entry_description.get_text()

            tool.jobs = []
            for row in self._store_job:
                pp_class = self._tool_preferences.POST_PROCESSORS[row[2]]
                tool.jobs.append(Job(row[0], row[1], pp_class))

            tool.extensions = []
            for row in self._store_extension:
                tool.extensions.append(row[0])

            # TODO: validate accelerator!
            if self._radio_user_accel.get_active():
                tool.accelerator = self._entry_accel.get_text()
            else:
                tool.accelerator = None

            return tool
        else:
            return None

    def _get_dialog(self):
        if not self._dialog:
            #
            # build the dialog
            #
            self._tool_preferences = ToolPreferences()

            self._dialog = self.find_widget("dialogConfigureTool")
            self._button_okay = self.find_widget("buttonOkay")
            self._labelProfileValidate = self.find_widget("labelHint")

            #
            # label
            #
            self._entry_label = self.find_widget("entryLabel")

            #
            # jobs
            #
            self._entry_new_job = self.find_widget("entryNewJob")
            self._button_add_job = self.find_widget("buttonAddJob")
            self._button_remove_job = self.find_widget("buttonRemoveJob")
            self._button_job_up = self.find_widget("buttonMoveUpJob")
            self._view_job = self.find_widget("treeviewJob")

            self._store_job = Gtk.ListStore(str, bool, str)   # command, mustSucceed, postProcessor

            self._view_job.set_model(self._store_job)

            mustSucceedRenderer = Gtk.CellRendererToggle()
            mustSucceedRenderer.connect("toggled", self._on_must_succeed_toggled)

            commandRenderer = Gtk.CellRendererText()
            commandRenderer.connect("edited", self._on_job_command_edited)

            self._store_pp = Gtk.ListStore(str)
            for p in self._tool_preferences.POST_PROCESSORS.keys():
                self._store_pp.append([p])

            ppRenderer = Gtk.CellRendererCombo()
            ppRenderer.set_property("editable", True)
            ppRenderer.set_property("model", self._store_pp)
            ppRenderer.set_property("text_column", 0)
            ppRenderer.set_property("has_entry", False)

            ppRenderer.connect("edited", self._on_job_pp_edited)

            _insert_column_with_attributes(self._view_job, -1, "Command", commandRenderer, text=0, editable=True)
            _insert_column_with_attributes(self._view_job, -1, "Must Succeed", mustSucceedRenderer, active=1)
            _insert_column_with_attributes(self._view_job, -1, "Post-Processor", ppRenderer, text=2)

            #
            # description
            #
            self._entry_description = self.find_widget("entryDescription")

            #
            # extensions
            #
            self._entry_new_extension = self.find_widget("entryNewExtension")

            self._store_extension = Gtk.ListStore(str)

            self._view_extension = self.find_widget("treeviewExtension")
            self._view_extension.set_model(self._store_extension)
            _insert_column_with_attributes(self._view_extension, -1, "", Gtk.CellRendererText(), text=0)
            self._view_extension.set_headers_visible(False)

            self._button_add_extension = self.find_widget("buttonAddExtension")
            self._button_remove_extension = self.find_widget("buttonRemoveExtension")

            self._radio_user_accel = self.find_widget("radioAccelUser")
            self._entry_accel = self.find_widget("entryAccel")

            self.connect_signals({ "on_entryNewJob_changed" : self._on_new_job_changed,
                                   "on_entryNewExtension_changed" : self._on_new_extension_changed,
                                   "on_buttonAddJob_clicked" : self._on_add_job_clicked,
                                   "on_buttonRemoveJob_clicked" : self._on_remove_job_clicked,
                                   "on_treeviewJob_cursor_changed" : self._on_job_cursor_changed,
                                   "on_treeviewExtension_cursor_changed" : self._on_extension_cursor_changed,
                                   "on_buttonAbort_clicked" : self._on_abort_clicked,
                                   "on_buttonOkay_clicked" : self._on_okay_clicked,
                                   "on_buttonRemoveExtension_clicked" : self._on_remove_extension_clicked,
                                   "on_buttonAddExtension_clicked" : self._on_add_extension_clicked,
                                   "on_buttonMoveUpJob_clicked" : self._on_move_up_job_clicked,
                                   "on_radioAccelUser_toggled" : self._on_accel_user_toggled })

        return self._dialog

    def _on_accel_user_toggled(self, togglebutton):
        enabled = togglebutton.get_active()
        self._entry_accel.set_sensitive(enabled)

    def _on_move_up_job_clicked(self, button):
        store, iter = self._view_job.get_selection().get_selected()
        prev = store.iter_previous(iter)
        if prev:
            store.swap(iter, prev)

    def _on_add_extension_clicked(self, button):
        extension = self._entry_new_extension.get_text()
        self._store_extension.append([extension])

    def _on_remove_extension_clicked(self, button):
        store, it = self._view_extension.get_selection().get_selected()
        store.remove(it)

    def _on_job_command_edited(self, renderer, path, text):
        """
        The command template has been edited
        """
        self._store_job.set_value(self._store_job.get_iter_from_string(path), 0, text)

    def _on_job_pp_edited(self, renderer, path, text):
        """
        Another post processor has been selected
        """
        self._store_job.set_value(self._store_job.get_iter_from_string(path), 2, text)

    def _on_must_succeed_toggled(self, renderer, path):
        """
        The 'must succeed' flag has been toggled
        """
        value = self._store_job.get(self._store_job.get_iter_from_string(path), 1)[0]
        self._store_job.set_value(self._store_job.get_iter_from_string(path), 1, not value)

    def _on_add_job_clicked(self, button):
        """
        Add a new job
        """
        command = self._entry_new_job.get_text()
        self._store_job.append([command, True, "GenericPostProcessor"])

    def _on_remove_job_clicked(self, button):
        store, it = self._view_job.get_selection().get_selected()
        store.remove(it)

    def _on_new_job_changed(self, widget):
        """
        The entry for a new command template has changed
        """
        self._button_add_job.set_sensitive(len(self._entry_new_job.get_text()) > 0)

    def _on_new_extension_changed(self, widget):
        self._button_add_extension.set_sensitive(len(self._entry_new_extension.get_text()) > 0)

    def _on_job_cursor_changed(self, tree_view):
        selection = tree_view.get_selection()
        if selection:
            store, iter = tree_view.get_selection().get_selected()
        if not selection or not iter:
            return
        self._button_remove_job.set_sensitive(True)

        first_row_selected = (store.get_string_from_iter(iter) == "0")
        self._button_job_up.set_sensitive(not first_row_selected)

    def _on_extension_cursor_changed(self, tree_view):
        selection = tree_view.get_selection()
        if selection:
            store, it = tree_view.get_selection().get_selected()
        if not selection or not it:
            return
        self._button_remove_extension.set_sensitive(True)

    def _on_abort_clicked(self, button):
        self._dialog.hide()

    def _on_okay_clicked(self, button):
        self._dialog.hide()

    def _validate_tool(self):
        """
        Validate the dialog contents
        """
        errors = []

        if len(self._store_job) == 0:
            errors.append("You have not specified any jobs.")

        if len(errors):
            self._buttonApply.set_sensitive(False)
        else:
            self._buttonApply.set_sensitive(True)

        if len(errors) == 1:
            self._labelProfileValidate.set_markup(errors[0])
        elif len(errors) > 1:
            self._labelProfileValidate.set_markup("\n".join([" * %s" % e for e in errors]))
        else:
            self._labelProfileValidate.set_markup("Remember to run all commands in batch mode (e.g. append <tt>-interaction batchmode</tt> to <tt>latex</tt>)")



class PreferencesDialog(GladeInterface):
    """
    This controls the configure dialog
    """

    _log = getLogger("PreferencesWizard")

    _dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("configure.ui")

    @property
    def dialog(self):
        if not self._dialog:
            self._dialog = self.find_widget("notebook1")

            self._preferences = Preferences()
            self._tool_preferences = ToolPreferences()

            # grab widgets

            self._button_delete_tool = self.find_widget("buttonDeleteTool")
            self._button_move_up_tool = self.find_widget("buttonMoveUpTool")
            self._button_configure_tool = self.find_widget("buttonConfigureTool")

            self._store_tool = Gtk.ListStore(str, str, object)     # label markup, extensions, Tool instance

            self._view_tool = self.find_widget("treeviewProfiles")
            self._view_tool.set_model(self._store_tool)
            _insert_column_with_attributes(self._view_tool, -1, "Label", Gtk.CellRendererText(), markup=0)
            _insert_column_with_attributes(self._view_tool, -1, "File Extensions", Gtk.CellRendererText(), text=1)

            # init tool and listen to tool changes
            self._load_tools()
            self._tool_preferences.connect("tools-changed", self._on_tools_changed)


            # misc
            check_hide_box = self.find_widget("checkHideBox")
            check_hide_box.set_active(self._preferences.get("hide-box-warnings"))


            #
            # proxies for SpinButtons
            #
            self._proxies = [PreferencesSpinButtonProxy(self.find_widget("spinMaxBibSize"), "maximum-bibtex-size")]

            #
            # signals
            #
            self.connect_signals({ "on_buttonClose_clicked" : self._on_close_clicked,
                                   "on_treeviewProfiles_cursor_changed" : self._on_tool_cursor_changed,
                                   "on_buttonAddBib_clicked" : self._on_add_bib_clicked,
                                   "on_buttonRemoveBib_clicked" : self._on_delete_bib_clicked,
                                   "on_buttonNewProfile_clicked" : self._on_new_tool_clicked,
                                   "on_buttonMoveUpTool_clicked" : self._on_tool_up_clicked,
                                   "on_buttonMoveDownTool_clicked" : self._on_tool_down_clicked,
                                   "on_buttonConfigureTool_clicked" : self._on_configure_tool_clicked,
                                   "on_buttonDeleteTool_clicked" : self._on_delete_tool_clicked,
                                   "on_checkHideBox_toggled" : self._on_hide_box_toggled})

        return self._dialog

    def _on_hide_box_toggled(self, togglebutton):
        value = togglebutton.get_active()
        self._preferences.set("hide-box-warnings", value)

    def _on_tools_changed(self, tools):
        self._load_tools()

    def _load_tools(self):
        # save cursor
        selection = self._view_tool.get_selection()
        if selection:
            store, iter = self._view_tool.get_selection().get_selected()
        if not selection or iter is None:
            restore_cursor = False
        else:
            path = store.get_path(iter)
            restore_cursor = True

        # reload tools
        self._store_tool.clear()
        for tool in self._tool_preferences.tools:
            self._store_tool.append(["<b>%s</b>" % tool.label, ", ".join(tool.extensions), tool])

        # restore cursor
        if restore_cursor:
            self._view_tool.set_cursor(path, None, False)

    def _on_configure_tool_clicked(self, button):
        store, it = self._view_tool.get_selection().get_selected()
        tool = store.get_value(it, 2)

        dialog = ConfigureToolDialog()

        if not dialog.run(tool) is None:
            self._tool_preferences.save_or_update_tool(tool)

    def _on_delete_tool_clicked(self, button):
        store, it = self._view_tool.get_selection().get_selected()
        tool = store.get_value(it, 2)

        self._tool_preferences.delete_tool(tool)

    def _on_tool_up_clicked(self, button):
        """
        Move up the selected tool
        """
        store, iter = self._view_tool.get_selection().get_selected()
        tool_1 = store.get_value(iter, 2)

        index_previous = int(store.get_string_from_iter(iter)) - 1
        assert index_previous >= 0

        iter_previous = store.get_iter_from_string(str(index_previous))
        tool_2 = store.get_value(iter_previous, 2)

        self._tool_preferences.swap_tools(tool_1, tool_2)

        # adjust selection
        self._view_tool.get_selection().select_path(str(index_previous))

    def _on_tool_down_clicked(self, button):
        """
        Move down the selected tool
        """
        store, iter = self._view_tool.get_selection().get_selected()
        tool_1 = store.get_value(iter, 2)

        index_next = int(store.get_string_from_iter(iter)) + 1
        assert index_next < len(store)

        iter_next = store.get_iter_from_string(str(index_next))
        tool_2 = store.get_value(iter_next, 2)

        # swap tools in preferences
        self._tool_preferences.swap_tools(tool_1, tool_2)

        # adjust selection
        self._view_tool.get_selection().select_path(str(index_next))

    def _on_new_tool_clicked(self, button):
        dialog = ConfigureToolDialog()

        tool = Tool("New Tool", [], "", None, [".tex"])

        if not dialog.run(tool) is None:
            self._tool_preferences.save_or_update_tool(tool)

    def _on_delete_bib_clicked(self, button):
        pass

    def _on_add_bib_clicked(self, button):
        pass

    def _on_close_clicked(self, button):
        self._dialog.hide()

    def _on_tool_cursor_changed(self, treeView):
        """
        The cursor in the tools view has changed
        """
        selection = treeView.get_selection()
        if selection:
            store, it = treeView.get_selection().get_selected()
        if not selection or not it:
            return

        self._profile = store.get_value(it, 1)

        self._button_delete_tool.set_sensitive(True)
        self._button_move_up_tool.set_sensitive(True)
        self._button_configure_tool.set_sensitive(True)

# ex:ts=4:et:
