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
bibtex.completion
"""

from logging import getLogger
from gtk import gdk

from ..base.resources import find_resource
from ..base import ICompletionHandler, IProposal, Template


class BibTeXProposal(IProposal):
	"""
	"""
	icon = gdk.pixbuf_new_from_file(find_resource("icons/document.png"))
	
	def __init__(self, overlap, source, label, details):
		self._source = source
		self._overlap = overlap
		self._label = label
		self._details = details
	
	@property
	def source(self):
		return self._source
	
	@property
	def label(self):
		return self._label
	
	@property
	def details(self):
		return self._details
	
	@property
	def overlap(self):
		return self._overlap


from ..preferences import Preferences
from model import Definition, DefinitionParser


# TODO: put the __get_*_from_entry_type methods into BibTeXEntryTypeProposal


class BibTeXCompletionHandler(ICompletionHandler):
	"""
	This implements the BibTeX-specific code completion
	"""
	_log = getLogger("BibTeXCompletionHandler")
	
	trigger_keys = []
	prefix_delimiters = ["@"]
	strip_delimiter = False			# don't remove the '@' from the prefix
	
	def __init__(self):
		self._color = Preferences().get("LightForeground", "#957d47")
		
		self._model = Definition()
		DefinitionParser().parse(self._model, find_resource("bibtex.xml"))
	
	def complete(self, prefix):
		self._log.debug("complete: '%s'" % prefix)
		
		proposals = []
		
		if len(prefix) == 1:
			# propose all entry types
			types = self._model.types
			proposals = self.__get_proposals_from_entry_types(types, 0)
		else:
			if prefix[1:].isalpha():
				type_name_prefix = prefix[1:].lower()
				overlap = len(type_name_prefix) + 1
				# @[a-zA-Z]+
				types = [type for type in self._model.types if type.name.lower().startswith(type_name_prefix)]
				proposals = self.__get_proposals_from_entry_types(types, overlap)
		
		return proposals
	
	def __get_source_from_entry_type(self, type):
		template = "@%s{${Identifier}" % type.name
		for field in type.requiredFields:
			template += ",\n\t%s = {${%s}}" % (field.name, field.label)
		template += "\n}"
		return Template(template)
	
	def __get_details_from_entry_type(self, type):
		details = "@%s{<span color='%s'>Identifier</span>" % (type.name, self._color)
		for field in type.requiredFields:
			details += ",\n\t%s = {<span color='%s'>%s</span>}" % (field.name, self._color, field.label)
		details += "\n}"
		return details
	
	def __get_proposals_from_entry_types(self, types, overlap):
		"""
		@param types: a list of EntryTypes 
		"""
		proposals = []
		for type in types:
			proposals.append(BibTeXProposal(overlap, self.__get_source_from_entry_type(type), type.name, self.__get_details_from_entry_type(type)))
		return proposals
	
	