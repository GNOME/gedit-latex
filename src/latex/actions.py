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
	

class LaTeXNewAction(IAction):
	_log = getLogger("LaTeXNewAction")
	
	label = "New LaTeX Document..."
	stock_id = None
	accelerator = None
	tooltip = None
	
	def activate(self, context):
		# TODO:
		self._log.debug("activate")
		

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
		
		
		
		
		