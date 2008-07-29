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
tools

A tool is what we called a build profile before. This is more generic.
It can be used for cleaning up, converting files and for building PDFs etc.
"""

from logging import getLogger


class Tool(object):
	def __init__(self, label, extensions, jobs, description):
		self._label = label
		self._extensions = extensions
		self._jobs = jobs
		self._description = description
	
	@property
	def label(self):
		"""
		A label used for this tool
		"""
		return self._label
	
	@property
	def description(self):
		"""
		A label used for this tool
		"""
		return self._description
	
	@property
	def extensions(self):
		"""
		The extensions this tool applies for (return None for every extension)
		"""
		return self._extensions
	
	@property
	def jobs(self):
		return self._jobs
	
	def __str__(self):
		return "Tool{%s}" % self._label
	
	
class ToolJob():
	def __init__(self, command_template, must_succeed):
		self._command_template = command_template
		self._must_succeed = must_succeed
	
	@property
	def command_template(self):
		return self._command_template
	
	@property
	def must_succeed(self):
		return self._must_succeed


import gtk

from ..base.interface import Action

	
class ToolAction(Action):
	
	_log = getLogger("ToolAction")
	
	def init(self, tool):
		self._tool = tool
	
	@property
	def label(self):
		return self._tool.label
	
	@property
	def tooltip(self):
		return self._tool.description
	
	@property
	def stock_id(self):
		return gtk.STOCK_CONVERT
	
	def activate(self, editor):
		self._log.debug("activate: " + str(self._tool))

