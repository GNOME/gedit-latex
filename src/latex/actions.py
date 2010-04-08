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
latex.actions
"""

from logging import getLogger
import gtk

from ..base import Action
from ..util import IconAction
from ..preferences import Preferences


class LaTeXAction(Action):
	#extensions = [".tex"]
	extensions = Preferences().get("LatexExtensions", ".tex").split(" ")


class LaTeXIconAction(IconAction):
	#extensions = [".tex"]
	extensions = Preferences().get("LatexExtensions", ".tex").split(" ")


class LaTeXTemplateAction(LaTeXIconAction):
	"""
	Utility base class for quickly defining Actions inserting a LaTeX template
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


class LaTeXMenuAction(LaTeXAction):
	
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


class LaTeXNewAction(Action):
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


from dialogs import ChooseMasterDialog
from . import PropertyFile


class LaTeXChooseMasterAction(LaTeXAction):
	_log = getLogger("LaTeXChooseMasterAction")
	
	label = "Choose Master Document..."
	stock_id = None
	accelerator = None
	tooltip = None
	
	def activate(self, context):
		editor = context.active_editor
		assert type(editor) is LaTeXEditor
		
		file = editor._file		# FIXME: access to private member
		
		# load property file
		property_file = PropertyFile(file)
		
		master_filename = ChooseMasterDialog().run(file.dirname)
		if master_filename:
			# relativize the master filename
			master_filename = File(master_filename).relativize(file.dirname, True)
			
			property_file["MasterFilename"] = master_filename
			property_file.save()
		
		
class LaTeXForwardSearchAction(LaTeXAction):
	_log = getLogger("LaTeXForwardSearchAction")
	
	label = "Find Position In DVI"
	stock_id = gtk.STOCK_FIND
	accelerator = None
	tooltip = None
	
	def activate(self, context):
		editor = context.active_editor
		assert type(editor) is LaTeXEditor
		
		tex_filename = "%s.tex" % editor.edited_file.shortname
		dvi_filename = "%s.dvi" % editor.file.shortname
		line, column = editor.cursor_position
		
		command = "xdvi -sourceposition \"%s:%s %s\" \"%s\"" % (line + 1, column, tex_filename, dvi_filename)
		self._log.debug(command)
		
		import os
		os.system(command)


from parser import LaTeXParser, Node
from ..issues import MockIssueHandler


class LaTeXCloseEnvironmentAction(LaTeXIconAction):
	_log = getLogger("LaTeXCloseEnvironmentAction")
	
	label = "Close Nearest Environment"
	icon = File(find_resource("icons/close_env.png"))
	accelerator = "<Ctrl><Alt>E"
	tooltip = "Close the nearest TeX environment at left of the cursor"
	
	def activate(self, context):
		# FIXME: use the document model of the Editor
		
		editor = context.active_editor
			
		assert type(editor) is LaTeXEditor
		
		# push environments on stack and find nearest one to close
		
		try:
			self._stack = []
			self._find_open_environments(LaTeXParser().parse(editor.content_at_left_of_cursor, None, MockIssueHandler()))
			
			if len(self._stack) > 0:
				editor.insert("\\end{%s}" % self._stack[-1])
			else:
				self._log.debug("No environment to close")
		except ValueError:
			self._log.debug("Environments are malformed")
		
	def _find_open_environments(self, parent_node):
		for node in parent_node:
			recurse = True
			if node.type == Node.COMMAND:
				if node.value == "begin":
					# push environment on stack
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					self._stack.append(environ)
					
				elif node.value == "end":
					# pop from stack
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					try:
						top_environ = self._stack.pop()
						if top_environ != environ:
							raise ValueError()
					except IndexError:
						raise ValueError()
				
				elif node.value == "newcommand":
					recurse = False
					
			if recurse:
				self._find_open_environments(node)

		
class LaTeXUseBibliographyAction(LaTeXIconAction):
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
	

class LaTeXCommentAction(LaTeXAction):
	label = "Toggle Comment"
	stock_id = None
	accelerator = "<Ctrl><Alt>C"
	tooltip = "Toggle LaTeX comment on the selection"
	
	def activate(self, context):
		context.active_editor.toggle_comment("%")


from ..util import verbose
from livepreview import LaTeXPreviews


