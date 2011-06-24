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
from gi.repository import Gdk

from ..base.resources import find_resource, MODE_READWRITE
from ..util import GladeInterface
from . import Preferences, IPreferencesMonitor

def _insert_column_with_attributes(view, pos, title, rend, **kwargs):
	print kwargs
	tv = Gtk.TreeViewColumn(title)
	tv.pack_start(rend, True)
	for k in kwargs:
		tv.add_attribute(rend, k, kwargs[k])
	view.insert_column(tv, pos)

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
	This connects to a Gdk.Color and gets/sets the value of a certain
	preference
	"""
	def __init__(self, widget, key, default_value):
		"""
		@param widget: the Gtk.Widget that serves as a proxy
		@param key: the key of the preferences field to be managed
		"""
		self._widget = widget
		self._key = key
		self._preferences = Preferences()
		
		# init value
		#self._widget.set_color(Gdk.color_parse(self._preferences.get(key, default_value)))
		
		# listen to change
		self._widget.connect("color-set", self._on_color_set)
	
	def _on_color_set(self, color_button):
		self._preferences.set(self._key, self._color_to_hex(color_button.get_color()))
	
	def _color_to_hex(self, color):
		"""
		Convert the value of a Gdk.Color widget to a hex color value
		
		@param color: Gdk.Color
		"""
		
		# Gdk.Color components have range 0-65535
		
		r = int((float(color.red) / 65535.0) * 255.0)
		g = int((float(color.green) / 65535.0) * 255.0)
		b = int((float(color.blue) / 65535.0) * 255.0)
		
		return "#%02x%02x%02x" % (r, g, b)

class PreferencesDialog(GladeInterface, IPreferencesMonitor):
	"""
	This controls the configure dialog
	"""
	
	_log = getLogger("PreferencesWizard")
	
	filename = find_resource("ui/configure.ui")
	_dialog = None
	
	@property
	def dialog(self):
		if not self._dialog:
			self._preferences = Preferences()
			
			self._dialog = self.find_widget("notebook1")
			
			#
			# recent bibliographies
			#
			self._storeBibs = Gtk.ListStore(str)
			
#			for bib in self._preferences.bibliographies:
#				self._storeBibs.append([bib.filename])
				
			self._viewBibs = self.find_widget("treeviewBibs")
			self._viewBibs.set_model(self._storeBibs)
			_insert_column_with_attributes(self._viewBibs, -1, "Filename", Gtk.CellRendererText(), text=0)
			
			self._preferences.register_monitor(self)
			
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
								   "on_buttonAddBib_clicked" : self._on_add_bib_clicked,
								   "on_buttonRemoveBib_clicked" : self._on_delete_bib_clicked,
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
	
	def _on_delete_bib_clicked(self, button):
		pass

	def _on_add_bib_clicked(self, button):
		pass
			
	def _on_close_clicked(self, button):
		self._dialog.hide()
	
