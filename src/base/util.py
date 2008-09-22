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
base.util
"""

class RangeMap(object):
	"""
	The RangeMap stores a mapping from ranges to values. That means if you store
	a value V in the range [LO, HI] with PUT(LO, HI, V) then a lookup at a
	position X returns the value when X is in [LO, HI]. Of course, there may be
	multiple values at the same position when ranges are overlapping.
	
	This is needed for
	 * spell checking (lookup word objects by cursor position)
	 * outline tree (lookup symbols by cursor position)
	"""
	
	# TODO: find a faster structure for this (maybe a B-tree for 1d intervals)
	
	def __init__(self):
		self._map = {}
	
	def put(self, lower, upper, value):
		"""
		Put value in range [lower, upper]
		"""
		self._map[(lower, upper)] = value
		
	def lookup(self, position):
		"""
		Lookup a value
		"""
		values = []
		for range, value in self._map.iteritems():
			if position >= range[0] and position <= range[1]:
				values.append(value)
		return values
	
	# TODO: maybe implement some remove() method to save memory and speedup the 
	# lookup(). Keep in mind, that only the spell checker may call a remove()
	# because for the outline tree the map is destroyed and rebuilt.

