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

from ..base.interface import IAction


class LaTeXMenuAction(IAction):
	@property
	def label(self):
		return "LaTeX"
	
	@property
	def stock_id(self):
		return None
	
	@property
	def accelerator(self):
		return None
	
	@property
	def tooltip(self):
		return None
	
	def activate(self, editor):
		pass
	

class LaTeXNewAction(IAction):
	_log = getLogger("LaTeXNewAction")
	
	@property
	def label(self):
		return "New LaTeX Document..."
	
	@property
	def stock_id(self):
		#return gtk.STOCK_NEW
		return None
	
	@property
	def accelerator(self):
		return None
	
	@property
	def tooltip(self):
		return None
	
	def activate(self, editor):
		self._log.debug("activate")
	

class LaTeXCommentAction(IAction):
	_log = getLogger("LaTeXCommentAction")
	
	@property
	def label(self):
		return "Toggle Comment"
	
	@property
	def stock_id(self):
		return None
	
	@property
	def accelerator(self):
		return None
	
	@property
	def tooltip(self):
		return None
	
	def activate(self, editor):
		self._log.debug("activate")
		
		
		