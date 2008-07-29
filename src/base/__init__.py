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
base

These are classes that are used and returned by the base layer but should
not be created, extended or implemented.
"""

from urlparse import urlparse
from os.path import splitext


class File(object):
	"""
	Abstracts from filename
	"""
	def __init__(self, uri):
		self._uri = uri
	
	@property
	def path(self):
		"""
		@return: filename
		"""
		return urlparse(self._uri).path
	
	@property
	def extension(self):
		return splitext(self.path)[1]
	
	@property
	def shortname(self):
		return splitext(self.path)[0]
		
	@property
	def uri(self):
		"""
		@return: general URI of this file
		"""
		return self._uri
	
	def __str__(self):
		return self._uri
	
	
class Marker(object):
	"""
	A Marker created by the Editor
	"""
	def __init__(self, left_mark, right_mark):
		self._left_mark = left_mark
		self._right_mark = right_mark
	
	@property
	def left_mark(self):
		return self._left_mark
	
	@property
	def right_mark(self):
		return self._right_mark

	