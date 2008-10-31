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
preferences.dialog
"""

from logging import getLogger
import gtk
from gtk import gdk

from ..base.resources import find_resource
from ..util import GladeInterface
from . import Preferences


class PreferencesColorProxy(object):
	
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


class PreferencesDialog(GladeInterface):
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
			
			self._buttonApply = self.find_widget("buttonApply")
			
			#
			# snippets
			#
			self._store_snippets = gtk.ListStore(bool, str, object) 	# active, name, Template instance
			
#			for template in self._preferences.templates:
#				self._store_snippets.append([True, template.name, template])
				
			self._view_snippets = self.find_widget("treeviewTemplates")
			self._view_snippets.set_model(self._store_snippets)
			self._view_snippets.insert_column_with_attributes(-1, "Active", gtk.CellRendererToggle(), active=0)
			self._view_snippets.insert_column_with_attributes(-1, "Name", gtk.CellRendererText(), text=1)
			
			self._entry_snippet = self.find_widget("textviewTemplate")
			
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
			
			self._labelProfileValidate = self.find_widget("labelProfileValidate")
			self._entryProfileName = self.find_widget("entryProfileName")
			self._entryNewJob = self.find_widget("entryNewJob")
			self._buttonAddJob = self.find_widget("buttonAddJob")
			self._view_job = self.find_widget("treeviewJobs")
			self._buttonRemoveJob = self.find_widget("buttonRemoveJob")
			self._buttonJobUp = self.find_widget("buttonJobUp")
			self._buttonProfileSave = self.find_widget("buttonProfileSave")
			self._entryViewCommand = self.find_widget("entryViewCommand")
			self._entryOutputFile = self.find_widget("entryOutputFile")
			
			# tools
			
			self._store_tool = gtk.ListStore(str, str, object)     # label markup, extensions, Tool instance
			
			for tool in self._preferences.tools:
				self._store_tool.append(["<b>%s</b>" % tool.label, ", ".join(tool.extensions), tool])
				
			self._view_tool = self.find_widget("treeviewProfiles")
			self._view_tool.set_model(self._store_tool)
			self._view_tool.insert_column_with_attributes(-1, "Label", gtk.CellRendererText(), markup=0)
			self._view_tool.insert_column_with_attributes(-1, "File Extensions", gtk.CellRendererText(), text=1)
			
			# jobs
			
			self._store_job = gtk.ListStore(str, bool, str)   # command, mustSucceed, postProcessor
			
			self._view_job.set_model(self._store_job)
			
			mustSucceedRenderer = gtk.CellRendererToggle()
			mustSucceedRenderer.connect("toggled", self._on_must_succeed_toggled)
			
			commandRenderer = gtk.CellRendererText()
			commandRenderer.connect("edited", self._on_job_command_edited)

			self._storePp = gtk.ListStore(str)
#			for pp in Builder.POST_PROCESSOR_CLASSES.iterkeys():
#				self._storePp.append([pp])
			
			ppRenderer = gtk.CellRendererCombo()
			ppRenderer.set_property("editable", True)
			ppRenderer.set_property("model", self._storePp)
			ppRenderer.set_property("text_column", 0)
			ppRenderer.set_property("has_entry", False)
			
			ppRenderer.connect("edited", self._on_job_pp_edited)
			
			self._view_job.insert_column_with_attributes(-1, "Command", commandRenderer, text=0, editable=True)
			self._view_job.insert_column_with_attributes(-1, "Must Succeed", mustSucceedRenderer, active=1)
			self._view_job.insert_column_with_attributes(-1, "Post-Processor", ppRenderer, text=2)
			
			#
			# spell check
			#
			try:
				# the import may fail if enchant is not installed
				from spellcheck import EnchantFacade
				
				
				self._storeLanguages = gtk.ListStore(str)
				
				enchant = EnchantFacade()
				for l in enchant.getLanguages():
					self._storeLanguages.append([l])
				
				self._comboLanguages = self.find_widget("comboLanguages")
				self._comboLanguages.set_model(self._storeLanguages)
				cell = gtk.CellRendererText()
				self._comboLanguages.pack_start(cell, True)
				self._comboLanguages.add_attribute(cell, "text", 0)
				self._comboLanguages.set_active(0)
			except ImportError:
				
				self._log.error("Enchant library could not be imported. Spell checking will be disabled.")
				# TODO: show warning 
				
				pass
			
			#
			# colors
			#
			self._color_proxies = [ PreferencesColorProxy(self.find_widget("colorLight"), "LightForeground", "#957d47"),
									PreferencesColorProxy(self.find_widget("colorSpelling"), "SpellingBackgroundColor", "#ffeccf"),
									PreferencesColorProxy(self.find_widget("colorWarning"), "WarningBackgroundColor", "#ffffcf"),
									PreferencesColorProxy(self.find_widget("colorError"), "ErrorBackgroundColor", "#ffdddd") ]
			
			#
			# signals
			#
			self.connect_signals({ "on_buttonApply_clicked" : self._on_apply_clicked,
								   "on_buttonAbort_clicked" : self._on_abort_clicked,
								   "on_treeviewTemplates_cursor_changed" : self._on_snippet_changed,
								   "on_treeviewProfiles_cursor_changed" : self._on_tool_changed,
								   "on_buttonProfileSave_clicked" : self._on_save_tool_clicked,
								   "on_entryNewJob_changed" : self._on_new_job_changed,
								   "on_buttonAddJob_clicked" : self._on_add_job_clicked,
								   "on_buttonNewTemplate_clicked" : self._on_new_snippet_clicked,
								   "on_buttonSaveTemplate_clicked" : self._on_save_snippet_clicked,
								   "on_buttonNewProfile_clicked" : self._on_new_tool_clicked,
								   "on_buttonMoveDownProfile_clicked" : self._on_tool_down_clicked })
			
		return self._dialog
	
	def _on_tool_down_clicked(self, button):
		store, it = self._view_tool.get_selection().get_selected()
		profile = store.get_value(it, 1)
		
		# update model
		Settings().moveDownProfile(profile)
		
		# update ui
		nextIt = store.iter_next(it)
		if (nextIt):
			store.swap(it, nextIt)
	
	def _on_new_tool_clicked(self, button):
		pass
	
	def _on_save_snippet_clicked(self, button):
		pass
	
	def _on_new_snippet_clicked(self, button):
		self._store_snippets.append([True, "Unnamed", Template("")])
	
	def _on_add_job_clicked(self, button):
		command = self._entryNewJob.get_text()
		self._store_job.append([command, True, "Generic"])
	
	def _on_new_job_changed(self, comboBox):
		self._buttonAddJob.set_sensitive(len(self._entryNewJob.get_text()) > 0)
	
	def _on_save_tool_clicked(self, button):
		"""
		Update the current profile
		"""
		self._profile.name = self._entryProfileName.get_text()
		self._profile.viewCommand = self._entryViewCommand.get_text()
		self._profile.outputFile = self._entryOutputFile.get_text()
		
		self._profile.jobs = []
		for row in self._store_job:
			self._profile.jobs.append(Job(row[0], row[1], row[2]))
		
		Settings().updateProfile(self._profile)
	
	def _on_apply_clicked(self, button):
		self._dialog.hide()
	
	def _on_abort_clicked(self, button):
		self._dialog.hide()
	
	def _on_snippet_changed(self, treeView):
		store, it = treeView.get_selection().get_selected()
		if not it: 
			return
		
		self._template = store.get_value(it, 2)
		
		self._entry_snippet.get_buffer().set_text(self._template.source)
		
	def _on_tool_changed(self, treeView):
		"""
		The cursor in the tools view has changed
		"""
		store, it = treeView.get_selection().get_selected()
		if not it: 
			return
		
		self._profile = store.get_value(it, 1)
		
		# load profile settings

		self._entryProfileName.set_text(self._profile.name)
		
		self._store_job.clear()
		for job in self._profile.jobs:
			self._store_job.append([job.command, job.mustSucceed, job.postProcessor])
			
		self._entryViewCommand.set_text(self._profile.viewCommand)
		self._entryOutputFile.set_text(self._profile.outputFile)
		
			
	def _on_job_command_edited(self, renderer, path, text):
		self._store_job.set(self._store_job.get_iter_from_string(path), 0, text)
	
	def _on_job_pp_edited(self, renderer, path, text):
		self._store_job.set(self._store_job.get_iter_from_string(path), 2, text)
	
	def _on_must_succeed_toggled(self, renderer, path):
		value = self._store_job.get(self._store_job.get_iter_from_string(path), 1)[0]
		self._store_job.set(self._store_job.get_iter_from_string(path), 1, not value)
	
	def _validate_tool(self):
		"""
		Validate the form
		"""
		errors = []
		
		# jobs

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
	