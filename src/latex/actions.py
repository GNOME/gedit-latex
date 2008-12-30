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


from ..base import Template, File
from ..base.resources import find_resource
from . import LaTeXSource
from dialogs import NewDocumentDialog
from editor import LaTeXEditor


class LaTeXNewAction(IAction):
	label = "New LaTeX Document..."
	stock_id = gtk.STOCK_NEW
	accelerator = "<Ctrl><Alt>N"
	tooltip = "Create a new LaTeX document"
	
	_dialog = None
	
	def activate(self, context):
		if not self._dialog:
			self._dialog = NewDocumentDialog()
		
		# we may not open the empty file and insert a Temlate here
		# because WindowContext.activate_editor calls gedit.Window.create_tab_from_uri 
		# which is async
		
		if self._dialog.run() == 1:
			file = self._dialog.file
			file.create(self._dialog.source)
			context.activate_editor(file)
		

class LaTeXChooseMasterAction(IAction):
	_log = getLogger("LaTeXChooseMasterAction")
	
	label = "Choose Master Document..."
	stock_id = None
	accelerator = None
	tooltip = None
	
	def activate(self, context):
		# TODO:
		self._log.debug("activate")
		
		
class LaTeXUseBibliographyAction(IconAction):
	_log = getLogger("LaTeXUseBibliographyAction")
	
	label = "Use Bibliography..."
	icon = File(find_resource("icons/bib.png"))
	accelerator = None
	tooltip = "Use Bibliography"
	
	_dialog = None
	
	def activate(self, context):
		if not self._dialog:
			from dialogs import UseBibliographyDialog
			self._dialog = UseBibliographyDialog()
			
		source = self._dialog.run_dialog(context.active_editor.edited_file)
		if source:
			editor = context.active_editor
			
			assert type(editor) is LaTeXEditor
			
			editor.insert_at_position(source + "\n\n", LaTeXEditor.POSITION_BIBLIOGRAPHY)
	

class LaTeXCommentAction(IAction):
	label = "Toggle Comment"
	stock_id = None
	accelerator = "<Ctrl><Alt>C"
	tooltip = "Toggle LaTeX comment on the selection"
	
	def activate(self, context):
		context.active_editor.toggle_comment("%")


class LaTeXSpellCheckAction(IAction):
	label = "Spell Check"
	stock_id = gtk.STOCK_SPELL_CHECK
	accelerator = "<Ctrl><Alt>S"
	tooltip = "Run LaTeX-aware spell check on the document"
	
	def activate(self, context):
		context.active_editor.spell_check()


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


class LaTeXBoldAction(LaTeXTemplateAction):
	label = "Bold"
	tooltip = "Bold"
	icon_name = "bf"
	template_source = "\\textbf{$_}"


class LaTeXItalicAction(LaTeXTemplateAction):
	label = "Italic"
	tooltip = "Italic"
	icon_name = "it"
	template_source = "\\textit{$_}"
	
	
class LaTeXUnderlineAction(LaTeXTemplateAction):
	label = "Underline"
	tooltip = "Underline"
	icon_name = "underline"
	template_source = "\\underline{$_}"
	
	
class LaTeXSmallCapitalsAction(LaTeXTemplateAction):
	label = "Small Capitals"
	tooltip = "Small Capitals"
	icon_name = "sc"
	template_source = "\\textsc{$_}"
	
	
class LaTeXRomanAction(LaTeXTemplateAction):
	label = "Roman"
	tooltip = "Roman"
	icon_name = "rm"
	template_source = "\\textrm{$_}"
	
	
class LaTeXSansSerifAction(LaTeXTemplateAction):
	label = "Sans Serif"
	tooltip = "Sans Serif"
	icon_name = "sf"
	template_source = "\\textsf{$_}"
	
	
class LaTeXTypewriterAction(LaTeXTemplateAction):
	label = "Typewriter"
	tooltip = "Typewriter"
	icon_name = "tt"
	template_source = "\\texttt{$_}"

# TODO: Blackboard Bold, Caligraphy, Fraktur

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
	
	dialog = None
	
	def activate(self, context):
		if not self.dialog:
			from dialogs import InsertGraphicsDialog
			self.dialog = InsertGraphicsDialog()
		source = self.dialog.run(context.active_editor.edited_file)
		if source:
			context.active_editor.insert(source)


class LaTeXTableAction(IconAction):
	label = "Insert Table or Matrix"
	accelerator = None
	tooltip = "Insert Table or Matrix"
	icon = File(find_resource("icons/table.png"))
	
	dialog = None
	
	def activate(self, context):
		if not self.dialog:
			from dialogs import InsertTableDialog
			self.dialog = InsertTableDialog()
		source = self.dialog.run()
		if source:
			context.active_editor.insert(source)
	
	
class LaTeXListingAction(IconAction):
	label = "Insert Source Code Listing"
	accelerator = None
	tooltip = "Insert Source Code Listing"
	icon = File(find_resource("icons/listing.png"))
	
	dialog = None
	
	def activate(self, context):
		if not self.dialog:
			from dialogs import InsertListingDialog
			self.dialog = InsertListingDialog()
		source = self.dialog.run(context.active_editor.edited_file)
		if source:
			context.active_editor.insert(source)
			
			
class LaTeXJustifyLeftAction(LaTeXTemplateAction):
	label = "Justify Left"
	tooltip = "Justify Left"
	icon_name = "justify-left"
	template_source = "\\begin{flushleft}$_\\end{flushleft}"
	
	
class LaTeXJustifyCenterAction(LaTeXTemplateAction):
	label = "Justify Center"
	tooltip = "Justify Center"
	icon_name = "justify-center"
	template_source = "\\begin{center}$_\\end{center}"


class LaTeXJustifyRightAction(LaTeXTemplateAction):
	label = "Justify Right"
	tooltip = "Justify Right"
	icon_name = "justify-right"
	template_source = "\\begin{flushright}$_\\end{flushright}"
	

class LaTeXMathMenuAction(IAction):
	label = "Math"
	accelerator = None
	tooltip = "Math"
	stock_id = None
	
	def activate(self, context):
		pass


class LaTeXMathAction(LaTeXTemplateAction):
	label = "Mathematical Environment"
	tooltip = "Mathematical Environment"
	icon_name = "math"
	template_source = "$ $_ $"
	
	
class LaTeXDisplayMathAction(LaTeXTemplateAction):
	label = "Centered Formula"
	tooltip = "Centered Formula"
	icon_name = "displaymath"
	template_source = "\\[ $_ \\]"
	
	
class LaTeXEquationAction(LaTeXTemplateAction):
	label = "Numbered Equation"
	tooltip = "Numbered Equation"
	icon_name = "equation"
	template_source = """\\begin{equation}
	$_
\\end{equation}"""


class LaTeXUnEqnArrayAction(LaTeXTemplateAction):
	label = "Array of Equations"
	tooltip = "Array of Equations"
	icon_name = "uneqnarray"
	packages = ["amsmath"]
	template_source = """\\begin{align*}
	$_
\\end{align*}"""


class LaTeXEqnArrayAction(LaTeXTemplateAction):
	label = "Numbered Array of Equations"
	tooltip = "Numbered Array of Equations"
	icon_name = "eqnarray"
	packages = ["amsmath"]
	template_source = """\\begin{align}
	$_
\\end{align}"""
	
	
	
	
	
	
	
	
	
	
	
	
	
	
		