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
from ..util import IconAction


class LaTeXTemplateAction(IconAction):
	"""
	Utility class for quickly defining Actions inserting a LaTeX template
	"""
	accelerator = None
	
	icon_name = None
	template_source = None
	packages = []
	
	@property
	def icon(self):
		return File(find_resource("icons/%s.png" % self.icon_name))
	
	def activate(self, context):
		context.active_editor.insert(LaTeXSource(Template(self.template_source), self.packages))


class LaTeXMenuAction(IAction):
	
	label = "LaTeX"
	stock_id = None
	accelerator = None
	tooltip = None
	
	def activate(self, context):
		pass


from dialogs import NewDocumentDialog
from editor import LaTeXEditor


class LaTeXNewAction(IAction):
	_log = getLogger("LaTeXNewAction")
	
	label = "New LaTeX Document..."
	stock_id = gtk.STOCK_NEW
	accelerator = "<Ctrl><Alt>N"
	tooltip = "Create a new LaTeX document"
	
	_dialog = None
	
	def activate(self, context):
		self._log.debug("activate")
		
		if not type(context.active_editor) is LaTeXEditor:
			# the active tab doesn't contain a LaTeX file
			# TODO: choose location and create new file and before continuing
			raise NotImplementedError
		
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


from ..base import Template, File
from ..base.resources import find_resource
from . import LaTeXSource


# TODO: subclass LaTeXTemplateAction


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


class LaTeXItemizeAction(LaTeXTemplateAction):
	label = "Itemize"
	tooltip = "Itemize"
	icon_name = "itemize"
	template_source = "\\begin{itemize}\n\t\\item $_\n\\end{itemize}"


class LaTeXEnumerateAction(LaTeXTemplateAction):
	label = "Enumerate"
	tooltip = "Enumerate"
	icon_name = "enumerate"
	template_source = "\\begin{enumerate}\n\t\\item $_\n\\end{enumerate}"


class LaTeXDescriptionAction(LaTeXTemplateAction):
	label = "Description"
	tooltip = "Description"
	icon_name = "description"
	template_source = "\\begin{description}\n\t\\item[$_]\n\\end{description}"
	

class LaTeXStructureAction(IconAction):
	label = "Structure"
	accelerator = None
	tooltip = "Structure"
	icon = File(find_resource("icons/section.png"))
	
	def activate(self, context):
		pass


class LaTeXStructureMenuAction(IAction):
	label = "Structure"
	accelerator = None
	tooltip = "Structure"
	stock_id = None
	
	def activate(self, context):
		pass


class LaTeXPartAction(LaTeXTemplateAction):
	label = "Part"
	tooltip = "Part"
	icon_name = "part"
	template_source = "\\part{$_}"


class LaTeXChapterAction(LaTeXTemplateAction):
	label = "Chapter"
	tooltip = "Chapter"
	icon_name = "chapter"
	template_source = "\\chapter{$_}"

		
class LaTeXSectionAction(LaTeXTemplateAction):
	label = "Section"
	tooltip = "Section"
	icon_name = "section"
	template_source = "\\section{$_}"
		

class LaTeXSubsectionAction(LaTeXTemplateAction):
	label = "Subsection"
	tooltip = "Subsection"
	icon_name = "subsection"
	template_source = "\\subsection{$_}"
		

class LaTeXParagraphAction(LaTeXTemplateAction):
	label = "Paragraph"
	tooltip = "Paragraph"
	icon_name = "paragraph"
	template_source = "\\paragraph{$_}"
		
		
class LaTeXSubparagraphAction(LaTeXTemplateAction):
	label = "Subparagraph"
	tooltip = "Subparagraph"
	icon_name = "paragraph"
	template_source = "\\subparagraph{$_}"
	
	
class LaTeXGraphicsAction(IconAction):
	label = "Insert Graphics"
	accelerator = None
	tooltip = "Insert Graphics"
	icon = File(find_resource("icons/graphics.png"))
	
	def activate(self, context):
		pass
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
		