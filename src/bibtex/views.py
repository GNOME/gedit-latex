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
bibtex.views

The BibTeX outline view
"""

import gtk
from gtk.gdk import Pixbuf, pixbuf_new_from_file
from xml.sax.saxutils import escape
from logging import getLogger

from ..outline import BaseOutlineView
from ..base.resources import find_resource
from ..base.preferences import Preferences
from parser import Entry


GROUP_NONE, GROUP_TYPE, GROUP_AUTHOR, GROUP_YEAR = 1, 2, 3, 4


class BibTeXOutlineView(BaseOutlineView):
	"""
	Special outline view for BibTeX
	"""

	_log = getLogger("BibTeXOutlineView")
	
	def init(self, context):
		BaseOutlineView.init(self, context)
		
		self._grouping = GROUP_NONE
		
		# add grouping controls to toolbar
		
		self._item_none = gtk.RadioMenuItem(None, "No Grouping")
		self._item_type = gtk.RadioMenuItem(self._item_none, "Group by Type")
		self._item_author = gtk.RadioMenuItem(self._item_none, "Group by Author")
		self._item_year = gtk.RadioMenuItem(self._item_none, "Group by Year")
		
		self._preferences = Preferences()
		
		grouping = self._preferences.get("BibtexOutlineGrouping", GROUP_NONE)
		if grouping == GROUP_NONE:
			self._item_none.set_active(True)
		elif grouping == GROUP_TYPE:
			self._item_type.set_active(True)
		elif grouping == GROUP_AUTHOR:
			self._item_author.set_active(True)
		elif grouping == GROUP_YEAR:
			self._item_year.set_active(True)
		
		self._item_none.connect("toggled", self._on_grouping_toggled)
		self._item_type.connect("toggled", self._on_grouping_toggled)
		self._item_author.connect("toggled", self._on_grouping_toggled)
		self._item_year.connect("toggled", self._on_grouping_toggled)

		menu = gtk.Menu()
		menu.add(self._item_none)
		menu.add(self._item_type)
		menu.add(self._item_author)
		menu.add(self._item_year)
		menu.show_all()

		tool_button = gtk.MenuToolButton(gtk.STOCK_SORT_DESCENDING)
		tool_button.set_menu(menu)
		tool_button.show()
		
		self._toolbar.insert(tool_button, -1)
	
	def _on_grouping_toggled(self, toggle_button):
		if self._item_none.get_active():
			self._grouping = GROUP_NONE
		elif self._item_type.get_active():
			self._grouping = GROUP_TYPE
		elif self._item_author.get_active():
			self._grouping = GROUP_AUTHOR
		elif self._item_year.get_active():
			self._grouping = GROUP_YEAR
		
		if self._outline:
			self._update()
	
	def _update(self):
		OutlineConverter().convert(self._store, self._outline, self._grouping)
	
	def set_outline(self, outline):
		"""
		Display the given model
		"""
		self._outline = outline
		
		self.assure_init()
		self._save_state()
		self._update()
		self._restore_state()
		
	def _on_node_selected(self, node):
		"""
		An outline node has been selected
		"""
		if isinstance(node, Entry):
			self._context.active_editor.select(node.start, node.end)


class OutlineConverter(object):
	"""
	This converts a BibTeX document to a gtk.TreeStore and realizes the 
	grouping feature
	"""
	
	_ICON_ENTRY = pixbuf_new_from_file(find_resource("icons/document.png"))
	_ICON_FIELD = pixbuf_new_from_file(find_resource("icons/field.png"))
	_ICON_AUTHOR = pixbuf_new_from_file(find_resource("icons/users.png"))
	_ICON_YEAR = pixbuf_new_from_file(find_resource("icons/calendar.png"))
	_ICON_TYPE = pixbuf_new_from_file(find_resource("icons/documents.png"))
	
	def convert(self, tree_store, document, grouping=GROUP_NONE):
		"""
		Convert a BibTeX document model into a gtk.TreeStore
		
		@param tree_store: the gtk.TreeStore to fill
		@param document: the BibTeX document model (bibtex.parser.Document object)
		@param grouping: the grouping to use: GROUP_NONE|GROUP_TYPE|GROUP_AUTHOR|GROUP_YEAR
		"""
		
		color = Preferences().get("LightForeground", "#7f7f7f")
		
		tree_store.clear()
		
		if grouping == GROUP_TYPE:
			# group by entry type
			
			groups = {}		# maps lower case entry type names to lists of entries
			
			# collect
			for entry in document.entries:
				try:
					entryList = groups[entry.type]
					entryList.append(entry)
				except KeyError:
					groups[entry.type] = [entry]
			
			# sort by type
			entryTypes = groups.keys()
			entryTypes.sort()
			
			# build tree
			for entryType in entryTypes:
				entries = groups[entryType]
				
				parentType = tree_store.append(None, ["%s <span color='%s'>%s</span>" % (escape(entryType), color, len(entries)), self._ICON_TYPE, None])
				
				for entry in entries:
					parentEntry = tree_store.append(parentType, [escape(entry.key), self._ICON_ENTRY, entry])
					
					for field in entry.fields:
						tree_store.append(parentEntry, ["<span color='%s'>%s</span> %s" % (color, escape(field.name), field.valueMarkup),
											self._ICON_FIELD, field])
		
		elif grouping == GROUP_YEAR:
			# group by year
			
			NO_YEAR_IDENT = "<i>n/a</i>"
			
			groups = {}
			
			# collect
			for entry in document.entries:
				try:
					year = str(entry.findField("year").valueString)
				except KeyError:
					# no year, so put this in an extra group
					year = NO_YEAR_IDENT
					
				try:
					entries = groups[year]
					entries.append(entry)
				except KeyError:
					groups[year] = [entry]
			
			# sort by year
			years = groups.keys()
			years.sort()
			
			# build tree
			for year in years:
				entries = groups[year]
				
				parentYear = tree_store.append(None, ["%s <span color='%s'>%s</span>" % (year, color, len(entries)), self._ICON_YEAR, None])
				
				for entry in entries:
					parentEntry = tree_store.append(parentYear, ["%s <span color='%s'>%s</span>" % (escape(entry.key), color, escape(entry.type)),
															 self._ICON_ENTRY, entry])
					
					for field in entry.fields:
						tree_store.append(parentEntry, ["<span color='%s'>%s</span> %s" % (color, escape(field.name), field.valueMarkup),
											self._ICON_FIELD, field])
		
		elif grouping == GROUP_AUTHOR:
			
			NA_IDENT = "Unknown Author"
			
			groups = {}
			
			# group
			for entry in document.entries:
				# split list of authors
				try:
					authorValue = str(entry.findField("author").valueString)
					authors = [a.strip() for a in authorValue.split("and")]
				except KeyError:
					# no year, so put this in an extra group
					authors = [NA_IDENT]
				
				# add to group(s)
				for author in authors:
					try:
						entries = groups[author]
						entries.append(entry)
					except KeyError:
						groups[author] = [entry]
			
			# sort
			authors = groups.keys()
			authors.sort()
			
			# build tree
			for author in authors:
				entries = groups[author]
				
				parent = tree_store.append(None, ["%s <span color='%s'>%s</span>" % (escape(author), color, len(entries)), self._ICON_AUTHOR, None])
				
				for entry in entries:
					parentEntry = tree_store.append(parent, ["%s <span color='%s'>%s</span>" % (escape(entry.key), color, escape(entry.type)),
															 self._ICON_ENTRY, entry])
					
					for field in entry.fields:
						tree_store.append(parentEntry, ["<span color='%s'>%s</span> %s" % (color, escape(field.name), field.valueMarkup),
											self._ICON_FIELD, field])
		
		else:
			# no grouping, display entries and fields in a tree
			
			for entry in document.entries:
				parent = tree_store.append(None, ["%s <span color='%s'>%s</span>" % (escape(entry.key), color, escape(entry.type)), self._ICON_ENTRY, entry])
				for field in entry.fields:
					tree_store.append(parent, ["<span color='%s'>%s</span> %s" % (color, escape(field.name), field.valueMarkup), self._ICON_FIELD, field])
				
				
				
				