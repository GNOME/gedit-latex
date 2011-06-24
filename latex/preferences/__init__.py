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
preferences
"""

from logging import getLogger

from ..base.resources import find_resource, MODE_READWRITE

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


class IPreferencesMonitor(object):
	"""
	This is not a real interface as classes don't have to implement all
	methods
	"""
	def _on_value_changed(self, key, new_value):
		"""
		A simple key-value-pair has changed
		"""

# ElementTree is part of Python 2.5
# TODO: see http://effbot.org/zone/element-index.htm
import xml.etree.ElementTree as ElementTree

import uuid


class ObjectCache(object):
	"""
	"""
	
	# TODO:
	
	def __init__(self):
		"""
		"""
		self.__objects = None
		self.__ids = None
	
	def save(self, id, object):
		self.__ids[object] = id
		self.__objects.append(object)
	
	def find_id(self, object):
		return self.__ids[object]
	
	def delete(self, id):
		pass


class Preferences(object):
	"""
	A simple map storing preferences as key-value-pairs
	"""
	
	_log = getLogger("Preferences")
	
	def __new__(cls):
		if not '_instance' in cls.__dict__:
			cls._instance = object.__new__(cls)
		return cls._instance
	
	def __init__(self):
		if not '_ready' in dir(self):
			#
			# init Preferences singleton
			#
			
#			self.preferences = { "ConnectOutlineToEditor" : True,
#								 "ErrorBackgroundColor" : "#ffdddd",
#								 "WarningBackgroundColor" : "#ffffcf",
#								 "SpellingBackgroundColor" : "#ffeccf",
#								 "LightForeground" : "#957d47" }

			self.__monitors = []
			
			self.__preferences_changed = False
			
			# parse
			self.__preferences = ElementTree.parse(find_resource("preferences.xml", MODE_READWRITE)).getroot()
			
			self._ready = True
	
	def register_monitor(self, monitor):
		"""
		Register an object monitoring the preferences
		
		@param monitor: an object implementing IPreferencesMonitor 
		"""
		
		# TODO: support a flag indicating which parts are to be monitored
		
		self.__monitors.append(monitor)
		
	def remove_monitor(self, monitor):
		"""
		Remove a monitor
		
		@raise ValueError: if monitor is not found
		"""
		del self.__monitors[self.__monitors.index(monitor)]
	
	def get(self, key, default_value=None):
		"""
		Return the value for a given key
		
		@param key: a key string
		@param default_value: a default value to be stored and returned if the key is not found
		"""
		value_element = self.__find_value_element(key)
		if value_element is None:
			return default_value
		else:
			return value_element.text
		
		# TODO: use this as soon as ElementTree 1.3 is part of Python:
		#return self.__preferences.findtext(".//value[@key='%s']" % key, default_value)
	
	def get_bool(self, key, default_value=None):
		"""
		Special version of get() casting the string value to a boolean value
		"""
		return str_to_bool(self.get(key, default_value))
	
	def __find_value_element(self, key):
		# TODO: use this as soon as ElementTree 1.3 is part of Python:
		#value_element = self.__preferences.find(".//value[@key='%s']" % key)
		
		for element in self.__preferences.findall("value"):
			if element.get("key") == key:
				return element
		self._log.debug("<value key='%s'> not found" % key)
		return None
	
	def set(self, key, value):
		self._log.debug("set('%s', '%s')" % (key, value))

		value_element = self.__find_value_element(key)
		if value_element is None:
			self._log.debug("Creating new <value key='%s'>" % key)
			
			value_element = ElementTree.SubElement(self.__preferences, "value")
			value_element.set("key", str(key))
		value_element.text = str(value)
		
		self.__preferences_changed = True
		
		# notify monitors
		for monitor in self.__monitors:
			monitor._on_value_changed(key, value)
	
	def save(self):
		"""
		Save the preferences to XML
		"""
		if self.__preferences_changed:
			self._log.debug("Saving preferences...")
		
			tree = ElementTree.ElementTree(self.__preferences)
			tree.write(find_resource("preferences.xml", MODE_READWRITE), encoding="utf-8")
			
			self.__preferences_changed = False

