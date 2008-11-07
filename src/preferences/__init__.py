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
	def _on_value_changed(self, key, old_value, new_value):
		"""
		A simple key-value-pair has changed
		"""

	def _on_tools_changed(self):
		"""
		The Tools have changed
		"""


# ElementTree is part of Python 2.5
# TODO: see http://effbot.org/zone/element-index.htm
import xml.etree.ElementTree as ElementTree


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
			
			self.__tool_objects = None
			self.__tool_ids = None
						
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
		self._log.warning("<value key='%s'> not found" % key)
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
		
		# TODO: notify monitors
	
	def __notify_tools_changed(self):
		"""
		Notify monitors that the Tools have changed
		"""
		for monitor in self.__monitors:
			monitor._on_tools_changed()
	
	@property
	def tools(self):
		"""
		Return all Tools
		"""
		
#		TOOLS = [ Tool("LaTeX → PDF", [Job("rubber --inplace --maxerr -1 --pdf --short --force --warn all \"$filename\"", True, RubberPostProcessor), 
#									   Job("gnome-open $shortname.pdf", True, GenericPostProcessor)], "Create a PDF from LaTeX source" , [".tex"]),
#				  Tool("Cleanup LaTeX Build", [Job("rm -f $directory/*.aux $directory/*.log $directory/*.toc $directory/*.bbl $directory/*.blg", True, GenericPostProcessor)], "Remove LaTeX build files", [".tex"]),
#				  Tool("BibTeX → XML", [Job("bibtex2xml \"$filename\"", True, GenericPostProcessor)], "Convert BibTeX to XML", [".bib"])]
#		return TOOLS
		
		if self.__tool_objects is None:
			self.__tool_ids = {}
			self.__tool_objects = []
			for tool_element in self.__tools.findall("tool"):
				jobs = []
				for job_element in tool_element.findall("job"):
					jobs.append(Job(job_element.text.strip(), job_element.get("mustSucceed"), self.POST_PROCESSORS[job_element.get("postProcessor")]))
				extensions = tool_element.get("extensions").split()
				id = tool_element.get("id")
				tool = Tool(tool_element.get("label"), jobs, tool_element.get("description"), extensions)
				self.__tool_ids[tool] = id
				self.__tool_objects.append(tool)
		return self.__tool_objects
	
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
		Save or update the given Tool
		
		@param tool: a Tool object
		"""
		if tool in self.__tool_ids:
			# update tool
			self._log.debug("Tool element found, updating...")
			id = self.__tool_ids[tool]
			tool_element = self.__find_tool_element(id)
			tool_element.set("label", tool.label)
		else:
			# create tool
			pass
		
		self.__tools_changed = True
		
		self.__notify_tools_changed()
		
	def delete_tool(self, tool):
		"""
		Delete the given Tool
		
		@param tool: a Tool object
		"""
		
		self.__notify_tools_changed()
	
	@property
	def snippets(self):
		"""
		Return all Snippets
		"""
		snippets = []
		for snippet_element in self.__snippets.findall("snippet"):
			snippets.append(Snippet(snippet_element.get("label"), snippet_element.text))
		return snippets
	
	def save(self):
		"""
		Save the preferences to XML files
		"""
		if self.__preferences_changed:
			self._log.debug("saving preferences...")
		
			tree = ElementTree.ElementTree(self.__preferences)
			tree.write(find_resource("preferences.xml", MODE_READWRITE))
			
			self.__preferences_changed = False
		
		if self.__tools_changed:
			self._log.debug("saving tools...")
		
			tree = ElementTree.ElementTree(self.__tools)
			tree.write(find_resource("tools.xml", MODE_READWRITE))
			
			self.__tools_changed = False
			
		
		
		
		
			