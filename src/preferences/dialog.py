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
import gtk
from gtk import gdk

from ..base.resources import find_resource, MODE_READWRITE
from ..util import GladeInterface
from . import Preferences, IPreferencesMonitor


class PreferencesSpinButtonProxy(object):
	def __init__(self, widget, key, default_value):
		"""
		@param widget: a SpinButton widget
		@param key: 
		@param default_value: 
		"""
		self._widget = widget
		self._key = key
		self._preferences = Preferences()
		
		self._widget.set_value(int(self._preferences.get(key, default_value)))
		
		self._widget.connect("value-changed", self._on_value_changed)
	
	def _on_value_changed(self, spin_button):
		self._preferences.set(self._key, spin_button.get_value_as_int())
		

class PreferencesColorProxy(object):
	"""
	This connects to a gtk.gdk.Color and gets/sets the value of a certain
	preference
	"""
	def __init__(self, widget, key, default_value):
		"""
		@param widget: the gtk.Widget that serves as a proxy
		@param key: the key of the preferences field to be managed
		"""
		self._widget = widget
		self._key = key
		self._preferences = Preferences()
		
		# init value
		self._widget.set_color(gdk.color_parse(self._preferences.get(key, default_value)))
		
		# listen to change
		self._widget.connect("color-set", self._on_color_set)
	
	def _on_color_set(self, color_button):
		self._preferences.set(self._key, self._color_to_hex(color_button.get_color()))
	
	def _color_to_hex(self, color):
		"""
		Convert the value of a gtk.gdk.Color widget to a hex color value
		
		@param color: gtk.gdk.Color
		"""
		
		# gtk.gdk.Color components have range 0-65535
		
		r = int((float(color.red) / 65535.0) * 255.0)
		g = int((float(color.green) / 65535.0) * 255.0)
		b = int((float(color.blue) / 65535.0) * 255.0)
		
		return "#%02x%02x%02x" % (r, g, b)


from ..tools import Tool, Job


class ConfigureToolDialog(GladeInterface):
	"""
	Wraps the dialog for setting up a Tool
	"""
	
	filename = find_resource("glade/configure_tool.glade")
	
	_dialog = None
	
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
				pp_class = self._preferences.POST_PROCESSORS[row[2]]
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
			self._preferences = Preferences()
			
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
			
			self._store_job = gtk.ListStore(str, bool, str)   # command, mustSucceed, postProcessor
			
			self._view_job.set_model(self._store_job)
			
			mustSucceedRenderer = gtk.CellRendererToggle()
			mustSucceedRenderer.connect("toggled", self._on_must_succeed_toggled)
			
			commandRenderer = gtk.CellRendererText()
			commandRenderer.connect("edited", self._on_job_command_edited)

			self._store_pp = gtk.ListStore(str)
			for p in self._preferences.POST_PROCESSORS.iterkeys():
				self._store_pp.append([p])
			
			ppRenderer = gtk.CellRendererCombo()
			ppRenderer.set_property("editable", True)
			ppRenderer.set_property("model", self._store_pp)
			ppRenderer.set_property("text_column", 0)
			ppRenderer.set_property("has_entry", False)
			
			ppRenderer.connect("edited", self._on_job_pp_edited)
			
			self._view_job.insert_column_with_attributes(-1, "Command", commandRenderer, text=0, editable=True)
			self._view_job.insert_column_with_attributes(-1, "Must Succeed", mustSucceedRenderer, active=1)
			self._view_job.insert_column_with_attributes(-1, "Post-Processor", ppRenderer, text=2)
			
			#
			# description
			#
			self._entry_description = self.find_widget("entryDescription")
			
			#
			# extensions
			#
			self._entry_new_extension = self.find_widget("entryNewExtension")
			
			self._store_extension = gtk.ListStore(str)
			
			self._view_extension = self.find_widget("treeviewExtension")
			self._view_extension.set_model(self._store_extension)
			self._view_extension.insert_column_with_attributes(-1, "", gtk.CellRendererText(), text=0)
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
		store.swap(iter)
	
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
		self._store_job.set(self._store_job.get_iter_from_string(path), 0, text)
	
	def _on_job_pp_edited(self, renderer, path, text):
		"""
		Another post processor has been selected
		"""
		self._store_job.set(self._store_job.get_iter_from_string(path), 2, text)
	
	def _on_must_succeed_toggled(self, renderer, path):
		"""
		The 'must succeed' flag has been toggled
		"""
		value = self._store_job.get(self._store_job.get_iter_from_string(path), 1)[0]
		self._store_job.set(self._store_job.get_iter_from_string(path), 1, not value)
	
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
		store, iter = tree_view.get_selection().get_selected()
		if not iter: 
			return
		self._button_remove_job.set_sensitive(True)
		
		first_row_selected = (store.get_string_from_iter(iter) == "0")
		self._button_job_up.set_sensitive(not first_row_selected)
	
	def _on_extension_cursor_changed(self, tree_view):
		store, it = tree_view.get_selection().get_selected()
		if not it: 
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
	

class ConfigureSnippetDialog(GladeInterface):
	filename = find_resource("glade/configure_snippet.glade")
	
	_dialog = None
	
	def run(self, snippet):
		print snippet
		
		dialog = self._get_dialog()
		dialog.set_title("Configure Snippet - %s" % snippet.label)
		
		# load snippet
		self._entry_label.set_text(snippet.label)
		self._textview_source.get_buffer().set_text(snippet.expression)
		self._store_package.clear()
		for package in snippet.packages:
			self._store_package.append([package])
		
		result = None
		if dialog.run() == 1:
			# success
			buffer = self._textview_source.get_buffer()
			snippet.expression = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())
			snippet.label = self._entry_label.get_text()
			snippet.packages = [row[0] for row in self._store_package]
			
			result = snippet
		
		dialog.hide()
		
		return result
	
	def _get_dialog(self):
		if not self._dialog:
			self._preferences = Preferences()
			
			self._dialog = self.find_widget("dialogSnippet")
			self._entry_label = self.find_widget("entryLabel")
			self._entry_new_package = self.find_widget("entryNewPackage")
			self._treeview_package = self.find_widget("treeviewPackage")
			self._store_package = gtk.ListStore(str)
			self._treeview_package.set_model(self._store_package)
			self._treeview_package.insert_column_with_attributes(-1, "", gtk.CellRendererText(), text=0)
			self._treeview_package.set_headers_visible(False)
			self._button_add_package = self.find_widget("buttonAddPackage")
			self._button_remove_package = self.find_widget("buttonRemovePackage")
			self._textview_source = self.find_widget("textviewSource")
			
			self.connect_signals({"on_buttonAddPackage_clicked" : self.__on_add_package_clicked,
								  "on_buttonRemovePackage_clicked" : self.__on_remove_package_clicked,
								  "on_entryNewPackage_changed" : self.__on_new_package_changed,
								  "on_treeviewPackage_cursor_changed" : self.__on_package_cursor_changed})
		return self._dialog
	
	def __on_package_cursor_changed(self, treeview):
		store, it = treeview.get_selection().get_selected()
		if not it: 
			return
		self._button_remove_package.set_sensitive(True)
	
	def __on_new_package_changed(self, entry):
		self._button_add_package.set_sensitive(len(self._entry_new_package.get_text()) > 0)
	
	def __on_add_package_clicked(self, button):
		package = self._entry_new_package.get_text()
		self._store_package.append([package])
	
	def __on_remove_package_clicked(self, button):
		store, it = self._treeview_package.get_selection().get_selected()
		store.remove(it)
	

from ..snippets import Snippet


class PreferencesDialog(GladeInterface, IPreferencesMonitor):
	"""
	This controls the configure dialog
	"""
	
	_log = getLogger("PreferencesWizard")
	
	filename = find_resource("glade/configure.glade")
	_dialog = None
	
	@property
	def dialog(self):
		if not self._dialog:
			self._preferences = Preferences()
			
			self._dialog = self.find_widget("dialogConfigure")
			
			#
			# snippets
			#
			self._store_snippets = gtk.ListStore(bool, str, object) 	# active, name, Template instance

			render_toggle = gtk.CellRendererToggle()
			render_toggle.connect("toggled", self.__on_snippet_active_toggled)
			
			self._view_snippets = self.find_widget("treeviewTemplates")
			self._view_snippets.set_model(self._store_snippets)
			self._view_snippets.insert_column_with_attributes(-1, "Active", render_toggle, active=0)
			self._view_snippets.insert_column_with_attributes(-1, "Name", gtk.CellRendererText(), text=1)
			
			self._entry_snippet = self.find_widget("textviewTemplate")
			
			self.__load_snippets()
			
			#
			# recent bibliographies
			#
			self._storeBibs = gtk.ListStore(str)
			
