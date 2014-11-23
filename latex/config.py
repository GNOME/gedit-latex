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
base.config
"""

# actions
from .latex.actions import LaTeXMenuAction, LaTeXNewAction, LaTeXChooseMasterAction, \
        LaTeXListMenuAction, LaTeXListActionDefault, \
        LaTeXItemizeAction, LaTeXEnumerateAction, LaTeXFontFamilyAction, LaTeXFontFamilyMenuAction, LaTeXBoldAction, \
        LaTeXItalicAction, LaTeXEmphasizeAction, LaTeXDescriptionAction, LaTeXStructureMenuAction, LaTeXPartAction, LaTeXChapterAction, \
        LaTeXSectionAction, LaTeXSubsectionAction, LaTeXParagraphAction, LaTeXSubparagraphAction, LaTeXStructureActionDefault, \
        LaTeXGraphicsAction, LaTeXUseBibliographyAction, LaTeXTableAction, LaTeXListingAction, LaTeXJustifyLeftAction, \
        LaTeXJustifyMenuAction, LaTeXJustifyActionDefault, \
        LaTeXJustifyCenterAction, LaTeXJustifyRightAction, LaTeXMathMenuAction, LaTeXMathActionDefault, LaTeXMathAction, LaTeXDisplayMathAction, \
        LaTeXEquationAction, LaTeXUnEqnArrayAction, LaTeXEqnArrayAction, LaTeXUnderlineAction, LaTeXSmallCapitalsAction, \
        LaTeXRomanAction, LaTeXSansSerifAction, LaTeXTypewriterAction, LaTeXCloseEnvironmentAction, LaTeXBlackboardBoldAction, \
        LaTeXCaligraphyAction, LaTeXFrakturAction, LaTeXBuildImageAction, \
        LaTeXBuildAction, LaTeXBuildMenuAction, FileDummyAction, ToolsDummyAction

from .bibtex.actions import BibTeXMenuAction, BibTeXNewEntryAction

ACTIONS = [LaTeXMenuAction, LaTeXNewAction, LaTeXChooseMasterAction,
        LaTeXListMenuAction, LaTeXListActionDefault,
        LaTeXItemizeAction, LaTeXEnumerateAction, LaTeXFontFamilyAction, LaTeXFontFamilyMenuAction, LaTeXBoldAction,
        LaTeXItalicAction, LaTeXEmphasizeAction, LaTeXDescriptionAction, LaTeXStructureMenuAction, LaTeXPartAction, LaTeXChapterAction,
        LaTeXSectionAction, LaTeXSubsectionAction, LaTeXParagraphAction, LaTeXSubparagraphAction, LaTeXStructureActionDefault,
        LaTeXGraphicsAction, LaTeXUseBibliographyAction, LaTeXTableAction, LaTeXListingAction, LaTeXJustifyLeftAction,
        LaTeXJustifyMenuAction, LaTeXJustifyActionDefault,
        LaTeXJustifyCenterAction, LaTeXJustifyRightAction, LaTeXMathMenuAction, LaTeXMathActionDefault, LaTeXMathAction, LaTeXDisplayMathAction,
        LaTeXEquationAction, LaTeXUnEqnArrayAction, LaTeXEqnArrayAction, LaTeXUnderlineAction, LaTeXSmallCapitalsAction,
        LaTeXRomanAction, LaTeXSansSerifAction, LaTeXTypewriterAction, LaTeXCloseEnvironmentAction, LaTeXBlackboardBoldAction,
        LaTeXCaligraphyAction, LaTeXFrakturAction, LaTeXBuildImageAction,
        LaTeXBuildAction, LaTeXBuildMenuAction,
        BibTeXMenuAction, BibTeXNewEntryAction,
        FileDummyAction, ToolsDummyAction]

MENUACTIONS = [LaTeXNewAction, LaTeXChooseMasterAction, LaTeXCloseEnvironmentAction, BibTeXNewEntryAction] 

# views
from .views import IssueView
from .latex.views import LaTeXSymbolMapView, LaTeXOutlineView
from .bibtex.views import BibTeXOutlineView
from .tools.views import ToolView

from .preferences import Preferences
LATEX_EXTENSIONS = Preferences().get("latex-extensions").split(",")
BIBTEX_EXTENSIONS = [".bib"]

EDITOR_VIEWS = {}

for e in LATEX_EXTENSIONS:
    EDITOR_VIEWS[e] = {"ToolView": ToolView, "IssueView": IssueView, "LaTeXOutlineView": LaTeXOutlineView, "LaTeXSymbolMapView": LaTeXSymbolMapView}

for e in BIBTEX_EXTENSIONS:
    EDITOR_VIEWS[e] = {"ToolView": ToolView, "IssueView": IssueView, "BibTeXOutlineView": BibTeXOutlineView}


# editors
from .latex.editor import LaTeXEditor
from .bibtex.editor import BibTeXEditor

EDITORS = [LaTeXEditor, BibTeXEditor]


# ex:ts=4:et:
