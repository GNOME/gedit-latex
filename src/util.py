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
util

Utility classes, functions and decorators used at various places across
the project
"""

import gtk
import traceback
from xml.sax import saxutils


class StringReader(object):
	"""
	A simple string reader that is able to push back one character
	"""
	def __init__(self, string):
		self._iter = iter(string)
		self.offset = 0
		self._pushbackChar = None
		self._pushbackFlag = False
	
	def read(self):
		if self._pushbackFlag:
			self._pushbackFlag = False
			return self._pushbackChar
		else:
			self.offset += 1
			return self._iter.next()
	
	def unread(self, char):
		#assert not self._pushbackFlag
		
		self._pushbackChar = char
		self._pushbackFlag = True


def escape(string, remove_newlines=True):
	"""
	Prepares a string for inclusion in Pango markup and error messages
	"""
	s = saxutils.escape(string)
	return s.replace("\n", " ")
	

def open_error(message, secondary_message=None):
	"""
	Popup an error dialog window
	"""
	dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT, 
							gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, message)
	if secondary_message:
		dialog.format_secondary_text(secondary_message)
	dialog.run()
	dialog.destroy()


def caught(f):
	"""
	'caught'-decorator. This runs the decorated method in a try-except-block
	and shows an error dialog on exception.
	"""
	def new_function(*args, **kw):
		try:
			return f(*args, **kw)
		except Exception, e:
			stack = traceback.format_exc(limit=10)
			open_error(str(e), stack)
	return new_function


from gtk import glade


class GladeInterface(object):
	"""
	Utility base class for interfaces loaded from a Glade definition 
	"""
	
	filename = None
	
	def __init__(self):
		self.__tree = None
	
	def __get_tree(self):
		if not self.__tree:
			self.__tree = glade.XML(self.filename)
		return self.__tree
	
	def find_widget(self, name):
		"""
		Find a widget by its name
		"""
		return self.__get_tree().get_widget(name)
	
	def connect_signals(self, mapping):
		"""
		Auto-connect signals
		"""
		self.__get_tree().signal_autoconnect(mapping)


from uuid import uuid1
from gtk import gdk

from base import IAction


class IconAction(IAction):
	"""
	A utility class for creating actions with a custom icon instead of
	a gtk stock id.
	
	The subclass must provide a field 'icon'.
	"""
	
	@property
	def icon(self):
		"""
		Return a File object for the icon to use
		"""
		raise NotImplementedError
	
	def __init_stock_id(self):
		#
		# generate a new stock id
		#
		
		# TODO: do we have to create the stock id every time?
		
		self.__stock_id = str(uuid1())
		
		# see http://article.gmane.org/gmane.comp.gnome.gtk%2B.python/5119
		
		# TODO: what is this strange construct for?
		stock_items = (
			((self.__stock_id, "", 0, 0, "")),
		)
		
		gtk.stock_add(stock_items)
		
		factory = gtk.IconFactory()
		factory.add_default()
		
		# TODO: use IconSource, the Pixbuf is just fallback
		pixbuf = gdk.pixbuf_new_from_file(self.icon.path)
		
		icon_set = gtk.IconSet(pixbuf)
		
		factory.add(self.__stock_id, icon_set)
	
	@property
	def stock_id(self):
		if self.icon:
			if not "__stock_id" in dir(self):
				self.__init_stock_id()
			return self.__stock_id
		else:
			return None
	
	
	
	