class LaTeXPreviewAction(LaTeXAction):
	label = "Embedded Preview"
	stock_id = gtk.STOCK_ZOOM_FIT
	tooltip = None
	accelerator = None
	
	def activate(self, context):
		pass
	

class LaTeXPreviewToggleAction(LaTeXAction):
	_log = getLogger("LaTeXPreviewToggleAction")
	
	label = "Toggle Embedded Preview"
	stock_id = gtk.STOCK_ZOOM_FIT				 # TODO: Create and use a better icon 
	accelerator = "<Ctrl><Shift>T"
	tooltip = "Toggle the embedded PDF preview"
	
	@verbose
	def activate(self, context):
		editor = context.active_editor
		if not type(editor) is LaTeXEditor:
			return

		if context.latex_previews == None:
			context.latex_previews = LaTeXPreviews(context)
		current_tab = context._window_decorator._window.get_active_tab()

		try:
			pdf_file_path = "%s.pdf" % editor.file.shortname
		except Exception, exc:
			# This happens when a .tex document has no master file.
			# Is it a bug ? Or should one catch this exception ?
			self._log.debug("Exception catched. %s" % exc)
			if context.latex_previews.is_shown(current_tab):
				context.latex_previews.hide(current_tab)
				self._log.debug("Closing the preview.")
			return

		context.latex_previews.toggle(current_tab, pdf_file_path)


class LaTeXPreviewZoomInAction(LaTeXAction):
	label = "Zoom In"
	stock_id = gtk.STOCK_ZOOM_IN
	accelerator = "<Alt><Super>P"
	tooltip = "Zoom the embedded preview in"

	def activate(self, context):
		editor = context.active_editor
		if not type(editor) is LaTeXEditor:
			return
		
		current_tab = context._window_decorator._window.get_active_tab()
		if context.latex_previews != None and context.latex_previews.is_shown(current_tab):
			context.latex_previews.zoom(current_tab, LaTeXPreviews.ZOOM_IN)


class LaTeXPreviewZoomOutAction(LaTeXAction):
	label = "Zoom Out"
	stock_id = gtk.STOCK_ZOOM_OUT
	accelerator = "<Alt><Super>M"
	tooltip = "Zoom the embedded preview out"

	def activate(self, context):
		editor = context.active_editor
		if not type(editor) is LaTeXEditor:
			return
			
		current_tab = context._window_decorator._window.get_active_tab()
		if context.latex_previews != None and context.latex_previews.is_shown(current_tab):
			context.latex_previews.zoom(current_tab, LaTeXPreviews.ZOOM_OUT)


class LaTeXPreviewScrollUpAction(LaTeXAction):
	label = "Scroll Up"
	stock_id = gtk.STOCK_GO_UP
	accelerator = "<Alt><Super>Up"
	tooltip = "Scroll the embedded preview up"

	def activate(self, context):
		editor = context.active_editor
		if not type(editor) is LaTeXEditor:
			return
			
		current_tab = context._window_decorator._window.get_active_tab()
		if context.latex_previews != None and context.latex_previews.is_shown(current_tab):
			context.latex_previews.scroll(current_tab, LaTeXPreviews.SCROLL_UP)


class LaTeXPreviewScrollDownAction(LaTeXAction):
	label = "Scroll Down"
	stock_id = gtk.STOCK_GO_DOWN
	accelerator = "<Alt><Super>Down"
	tooltip = "Scroll the embedded preview down"

	def activate(self, context):
		editor = context.active_editor
		if not type(editor) is LaTeXEditor:
			return
			
		current_tab = context._window_decorator._window.get_active_tab()
		if context.latex_previews != None and context.latex_previews.is_shown(current_tab):
			context.latex_previews.scroll(current_tab, LaTeXPreviews.SCROLL_DOWN)


class LaTeXPreviewScrollLeftAction(LaTeXAction):
	label = "Scroll Left"
	stock_id = gtk.STOCK_GO_BACK
	accelerator = "<Alt><Super>Left"
	tooltip = "Scroll the embedded preview to the left"

	def activate(self, context):
		editor = context.active_editor
		if not type(editor) is LaTeXEditor:
			return
			
		current_tab = context._window_decorator._window.get_active_tab()
		if context.latex_previews != None and context.latex_previews.is_shown(current_tab):
			context.latex_previews.scroll(current_tab, LaTeXPreviews.SCROLL_LEFT)


