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
base.interface

These classes form the interface exposed by the plugin base
"""


class Action(object):
	"""
	"""
	
	@property
	def label(self):
		raise NotImplementedError
	
	@property
	def stock_id(self):
		return None
	
	@property
	def accelerator(self):
		return None
	
	@property
	def tooltip(self):
		return None

	def activate(self, editor):
		pass


class Editor(object):
	
	def __init__(self, tab_decorator, file):
		self._tab_decorator = tab_decorator
		self._file = file
		
		self.init(file)
	
	def init(self, file):
		"""
		@param file: File object
		"""
	
	def save(self):
		"""
		The file has been saved to its original location
		"""
	
	def destroy(self):
		"""
		The edited file has been closed or saved as another file
		"""
		
		