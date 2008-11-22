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
snippets
"""

class Snippet(object):
	def __init__(self, label, expression, active, packages):
		"""
		@param label: a str label for this Snippet
		@param expression: a str expression in the template format
		@param active: True if this Snippet is active and should be proposed by completion
		@param packages: a list of package names required by this Snippet
		"""
		self.label = label
		self.expression = expression
		self.active = active
		self.packages = packages
	
	def __str__(self):
		return "Snippet{label=%s, active=%s, packages=%s}" % (self.label, self.active, self.packages)
	