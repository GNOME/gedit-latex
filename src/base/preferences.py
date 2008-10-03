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
base.preferences
"""

def str_to_bool(x):
	"""
	Converts a string to a boolean value
	"""
	if type(x) is bool:
		return x
	elif type(x) is str or type(x) is unicode:
		try:
			return {"false" : False, "0" : False, "true" : True, "1" : True}[x.strip().lower()]
		except KeyError:
			print "str_to_bool: unsupported value %s" % x
	else:
		print "str_to_bool: unsupported type %s" % str(type(x))

class Preferences(object):
	"""
	A simple map storing preferences as key-value-pairs
	"""
	
	# TODO: use XML file
	
	def __new__(type):
		if not '_instance' in type.__dict__:
			type._instance = object.__new__(type)
		return type._instance
	
	def __init__(self):
		if not '_ready' in dir(self):
			self.preferences = { "ConnectOutlineToEditor" : True,
								 "ErrorBackgroundColor" : "#ffdddd",
								 "WarningBackgroundColor" : "#ffffcf",
								 "SpellingBackgroundColor" : "#ffeccf",
								 "LightForeground" : "#7f7f7f" }
			self._ready = True
	
	def get(self, key, default_value=None):
		"""
		Return the value for a given key
		
		@param key: a key string
		@param default_value: a default value to be stored and returned if the key is not found
		
		@raise KeyError: if the key is not found and no default value is given
		"""
		try:
			return self.preferences[key]
		except KeyError:
			if default_value != None:
				self.preferences[key] = default_value
				return default_value
			else:
				raise KeyError
	
	def get_bool(self, key, default_value=None):
		"""
		Special version of get() casting the string value to a boolean value
		"""
		return str_to_bool(self.get(key, default_value))
		
		
			