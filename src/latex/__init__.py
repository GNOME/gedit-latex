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
latex
"""

class LaTeXSource(object):
	"""
	This connects a portion of source with some required packages
	"""
	def __init__(self, source, packages=[]):
		self.source = source
		self.packages = packages
		
		
from logging import getLogger

# TODO: use ElementTree
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from ..base import File


class PropertyFile(dict):
	"""
	A property file is a hidden XML file that holds meta data for exactly one file.
	It can be used to store the master file of a LaTeX document fragment.
	"""
	
	__log = getLogger("PropertyFile")
	
	# TODO: insert value as TEXT node
	
	def __init__(self, file):
		"""
		Create or load the property file for a given File
		"""
		self.__file = File("%s/.%s.properties.xml" % (file.dirname, file.basename))
		
		try:
			self.__dom = minidom.parse(self.__file.path)
			
			for property_node in self.__dom.getElementsByTagName("property"):
				k = property_node.getAttribute("key")
				v = property_node.getAttribute("value")
				self.__setitem__(k, v)
				
		except IOError:
			self.__log.debug("File %s not found, creating empty one" % self.__file)
			
			self.__dom = minidom.getDOMImplementation().createDocument(None, "properties", None)
		
		except ExpatError, e:
			self.__log.error("Error parsing %s: %s" % (self.__file, e))
		
	
	def __find_node(self, k):
		for node in self.__dom.getElementsByTagName("property"):
			if node.getAttribute("key") == str(k):
				return node
		raise KeyError
	
	def __getitem__(self, k):
		return self.__find_node(k).getAttribute("value")
	
	def __setitem__(self, k, v):
		try:
			self.__find_node(k).setAttribute("value", str(v))
		except KeyError:
			node = self.__dom.createElement("property")
			node.setAttribute("key", str(k))
			node.setAttribute("value", str(v))
			self.__dom.documentElement.appendChild(node)
	
	def save(self):
		filename = self.__file.path
		
		if self.__file.exists:
			mode = "w"
		else:
			mode = "a"
		
		try:
			f = open(filename, mode)
			f.write(self.__dom.toxml())
			f.close()
			self.__log.debug("Saved to %s" % filename)
		except IOError, e:
			self.__log.error("Error saving %s: %s" % (filename, e))