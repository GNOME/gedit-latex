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
tools.postprocess
"""

from logging import getLogger
import re

from ..issues import Issue
from ..util import escape


class PostProcessor(object):
	"""
	The contract for a post-processor
	"""
	
	def process(self, file, stdout, stderr, condition):
		"""
		@param file: the File processed by the Tool
		@param stdout: the output written to STDOUT
		@param stderr: the output written to STDERR
		@param condition: the exit condition of the Tool process
		"""
		raise NotImplementedError
	
	@property
	def successful(self):
		"""
		Return whether the Tool process was successful
		"""
		raise NotImplementedError
		
	@property
	def issues(self):
		"""
		Return a list of Issues
		"""
		raise NotImplementedError
	
	@property
	def summary(self):
		"""
		Return a short string summarizing the result of the Tool process
		"""
		raise NotImplementedError
	
	
class GenericPostProcessor(PostProcessor):
	"""
	This just interprets the exit condition of the process
	"""
	
	_log = getLogger("GenericPostProcessor")
	
	name = "GenericPostProcessor"
	
	def __init__(self):
		self._issues = None
		self._summary = None
	
	def process(self, file, stdout, stderr, condition):
		self._issues = []
		self._summary = ""
		self._condition = condition
	
	@property
	def successful(self):
		return not bool(self._condition)
	
	@property
	def issues(self):
		return self._issues
	
	@property
	def summary(self):
		return self._summary
