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

# ui definition

UI = """
    <ui>
        <menubar name="MenuBar">
            <menu name="FileMenu" action="File">
                <placeholder name="FileOps_1">
                    <menuitem action="LaTeXNewAction" />
                </placeholder>
                <placeholder name="FileOps_3">
                    <menuitem action="LaTeXSaveAsTemplateAction" />
                </placeholder>
            </menu>
            <placeholder name="ExtraMenu_1">
                <menu action="LaTeXMenuAction">
                    <menuitem action="LaTeXChooseMasterAction" />
                    <separator />
                    <menuitem action="LaTeXGraphicsAction" />
                    <menuitem action="LaTeXTableAction" />
                    <menuitem action="LaTeXListingAction" />
                    <menuitem action="LaTeXUseBibliographyAction" />
                    <separator />
                    <menuitem action="LaTeXCloseEnvironmentAction" />
                    <separator />
                    <menuitem action="LaTeXBuildImageAction" />
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
                    <menuitem action="LaTeXEmphasizeAction" />
                    <menuitem action="LaTeXUnderlineAction" />
                    <menuitem action="LaTeXSmallCapitalsAction" />
                    <menuitem action="LaTeXRomanAction" />
                    <menuitem action="LaTeXSansSerifAction" />
                    <menuitem action="LaTeXTypewriterAction" />
                    <separator />
                    <menuitem action="LaTeXBlackboardBoldAction" />
                    <menuitem action="LaTeXCaligraphyAction" />
                    <menuitem action="LaTeXFrakturAction" />
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
            <separator />
            <toolitem action="LaTeXBuildImageAction" />
        </toolbar>
    </ui>"""

# actions

from ..latex.actions import LaTeXMenuAction, LaTeXNewAction, LaTeXChooseMasterAction, \
        LaTeXItemizeAction, LaTeXEnumerateAction, LaTeXFontFamilyAction, LaTeXFontFamilyMenuAction, LaTeXBoldAction, \
        LaTeXItalicAction, LaTeXEmphasizeAction, LaTeXDescriptionAction, LaTeXStructureMenuAction, LaTeXPartAction, LaTeXChapterAction, \
        LaTeXSectionAction, LaTeXSubsectionAction, LaTeXParagraphAction,LaTeXSubparagraphAction, LaTeXStructureAction, \
        LaTeXGraphicsAction, LaTeXUseBibliographyAction, LaTeXTableAction, LaTeXListingAction, LaTeXJustifyLeftAction, \
        LaTeXJustifyCenterAction, LaTeXJustifyRightAction, LaTeXMathMenuAction, LaTeXMathAction, LaTeXDisplayMathAction, \
        LaTeXEquationAction, LaTeXUnEqnArrayAction, LaTeXEqnArrayAction, LaTeXUnderlineAction, LaTeXSmallCapitalsAction, \
        LaTeXRomanAction, LaTeXSansSerifAction, LaTeXTypewriterAction, LaTeXCloseEnvironmentAction, LaTeXBlackboardBoldAction, \
        LaTeXCaligraphyAction, LaTeXFrakturAction, LaTeXBuildImageAction, LaTeXSaveAsTemplateAction

from ..bibtex.actions import BibTeXMenuAction, BibTeXNewEntryAction

ACTIONS = [ LaTeXMenuAction, LaTeXNewAction, LaTeXChooseMasterAction,
        LaTeXItemizeAction, LaTeXEnumerateAction, LaTeXFontFamilyAction, LaTeXFontFamilyMenuAction, LaTeXBoldAction,
        LaTeXItalicAction, LaTeXEmphasizeAction, LaTeXDescriptionAction, LaTeXStructureMenuAction, LaTeXPartAction, LaTeXChapterAction,
        LaTeXSectionAction, LaTeXSubsectionAction, LaTeXParagraphAction,LaTeXSubparagraphAction, LaTeXStructureAction,
        LaTeXGraphicsAction, LaTeXUseBibliographyAction, LaTeXTableAction, LaTeXListingAction, LaTeXJustifyLeftAction,
        LaTeXJustifyCenterAction, LaTeXJustifyRightAction, LaTeXMathMenuAction, LaTeXMathAction, LaTeXDisplayMathAction,
        LaTeXEquationAction, LaTeXUnEqnArrayAction, LaTeXEqnArrayAction, LaTeXUnderlineAction, LaTeXSmallCapitalsAction,
        LaTeXRomanAction, LaTeXSansSerifAction, LaTeXTypewriterAction, LaTeXCloseEnvironmentAction, LaTeXBlackboardBoldAction,
        LaTeXCaligraphyAction, LaTeXFrakturAction, LaTeXBuildImageAction, LaTeXSaveAsTemplateAction,
        BibTeXMenuAction, BibTeXNewEntryAction ]

# views

from ..views import IssueView
from ..latex.views import LaTeXSymbolMapView, LaTeXOutlineView
from ..bibtex.views import BibTeXOutlineView


#WINDOW_SCOPE_VIEWS = { ".tex" : {"LaTeXSymbolMapView" : LaTeXSymbolMapView } }
#
#EDITOR_SCOPE_VIEWS = { ".tex" : {"IssueView" : IssueView,
#                                 "LaTeXOutlineView" : LaTeXOutlineView},
#
#                       ".bib" : {"IssueView" : IssueView,
#                                 "BibTeXOutlineView" : BibTeXOutlineView} }

from ..preferences import Preferences
LATEX_EXTENSIONS = Preferences().get("latex-extensions").split(",")
BIBTEX_EXTENSIONS = [".bib"]

WINDOW_SCOPE_VIEWS = {}
EDITOR_SCOPE_VIEWS = {}

for e in LATEX_EXTENSIONS:
    WINDOW_SCOPE_VIEWS[e] = {"LaTeXSymbolMapView" : LaTeXSymbolMapView }
    EDITOR_SCOPE_VIEWS[e] = {"IssueView" : IssueView, "LaTeXOutlineView" : LaTeXOutlineView}

for e in BIBTEX_EXTENSIONS:
    EDITOR_SCOPE_VIEWS[e] = {"IssueView" : IssueView, "BibTeXOutlineView" : BibTeXOutlineView}


# editors

from ..latex.editor import LaTeXEditor
from ..bibtex.editor import BibTeXEditor

EDITORS = [ LaTeXEditor, BibTeXEditor ]


# ex:ts=8:et:
