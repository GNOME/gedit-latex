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
latex.completion

LaTeX-specific completion classes
"""

from logging import getLogger

from ..base import ICompletionHandler, IProposal, Template


class LaTeXTemplateProposal(IProposal):
	"""
	A proposal inserting a Template when activated
	"""
	icon = None
	
	def __init__(self, template, label):
		self._template = template
		self._label = label
	
	@property
	def source(self):
		return self._template
	
	@property
	def label(self):
		return self._label
	
	@property
	def details(self):
		return None
	
	@property
	def overlap(self):
		return 0
	

class LaTeXProposal(IProposal):
	"""
	A proposal inserting a simple string when activated
	"""
	icon = None
	
	def __init__(self, source):
		self._source = source
	
	@property
	def source(self):
		return self._source
	
	@property
	def label(self):
		return self._source
	
	@property
	def details(self):
		return None
	
	@property
	def overlap(self):
		return 0
	

from model import LanguageModelFactory


class LaTeXCompletionHandler(ICompletionHandler):
	"""
	This implements the LaTeX-specific code completion
	"""
	_log = getLogger("LaTeXCompletionHandler")
	
	trigger_keys = ["backslash", "braceleft"]
	prefix_delimiters = ["\\"]
	strip_delimiter = False			# don't remove the '\' from the prefix
	
	def __init__(self):
		self._log.debug("init")
		
		self._language_model = LanguageModelFactory().create_language_model()
	
	def complete(self, prefix):
		"""
		Try to complete a given prefix
		"""
		#self._log.debug("complete(%s)" % prefix)
		
		proposals = [LaTeXTemplateProposal(Template("Hello[${One}][${Two}][${Three}]"), "Hello[Some]"), LaTeXProposal("\\world")]
		
		return proposals
	
	