#			for bib in self._preferences.bibliographies:
#				self._storeBibs.append([bib.filename])
				
			self._viewBibs = self.find_widget("treeviewBibs")
			self._viewBibs.set_model(self._storeBibs)
			self._viewBibs.insert_column_with_attributes(-1, "Filename", gtk.CellRendererText(), text=0)
			
			#
			# tools
			#
			
			# grab widgets

			self._button_delete_tool = self.find_widget("buttonDeleteTool")
			self._button_move_up_tool = self.find_widget("buttonMoveUpTool")
			self._button_configure_tool = self.find_widget("buttonConfigureTool")
			
			self._store_tool = gtk.ListStore(str, str, object)     # label markup, extensions, Tool instance
				
			self._view_tool = self.find_widget("treeviewProfiles")
			self._view_tool.set_model(self._store_tool)
			self._view_tool.insert_column_with_attributes(-1, "Label", gtk.CellRendererText(), markup=0)
			self._view_tool.insert_column_with_attributes(-1, "File Extensions", gtk.CellRendererText(), text=1)
			
			# init tool and listen to tool changes
			self.__load_tools()
			self._preferences.register_monitor(self)
			
			#
			# spell check
			#
			try:
				# the import may fail if enchant is not installed
				from ..latex.spellcheck import SpellCheckerBackend
				
				
				self._storeLanguages = gtk.ListStore(str)
				
				backend = SpellCheckerBackend()
				
				try :
					active_language = self._preferences.get("SpellCheckDictionary", backend.default_language)
				except Exception:
					self._log.error("Failed to determine default Enchant language")
					active_language = self._preferences.get("SpellCheckDictionary")
				
				active_index = 0
				i = 0
				for l in backend.languages:
					self._storeLanguages.append([l])
					if l == active_language:
						active_index = i
					else:
						i += 1
				
				self._comboLanguages = self.find_widget("comboLanguages")
				self._comboLanguages.set_model(self._storeLanguages)
				cell = gtk.CellRendererText()
				self._comboLanguages.pack_start(cell, True)
				self._comboLanguages.add_attribute(cell, "text", 0)
				self._comboLanguages.set_active(active_index)
			except ImportError:
				
				self._log.error("Enchant library could not be imported. Spell checking will be disabled.")
				
				# TODO: disable controls
				
				pass
			
			# misc
			check_hide_box = self.find_widget("checkHideBox")
			check_hide_box.set_active(self._preferences.get_bool("HideBoxWarnings", False))
			
			
			check_show_toolbar = self.find_widget("checkShowToolbar")
			check_show_toolbar.set_active(self._preferences.get_bool("ShowLatexToolbar", True))
			
			
			filechooser_tmp = self.find_widget("filechooserTemplates")
			filechooser_tmp.set_filename(self._preferences.get("TemplateFolder", find_resource("templates", MODE_READWRITE)))
			
			
			#
			# proxies for ColorButtons and SpinButtons
			#
			self._proxies = [ PreferencesColorProxy(self.find_widget("colorLight"), "LightForeground", "#957d47"),
									PreferencesColorProxy(self.find_widget("colorSpelling"), "SpellingBackgroundColor", "#ffeccf"),
									PreferencesColorProxy(self.find_widget("colorWarning"), "WarningBackgroundColor", "#ffffcf"),
									PreferencesColorProxy(self.find_widget("colorError"), "ErrorBackgroundColor", "#ffdddd"),
									PreferencesColorProxy(self.find_widget("colorTemplateBackground"), "TemplateBackgroundColor", "#f2f7ff"),
									PreferencesColorProxy(self.find_widget("colorPlaceholderBackground"), "PlaceholderBackgroundColor", "#d6e4ff"),
									PreferencesColorProxy(self.find_widget("colorPlaceholderForeground"), "PlaceholderForegroundColor", "#2a66e1"),
									PreferencesSpinButtonProxy(self.find_widget("spinMaxBibSize"), "MaximumBibTeXSize", 500) ]
			
			#
			# signals
			#
			self.connect_signals({ "on_buttonClose_clicked" : self._on_close_clicked,
								   "on_treeviewTemplates_cursor_changed" : self._on_snippet_cursor_changed,
								   "on_treeviewProfiles_cursor_changed" : self._on_tool_cursor_changed,
								   "on_buttonNewTemplate_clicked" : self._on_new_snippet_clicked,
								   "on_buttonNewProfile_clicked" : self._on_new_tool_clicked,
								   "on_buttonMoveUpTool_clicked" : self._on_tool_up_clicked,
								   "on_buttonMoveDownTool_clicked" : self._on_tool_down_clicked,
								   "on_buttonConfigureTool_clicked" : self._on_configure_tool_clicked,
								   "on_buttonDeleteTool_clicked" : self._on_delete_tool_clicked,
								   "on_buttonEditSnippet_clicked" : self._on_edit_snippet_clicked,
								   "on_comboLanguages_changed" : self._on_language_changed,
								   "on_checkHideBox_toggled" : self._on_hide_box_toggled,
								   "on_filechooserTemplates_selection_changed" : self._on_templates_dir_changed,
								   "on_checkShowToolbar_toggled" : self._on_show_toolbar_toggled })
			
		return self._dialog
	
	def _on_show_toolbar_toggled(self, togglebutton):
		value = togglebutton.get_active()
		self._preferences.set("ShowLatexToolbar", value)
	
	def _on_templates_dir_changed(self, filechooser):
		folder = filechooser.get_filename()
		if folder is None:
			return
		
		self._preferences.set("TemplateFolder", folder)
	
	def _on_hide_box_toggled(self, togglebutton):
		value = togglebutton.get_active()
		self._preferences.set("HideBoxWarnings", value)
	
	def _on_language_changed(self, combobox):
		language = combobox.get_model().get_value(combobox.get_active_iter(), 0)
		self._preferences.set("SpellCheckDictionary", language)
	
	def __load_snippets(self):
		self._store_snippets.clear()
		for snippet in self._preferences.snippets:
			self._store_snippets.append([snippet.active, snippet.label, snippet])
		
		self._entry_snippet.get_buffer().set_text("")
	
	def __on_snippet_active_toggled(self, renderer, path):
		iter = self._store_snippets.get_iter_from_string(path)
		active = not self._store_snippets.get_value(iter, 0)
		self._store_snippets.set_value(iter, 0, active)
		snippet = self._store_snippets.get_value(iter, 2)
		snippet.active = active
		self._preferences.save_or_update_snippet(snippet)
	
	def _on_edit_snippet_clicked(self, button):
		store, it = self._view_snippets.get_selection().get_selected()
		snippet = store.get_value(it, 2)
		
		snippet = ConfigureSnippetDialog().run(snippet)
		if not snippet is None:
			self._preferences.save_or_update_snippet(snippet)
	
	def _on_tools_changed(self):
		# see IPreferencesMonitor._on_tools_changed
		self.__load_tools()
	
	def _on_snippets_changed(self):
		# see IPreferencesMonitor._on_snippets_changed
		self.__load_snippets()
	
	def __load_tools(self):
		# save cursor
		store, iter = self._view_tool.get_selection().get_selected()
		if iter is None:
			restore_cursor = False
		else:
			path = store.get_string_from_iter(iter)
			restore_cursor = True
		
		# reload tools
		self._store_tool.clear()
		for tool in self._preferences.tools:
			self._store_tool.append(["<b>%s</b>" % tool.label, ", ".join(tool.extensions), tool])
		
		# restore cursor
		if restore_cursor:
			self._view_tool.set_cursor(path)
	
	def _on_configure_tool_clicked(self, button):
		store, it = self._view_tool.get_selection().get_selected()
		tool = store.get_value(it, 2)
		
		dialog = ConfigureToolDialog()
		
		if not dialog.run(tool) is None:
			self._preferences.save_or_update_tool(tool)
	
	def _on_delete_tool_clicked(self, button):
		store, it = self._view_tool.get_selection().get_selected()
		tool = store.get_value(it, 2)
		
		self._preferences.delete_tool(tool)
	
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
		
		self._preferences.swap_tools(tool_1, tool_2)
	
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
		self._preferences.swap_tools(tool_1, tool_2)
		
		# adjust selection
		self._view_tool.get_selection().select_path(str(index_next))
	
	def _on_new_tool_clicked(self, button):
		dialog = ConfigureToolDialog()
		
		tool = Tool("New Tool", [], "", [".tex"])
		
		if not dialog.run(tool) is None:
			self._preferences.save_or_update_tool(tool)
	
	def _on_new_snippet_clicked(self, button):
		snippet = ConfigureSnippetDialog().run(Snippet("Unnamed", "", True, []))
		if not snippet is None:
			self._preferences.save_or_update_snippet(snippet)
	
	def _on_close_clicked(self, button):
		self._dialog.hide()
	
	def _on_snippet_cursor_changed(self, treeView):
		store, it = treeView.get_selection().get_selected()
		if not it: 
			return
		
		snippet = store.get_value(it, 2)
		
		self._entry_snippet.get_buffer().set_text(snippet.expression)
		
	def _on_tool_cursor_changed(self, treeView):
		"""
		The cursor in the tools view has changed
		"""
		store, it = treeView.get_selection().get_selected()
		if not it: 
			return
		
		self._profile = store.get_value(it, 1)
		
		self._button_delete_tool.set_sensitive(True)
		self._button_move_up_tool.set_sensitive(True)
		self._button_configure_tool.set_sensitive(True)
		
			
	
	
	