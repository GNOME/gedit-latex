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
util

Utility classes, functions and decorators used at various places across
the project
"""

import logging

def require(arg_name, *allowed_types):
	"""
	Type-checking decorator (see http://code.activestate.com/recipes/454322/)
	
	Usage:
	
	@require("x", int, float)
	@require("y", float)
	def foo(x, y):
		return x+y
		
	print foo(1, 2.5)	  	# Prints 3.5.
	print foo(2.0, 2.5)		# Prints 4.5.
	print foo("asdf", 2.5) 	# Raises TypeError exception.
	print foo(1, 2)			# Raises TypeError exception.
	"""
	def make_wrapper(f):
		if hasattr(f, "wrapped_args"):
			wrapped_args = getattr(f, "wrapped_args")
		else:
			code = f.func_code
			wrapped_args = list(code.co_varnames[:code.co_argcount])

		try:
			arg_index = wrapped_args.index(arg_name)
		except ValueError:
			raise NameError, arg_name

		def wrapper(*args, **kwargs):
			if len(args) > arg_index:
				arg = args[arg_index]
				if not isinstance(arg, allowed_types):
					type_list = " or ".join(str(allowed_type) for allowed_type in allowed_types)
					raise TypeError, "Expected '%s' to be %s; was %s." % (arg_name, type_list, type(arg))
			else:
				if arg_name in kwargs:
					arg = kwargs[arg_name]
					if not isinstance(arg, allowed_types):
						type_list = " or ".join(str(allowed_type) for allowed_type in allowed_types)
						raise TypeError, "Expected '%s' to be %s; was %s." % (arg_name, type_list, type(arg))

			return f(*args, **kwargs)

		wrapper.wrapped_args = wrapped_args
		return wrapper

	return make_wrapper


from gi.repository import Gtk
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
	s = s.replace("\n", " ")
	s = s.replace("\"", "&quot;")
	return s
	

def open_error(message, secondary_message=None):
	"""
	Popup an error dialog window
	"""
	dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT, 
							Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, message)
	if secondary_message:
		# TODO: why not use markup?
		dialog.format_secondary_text(secondary_message)
	dialog.run()
	dialog.destroy()


def open_info(message, secondary_message=None):
	"""
	Popup an info dialog window
	"""
	dialog = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT, 
							Gtk.MessageType.INFO, Gtk.ButtonsType.OK, message)
	if secondary_message:
		dialog.format_secondary_markup(secondary_message)
	dialog.run()
	dialog.destroy()
	

def verbose(function):
	"""
	'verbose'-decorator. This runs the decorated method in a try-except-block
	and shows an error dialog on exception.
	"""
	def decorated_function(*args, **kw):
		try:
			return function(*args, **kw)
		except Exception, e:
			stack = traceback.format_exc(limit=10)
			open_error(str(e), stack)
	return decorated_function


#from gtk import glade


class GladeInterface(object):
	"""
	Utility base class for interfaces loaded from a Glade definition 
	"""
	
	__log = logging.getLogger("GladeInterface")
	
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
		widget = self.__get_tree().get_widget(name)
		if widget is None:
			self.__log.error("Widget '%s' could not be found in interface description '%s'" % (name, self.filename))
		return widget
	
	def connect_signals(self, mapping):
		"""
		Auto-connect signals
		"""
		self.__get_tree().signal_autoconnect(mapping)


from uuid import uuid1
from gi.repository import Gdk

from base import Action


class IconAction(Action):
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
		
		Gtk.stock_add(stock_items)
		
		factory = Gtk.IconFactory()
		factory.add_default()
		
		# TODO: use IconSource, the Pixbuf is just fallback
		pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.icon.path)
		
		icon_set = Gtk.IconSet(pixbuf)
		
		factory.add(self.__stock_id, icon_set)
	
	@property
	def stock_id(self):
		if self.icon:
			if not "__stock_id" in dir(self):
				self.__init_stock_id()
			return self.__stock_id
		else:
			return None
	
	
	
	
