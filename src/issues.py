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
issues
"""


class IIssueHandler(object):
	"""
	A class implementing this interface handles issues
	"""
	def issue(self, issue):
		"""
		An issue has occured
		"""
		raise NotImplementedError


class Issue(object):
	"""
	An issue can be a warning, an error, an info or a task that occures or is
	recognized during parsing and validation of a source file
	"""
	
	SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_INFO, SEVERITY_TASK = 0, 1, 2, 3
	
	def __init__(self, message, start, end, file, severity):
		"""
		@param message: a str in Pango markup
		@param start: the start offset of the issue
		@param end: the end offset
		@param file: the File object representing the file the issue occured in
		@param severity: one of SEVERITY_*
		"""
		self.message = message
		self.start = start
		self.end = end
		self.file = file
		self.severity = severity
		
	def __str__(self):
		return "Issue{'%s', %s, %s, %s, %s}" % (self.message, self.start, self.end, self.file, self.severity)