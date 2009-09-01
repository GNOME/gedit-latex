# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2009 Michael Zeising
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
from ..tools import Tool, Job
from ..tools.postprocess import GenericPostProcessor, RubberPostProcessor, LaTeXPostProcessor
from ..snippets import Snippet


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

	def _on_snippets_changed(self):
		"""
		The snippets have changed
		"""

	def _on_tools_changed(self):
		"""
		The Tools have changed
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
	
	# maps names to classes
	POST_PROCESSORS = {"GenericPostProcessor" : GenericPostProcessor, 
					   "LaTeXPostProcessor" : LaTeXPostProcessor, 
					   "RubberPostProcessor" : RubberPostProcessor}
	
	def __new__(type):
		if not '_instance' in type.__dict__:
			type._instance = object.__new__(type)
		return type._instance
	
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
			self.__tools_changed = False
			self.__snippets_changed = False
			
			# TODO: use some object cache mechanism instead of those fields
			self.__tool_objects = None
			self.__tool_ids = None
			
			self.__snippet_objects = None
			self.__snippet_ids = None
						
			# parse
			self.__preferences = ElementTree.parse(find_resource("preferences.xml", MODE_READWRITE)).getroot()
			self.__tools = ElementTree.parse(find_resource("tools.xml", MODE_READWRITE)).getroot()
			self.__snippets = ElementTree.parse(find_resource("snippets.xml", MODE_READWRITE)).getroot()
			
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
	
	def __notify_tools_changed(self):
		"""
		Notify monitors that the Tools have changed
		"""
		for monitor in self.__monitors:
			monitor._on_tools_changed()
	
	def __notify_snippets_changed(self):
		"""
		Notify monitors that the Tools have changed
		"""
		for monitor in self.__monitors:
			monitor._on_snippets_changed()
	
	@property
	def tools(self):
		"""
		Return all Tools
		"""
		self.__tool_ids = {}
		
		tools = []
		
		for tool_element in self.__tools.findall("tool"):
			jobs = []
			for job_element in tool_element.findall("job"):
				jobs.append(Job(job_element.text.strip(), str_to_bool(job_element.get("mustSucceed")), self.POST_PROCESSORS[job_element.get("postProcessor")]))
			
			assert not tool_element.get("extensions") is None
			
			extensions = tool_element.get("extensions").split()
			accelerator = tool_element.get("accelerator")
			id = tool_element.get("id")
			tool = Tool(tool_element.get("label"), jobs, tool_element.get("description"), accelerator, extensions)
			self.__tool_ids[tool] = id
			
			tools.append(tool)
			
		return tools
	
	def __find_tool_element(self, id):
		"""
		Find the tool element with the given id 
		"""
		for element in self.__tools.findall("tool"):
			if element.get("id") == id:
				return element
		self._log.warning("<tool id='%s'> not found" % id)
		return None
	
	def save_or_update_tool(self, tool):
		"""
		Save or update the XML subtree for the given Tool
		
		@param tool: a Tool object
		"""
		tool_element = None
		if tool in self.__tool_ids:
			# find tool
			self._log.debug("Tool element found, updating...")
			
			id = self.__tool_ids[tool]
			tool_element = self.__find_tool_element(id)
		else:
			# create tool
			self._log.debug("Creating new Tool...")
			
			id = str(uuid.uuid4())		# random UUID
			self.__tool_ids[tool] = id
			
			tool_element = ElementTree.SubElement(self.__tools, "tool")
			tool_element.set("id", id)
		
		tool_element.set("label", tool.label)
		tool_element.set("description", tool.description)
		tool_element.set("extensions", " ".join(tool.extensions))
		tool_element.set("accelerator", tool.accelerator)
		
		# remove all jobs
		for job_element in tool_element.findall("job"):
			tool_element.remove(job_element)
			
		# append new jobs
		for job in tool.jobs:
			job_element = ElementTree.SubElement(tool_element, "job")
			job_element.set("mustSucceed", str(job.must_succeed))
			job_element.set("postProcessor", job.post_processor.name)
			job_element.text = job.command_template
		
		self.__tools_changed = True
		
		self.__notify_tools_changed()
	
	def swap_tools(self, tool_1, tool_2):
		"""
		Swap the order of two Tools
		"""
		# grab their ids
		id_1 = self.__tool_ids[tool_1]
		id_2 = self.__tool_ids[tool_2]
		
		self._log.debug("Tool IDs are {%s: %s, %s, %s}" % (tool_1.label, id_1, tool_2.label, id_2))
		
		tool_element_1 = None
		tool_element_2 = None
		
		# find the XML elements and current indexes of the tools
		i = 0
		for tool_element in self.__tools:
			if tool_element.get("id") == id_1:
				tool_element_1 = tool_element
				index_1 = i
			elif tool_element.get("id") == id_2:
				tool_element_2 = tool_element
				index_2 = i
			
			if not (tool_element_1 is None or tool_element_2 is None):
				break
			
			i += 1
		
		self._log.debug("Found XML elements, indexes are {%s: %s, %s, %s}" % (tool_1.label, index_1, tool_2.label, index_2))
		
		# remove them from the XML model and insert them again in swapped order
		self.__tools.remove(tool_element_1)
		self.__tools.remove(tool_element_2)
		
		self._log.debug("Removed elements from XML model")
		
		self.__tools.insert(index_1, tool_element_2)
		self.__tools.insert(index_2, tool_element_1)
		
		self._log.debug("Inserted them in swapped order")
		
		# notify changes
		self.__tools_changed = True
		self.__notify_tools_changed()
	
	def delete_tool(self, tool):
		"""
		Delete the given Tool
		
		@param tool: a Tool object
		"""
		try:
			id = self.__tool_ids[tool]
			tool_element = self.__find_tool_element(id)
			self.__tools.remove(tool_element)
			
			del self.__tool_ids[tool]
			
			self.__tools_changed = True
		except KeyError, e:
			self._log.error("delete_tool: %s" % e)
		
		self.__notify_tools_changed()
	
	def __find_snippet_element(self, id):
		for element in self.__snippets.findall("snippet"):
			if element.get("id") == id:
				return element
		self._log.warning("<snippet id='%s'> not found" % id)
		return None
	
	@property
	def snippets(self):
		"""
		Return and cache all Snippets
		"""
		if self.__snippet_objects is None:
			self.__snippet_ids = {}
			self.__snippet_objects = []
			for snippet_element in self.__snippets.findall("snippet"):
				id = snippet_element.get("id")
				label = snippet_element.get("label")
				packages = snippet_element.get("packages")
				if packages is None:
					packages = []
				else:
					packages = packages.split()
				expression = snippet_element.text.strip()
				active = str_to_bool(snippet_element.get("active"))
				snippet = Snippet(label, expression, active, packages)
				self.__snippet_ids[snippet] = id
				self.__snippet_objects.append(snippet)
		return self.__snippet_objects
	
	def save_or_update_snippet(self, snippet):
		"""
		@param snippet: a snippets.Snippet object
		"""
		snippet_element = None
		if snippet in self.__snippet_ids:
			# find snippet
			self._log.debug("Snippet element found, updating...")
			
			id = self.__snippet_ids[snippet]
			snippet_element = self.__find_snippet_element(id)
		else:
			# create snippet
			self._log.debug("Creating new Snippet...")
			
			id = str(uuid.uuid4())		# random UUID
			self.__snippet_ids[snippet] = id
			self.__snippet_objects.append(snippet)
			
			snippet_element = ElementTree.SubElement(self.__snippets, "snippet")
			snippet_element.set("id", id)
		
		snippet_element.set("label", snippet.label)
		snippet_element.set("packages", " ".join(snippet.packages))
		snippet_element.set("active", str(snippet.active))
		snippet_element.text = snippet.expression
		
		self.__snippets_changed = True
		
		self.__notify_snippets_changed()
	
	def save(self):
		"""
		Save the preferences to XML
		"""
		if self.__preferences_changed:
			self._log.debug("Saving preferences...")
		
			tree = ElementTree.ElementTree(self.__preferences)
			tree.write(find_resource("preferences.xml", MODE_READWRITE), encoding="utf-8")
			
			self.__preferences_changed = False
		
		if self.__tools_changed:
			self._log.debug("Saving tools...")
		
			tree = ElementTree.ElementTree(self.__tools)
			tree.write(find_resource("tools.xml", MODE_READWRITE), encoding="utf-8")
			
			self.__tools_changed = False
		
		if self.__snippets_changed:
			self._log.debug("Saving snippets...")
		
			tree = ElementTree.ElementTree(self.__snippets)
			tree.write(find_resource("snippets.xml", MODE_READWRITE), encoding="utf-8")
			
			self.__snippets_changed = False
			
		
		
		
		
			