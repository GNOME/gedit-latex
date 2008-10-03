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
latex.actions
"""

from logging import getLogger
import gtk

from ..base import IAction


class LaTeXMenuAction(IAction):
	
	label = "LaTeX"
	stock_id = None
	accelerator = None
	tooltip = None
	
	def activate(self, context):
		pass


from dialogs import NewDocumentDialog


class LaTeXNewAction(IAction):
	_log = getLogger("LaTeXNewAction")
	
	label = "New LaTeX Document..."
	stock_id = gtk.STOCK_NEW
	accelerator = None
	tooltip = "Create a new LaTeX document"
	
	_dialog = None
	
	def activate(self, context):
		self._log.debug("activate")
		
		if not self._dialog:
			self._dialog = NewDocumentDialog()
		
		template = self._dialog.run()
		if template:
			context.active_editor.insert(template)
		

class LaTeXChooseMasterAction(IAction):
	_log = getLogger("LaTeXChooseMasterAction")
	
	label = "Choose Master Document..."
	stock_id = None
	accelerator = None
	tooltip = None
	
	def activate(self, context):
		# TODO:
		self._log.debug("activate")
	

class LaTeXCommentAction(IAction):
	_log = getLogger("LaTeXCommentAction")
	
	label = "Toggle Comment"
	stock_id = None
	accelerator = "<Ctrl><Alt>C"
	tooltip = None
	
	def activate(self, context):
		context.active_editor.toggle_comment("%")
		
		
class LaTeXSpellCheckAction(IAction):
	_log = getLogger("LaTeXSpellCheckAction")
	
	label = "Spell Check"
	stock_id = None
	accelerator = "<Ctrl><Alt>S"
	tooltip = None
	
	def activate(self, context):
		context.active_editor.spell_check()


from ..util import IconAction
from ..base import Template, File
from ..base.resources import find_resource
from . import LaTeXSource


class LaTeXFontFamilyAction(IconAction):
	label = "Font Family"
	accelerator = None
	tooltip = "Font Family"
	icon = File(find_resource("icons/bf.png"))
	
	def activate(self, context):
		pass

class LaTeXFontFamilyMenuAction(IAction):
	label = "Font Family"
	accelerator = None
	tooltip = "Font Family"
	stock_id = None
	
	def activate(self, context):
		pass


class LaTeXBoldAction(IconAction):
	label = "Bold"
	accelerator = None
	tooltip = "Bold"
	icon = File(find_resource("icons/bf.png"))
	
	def activate(self, context):
		pass
	

class LaTeXItalicAction(IconAction):
	label = "Italic"
	accelerator = None
	tooltip = "Italic"
	icon = File(find_resource("icons/it.png"))
	
	def activate(self, context):
		pass


class LaTeXItemizeAction(IconAction):
	label = "Itemize"
	accelerator = None
	tooltip = "Itemize"
	icon = File(find_resource("icons/itemize.png"))
	
	def activate(self, context):
		context.active_editor.insert(LaTeXSource(Template("\\begin{itemize}\n\t\\item $_\n\\end{itemize}"), []))


class LaTeXEnumerateAction(IconAction):
	label = "Enumerate"
	accelerator = None
	tooltip = "Enumerate"
	icon = File(find_resource("icons/enumerate.png"))
	
	def activate(self, context):
		context.active_editor.insert(LaTeXSource(Template("\\begin{enumerate}\n\t\\item $_\n\\end{enumerate}"), []))
		
		
		