class LaTeXPreviewScrollRightAction(LaTeXAction):
	label = "Scroll Right"
	stock_id = gtk.STOCK_GO_FORWARD
	accelerator = "<Alt><Super>Right"
	tooltip = "Scroll the embedded preview to the right"

	def activate(self, context):
		editor = context.active_editor
		if not type(editor) is LaTeXEditor:
			return
			
		current_tab = context._window_decorator._window.get_active_tab()
		if context.latex_previews != None and context.latex_previews.is_shown(current_tab):
			context.latex_previews.scroll(current_tab, LaTeXPreviews.SCROLL_RIGHT)


class LaTeXSpellCheckAction(LaTeXAction):
	label = "Spell Check"
	stock_id = gtk.STOCK_SPELL_CHECK
	accelerator = "<Ctrl><Alt>S"
	tooltip = "Run LaTeX-aware spell check on the document"
	
	def activate(self, context):
		context.active_editor.spell_check()


class LaTeXFontFamilyAction(LaTeXIconAction):
	menu_tool_action = True
	
	label = "Font Family"
	accelerator = None
	tooltip = "Font Family"
	icon = File(find_resource("icons/bf.png"))
	
	def activate(self, context):
		pass


class LaTeXFontFamilyMenuAction(LaTeXAction):
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
	

class LaTeXEmphasizeAction(LaTeXTemplateAction):
	label = "Emphasize"
	tooltip = "Emphasize"
	icon_name = "it"
	template_source = "\\emph{$_}"
	
	
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


class LaTeXBlackboardBoldAction(LaTeXTemplateAction):
	label = "Blackboard Bold"
	tooltip = "Blackboard Bold"
	icon_name = "bb"
	packages = ["amsmath"]
	template_source = "\ensuremath{\mathbb{$_}}"
	
	
class LaTeXCaligraphyAction(LaTeXTemplateAction):
	label = "Caligraphy"
	tooltip = "Caligraphy"
	icon_name = "cal"
	template_source = "\ensuremath{\mathcal{$_}}"


class LaTeXFrakturAction(LaTeXTemplateAction):
	label = "Fraktur"
	tooltip = "Fraktur"
	icon_name = "frak"
	packages = ["amsmath"]
	template_source = "\ensuremath{\mathfrak{$_}}"


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
	

class LaTeXStructureAction(LaTeXIconAction):
	menu_tool_action = True
	
	label = "Structure"
	accelerator = None
	tooltip = "Structure"
	icon = File(find_resource("icons/section.png"))
	
	def activate(self, context):
		pass


class LaTeXStructureMenuAction(LaTeXAction):
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
	
	
class LaTeXGraphicsAction(LaTeXIconAction):
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


class LaTeXTableAction(LaTeXIconAction):
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
	
	
class LaTeXListingAction(LaTeXIconAction):
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


from ..tools import ToolRunner


class LaTeXBuildImageAction(LaTeXIconAction):
	label = "Build Image"
	accelerator = None
	tooltip = "Build an image from the LaTeX document"
	icon = File(find_resource("icons/build-image.png"))
	
	dialog = None
	
	def activate(self, context):
		if not self.dialog:
			from dialogs import BuildImageDialog
			self.dialog = BuildImageDialog()
			
		tool = self.dialog.run()
		if tool is not None:
			tool_view = context.find_view(None, "ToolView")
			
			if context.active_editor:
				ToolRunner().run(context.active_editor.file, tool, tool_view)

			
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
	

class LaTeXMathMenuAction(LaTeXAction):
	label = "Math"
	accelerator = None
	tooltip = "Math"
	stock_id = None
	
	def activate(self, context):
		pass


class LaTeXMathAction(LaTeXTemplateAction):
	menu_tool_action = True
	
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
	
	
class LaTeXSaveAsTemplateAction(LaTeXAction):
	label = "Save As Template..."
	accelerator = None
	tooltip = "Save the current document as a template"
	stock_id = gtk.STOCK_SAVE_AS
	
	def activate(self, context):
		from dialogs import SaveAsTemplateDialog
		
		dialog = SaveAsTemplateDialog()
		file = dialog.run()
		
		content = context.active_editor.content
		
		fo = open(file.path, "w")
		fo.write(content)
		fo.close
	
	
	
	
	
	
	
		
