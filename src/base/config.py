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
base.config
"""

UI = """
	<ui>
		<menubar name="MenuBar">
			<menu name="FileMenu" action="File">
				<placeholder name="FileOps_1">
					<menuitem action="LaTeXNewAction" />
				</placeholder>
			</menu>
			<placeholder name="ExtraMenu_1">
				<menu action="LaTeXMenuAction">
					<menuitem action="LaTeXChooseMasterAction" />
					<menuitem action="LaTeXCommentAction" />
					<menuitem action="LaTeXSpellCheckAction" />
					<separator />
					<menuitem action="LaTeXGraphicsAction" />
					<menuitem action="LaTeXTableAction" />
					<menuitem action="LaTeXListingAction" />
					<menuitem action="LaTeXUseBibliographyAction" />
				</menu>
				<menu action="BibTeXMenuAction">
					<menuitem action="BibTeXNewEntryAction" />
				</menu>
			</placeholder>
		</menubar>
		<toolbar name="LaTeXToolbar">
			<toolitem action="LaTeXFontFamilyAction">
				<menu action="LaTeXFontFamilyMenuAction">
					<menuitem action="LaTeXBoldAction" />
					<menuitem action="LaTeXItalicAction" />
				</menu>
			</toolitem>
			<toolitem action="LaTeXJustifyLeftAction" />
			<toolitem action="LaTeXJustifyCenterAction" />
			<toolitem action="LaTeXJustifyRightAction" />
			<separator />
			<toolitem action="LaTeXItemizeAction" />
			<toolitem action="LaTeXEnumerateAction" />
			<toolitem action="LaTeXDescriptionAction" />
			<separator />
			<toolitem action="LaTeXStructureAction">
				<menu action="LaTeXStructureMenuAction">
					<menuitem action="LaTeXPartAction" />
					<menuitem action="LaTeXChapterAction" />
					<separator />
					<menuitem action="LaTeXSectionAction" />
					<menuitem action="LaTeXSubsectionAction" />
					<menuitem action="LaTeXParagraphAction" />
					<menuitem action="LaTeXSubparagraphAction" />
				</menu>
			</toolitem>
			<separator />
			<toolitem action="LaTeXMathAction">
				<menu action="LaTeXMathMenuAction">
					<menuitem action="LaTeXMathAction" />
					<menuitem action="LaTeXDisplayMathAction" />
					<menuitem action="LaTeXEquationAction" />
					<menuitem action="LaTeXUnEqnArrayAction" />
					<menuitem action="LaTeXEqnArrayAction" />
				</menu>
			</toolitem>
			<separator />
			<toolitem action="LaTeXGraphicsAction" />
			<toolitem action="LaTeXTableAction" />
			<toolitem action="LaTeXListingAction" />
			<toolitem action="LaTeXUseBibliographyAction" />
		</toolbar>
	</ui>"""
		

from ..latex.actions import LaTeXMenuAction, LaTeXNewAction, LaTeXCommentAction, LaTeXSpellCheckAction, LaTeXChooseMasterAction, \
		LaTeXItemizeAction, LaTeXEnumerateAction, LaTeXFontFamilyAction, LaTeXFontFamilyMenuAction, LaTeXBoldAction, \
		LaTeXItalicAction, LaTeXDescriptionAction, LaTeXStructureMenuAction, LaTeXPartAction, LaTeXChapterAction, \
		LaTeXSectionAction, LaTeXSubsectionAction, LaTeXParagraphAction,LaTeXSubparagraphAction, LaTeXStructureAction, \
		LaTeXGraphicsAction, LaTeXUseBibliographyAction, LaTeXTableAction, LaTeXListingAction, LaTeXJustifyLeftAction, \
		LaTeXJustifyCenterAction, LaTeXJustifyRightAction, LaTeXMathMenuAction, LaTeXMathAction, LaTeXDisplayMathAction, \
		LaTeXEquationAction, LaTeXUnEqnArrayAction, LaTeXEqnArrayAction

from ..bibtex.actions import BibTeXMenuAction, BibTeXNewEntryAction


# TODO: extensions and UI path should be asked from Action objects (build UI like for tool actions)


ACTION_OBJECTS = { "LaTeXMenuAction" : LaTeXMenuAction(), 
				   "LaTeXNewAction" : LaTeXNewAction(),
				   "LaTeXCommentAction" : LaTeXCommentAction(),
				   "LaTeXSpellCheckAction" : LaTeXSpellCheckAction(),
				   "LaTeXChooseMasterAction" : LaTeXChooseMasterAction(),
				   "LaTeXItemizeAction" : LaTeXItemizeAction(),
				   "LaTeXEnumerateAction" : LaTeXEnumerateAction(),
				   "LaTeXFontFamilyAction" : LaTeXFontFamilyAction(),
				   "LaTeXFontFamilyMenuAction" : LaTeXFontFamilyMenuAction(),
				   "LaTeXBoldAction" : LaTeXBoldAction(),
				   "LaTeXItalicAction" : LaTeXItalicAction(),
				   "LaTeXDescriptionAction" : LaTeXDescriptionAction(),
				   "LaTeXStructureAction" : LaTeXStructureAction(),
				   "LaTeXStructureMenuAction" : LaTeXStructureMenuAction(),
				   "LaTeXPartAction" : LaTeXPartAction(),
				   "LaTeXChapterAction" : LaTeXChapterAction(),
				   "LaTeXSectionAction" : LaTeXSectionAction(),
				   "LaTeXSubsectionAction" : LaTeXSubsectionAction(),
				   "LaTeXParagraphAction" : LaTeXParagraphAction(),
				   "LaTeXSubparagraphAction" : LaTeXSubparagraphAction(),
				   "LaTeXGraphicsAction" : LaTeXGraphicsAction(),
				   "LaTeXUseBibliographyAction" : LaTeXUseBibliographyAction(),
				   "LaTeXTableAction" : LaTeXTableAction(),
				   "LaTeXListingAction" : LaTeXListingAction(),
				   "LaTeXJustifyLeftAction" : LaTeXJustifyLeftAction(),
				   "LaTeXJustifyCenterAction" : LaTeXJustifyCenterAction(),
				   "LaTeXJustifyRightAction" : LaTeXJustifyRightAction(),
				   "LaTeXMathMenuAction" : LaTeXMathMenuAction(),
				   "LaTeXMathAction" : LaTeXMathAction(),
				   "LaTeXDisplayMathAction" : LaTeXDisplayMathAction(),
				   "LaTeXEquationAction" : LaTeXEquationAction(),
				   "LaTeXUnEqnArrayAction" : LaTeXUnEqnArrayAction(),
				   "LaTeXEqnArrayAction" : LaTeXEqnArrayAction(),
				   "BibTeXMenuAction" : BibTeXMenuAction(),
				   "BibTeXNewEntryAction" : BibTeXNewEntryAction() }

ACTION_EXTENSIONS = { None : ["LaTeXNewAction"],
					  ".tex" : ["LaTeXMenuAction", 
								"LaTeXCommentAction", 
								"LaTeXSpellCheckAction", 
								"LaTeXChooseMasterAction",
								"LaTeXItemizeAction",
								"LaTeXEnumerateAction",
								"LaTeXFontFamilyAction",
								"LaTeXFontFamilyMenuAction",
								"LaTeXBoldAction",
								"LaTeXItalicAction",
								"LaTeXDescriptionAction",
								"LaTeXStructureAction",
								"LaTeXStructureMenuAction",
								"LaTeXPartAction",
								"LaTeXChapterAction",
								"LaTeXSectionAction",
								"LaTeXSubsectionAction",
								"LaTeXParagraphAction",
								"LaTeXSubparagraphAction",
								"LaTeXGraphicsAction",
								"LaTeXUseBibliographyAction",
								"LaTeXTableAction",
								"LaTeXListingAction",
								"LaTeXJustifyCenterAction",
								"LaTeXJustifyLeftAction",
								"LaTeXJustifyRightAction",
								"LaTeXMathMenuAction",
				   				"LaTeXMathAction",
				   				"LaTeXDisplayMathAction",
				   				"LaTeXEquationAction",
				   				"LaTeXUnEqnArrayAction",
				   				"LaTeXEqnArrayAction"],
				   		".bib" : ["BibTeXMenuAction", "BibTeXNewEntryAction"] }

#from ..tools import Tool, Job
#from ..tools.postprocess import GenericPostProcessor, RubberPostProcessor
#
#
#TOOLS = { ".tex" : [ Tool("LaTeX → PDF", [Job("rubber --inplace --maxerr -1 --pdf --short --force --warn all \"$filename\"", True, RubberPostProcessor), Job("gnome-open $shortname.pdf", True, GenericPostProcessor)], "Create a PDF from LaTeX source"),
#					 Tool("Cleanup LaTeX Build", [Job("rm -f $directory/*.aux $directory/*.log $directory/*.toc $directory/*.bbl $directory/*.blg", True, GenericPostProcessor)], "Remove LaTeX build files")] }


from ..views import IssueView
from ..latex.views import LaTeXSymbolMapView, LaTeXOutlineView
from ..bibtex.views import BibTeXOutlineView


WINDOW_SCOPE_VIEWS = { ".tex" : {"LaTeXSymbolMapView" : LaTeXSymbolMapView } }

EDITOR_SCOPE_VIEWS = { ".tex" : {"IssueView" : IssueView, 
								 "LaTeXOutlineView" : LaTeXOutlineView},
								 
					   ".bib" : {"IssueView" : IssueView, 
								 "BibTeXOutlineView" : BibTeXOutlineView} }

from ..latex.editor import LaTeXEditor
from ..bibtex.editor import BibTeXEditor


EDITORS = {".tex" : LaTeXEditor, ".bib" : BibTeXEditor}
