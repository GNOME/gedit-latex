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
latex.actions
"""
from gi.repository import Gtk

from logging import getLogger

from ..action import Action, IconAction
from ..preferences import Preferences
from ..issues import MockIssueHandler
from ..tools import ToolRunner
from ..gldefs import _
from .editor import LaTeXEditor
from .parser import LaTeXParser, Node
from .dialogs import UseBibliographyDialog, InsertGraphicsDialog, InsertTableDialog, \
                    InsertListingDialog, BuildImageDialog, \
                    NewDocumentDialog
from . import LaTeXSource

LOG = getLogger(__name__)

class LaTeXAction(Action):
    extensions = Preferences().get("latex-extensions").split(",")


class LaTeXIconAction(IconAction):
    extensions = Preferences().get("latex-extensions").split(",")


class LaTeXTemplateAction(LaTeXIconAction):
    """
    Utility base class for quickly defining Actions inserting a LaTeX snippet
    """
    accelerator = None
    snippet_source = None
    packages = []

    def activate(self, context):
        context.active_editor.insert(LaTeXSource(self.snippet_source, self.packages))


class LaTeXMenuAction(LaTeXAction):
    label = _("LaTeX")
    stock_id = None
    accelerator = None
    tooltip = None

    def activate(self, context):
        pass


class LaTeXNewAction(Action):
    label = _("New LaTeX Document…")
    stock_id = Gtk.STOCK_NEW
    accelerator = "<Ctrl><Alt>N"
    tooltip = _("Create a new LaTeX document")

    dialog = None

    def activate(self, context):
        if not self.dialog:
            self.dialog = NewDocumentDialog()

        # we may not open the empty file and insert a Temlate here
        # because WindowContext.activate_editor calls gedit.Window.create_tab_from_uri
        # which is async

        if self.dialog.run() == 1:
            file = self.dialog.file
            file.create(self.dialog.source)
            context.activate_editor(file)


class LaTeXChooseMasterAction(LaTeXAction):
    label = _("Choose Master Document…")
    stock_id = None
    accelerator = None
    tooltip = None

    def activate(self, context):
        editor = context.active_editor
        assert type(editor) is LaTeXEditor

        editor.choose_master_file()

class LaTeXCloseEnvironmentAction(LaTeXIconAction):
    label = _("Close Nearest Environment")
    accelerator = "<Ctrl><Alt>E"
    tooltip = _("Close the nearest TeX environment at left of the cursor")
    icon_name = "close_env"

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
                LOG.debug("No environment to close")
        except ValueError:
            LOG.info("Environments are malformed")

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
    label = _("Use Bibliography…")
    accelerator = None
    tooltip = _("Use Bibliography")
    icon_name = "bib"

    dialog = None

    def activate(self, context):
        if not self.dialog:
            self.dialog = UseBibliographyDialog()

        source = self.dialog.run_dialog(context.active_editor.edited_file)
        if source:
            editor = context.active_editor
            assert type(editor) is LaTeXEditor

            editor.insert_at_position(source + "\n\n", LaTeXEditor.POSITION_BIBLIOGRAPHY)


class LaTeXFontFamilyAction(LaTeXIconAction):
    menu_tool_action = True

    label = _("Font Family")
    accelerator = None
    tooltip = _("Font Family")
    icon_name = "bf"

    def activate(self, context):
        pass


class LaTeXFontFamilyMenuAction(LaTeXMenuAction):
    label = _("Font Family")
    tooltip = _("Font Family")


class LaTeXBoldAction(LaTeXTemplateAction):
    label = _("Bold")
    tooltip = _("Bold")
    icon_name = "bf"
    snippet_source = "\\textbf{$0}"


class LaTeXItalicAction(LaTeXTemplateAction):
    label = _("Italic")
    tooltip = _("Italic")
    icon_name = "it"
    snippet_source = "\\textit{$0}"


class LaTeXEmphasizeAction(LaTeXTemplateAction):
    label = _("Emphasize")
    tooltip = _("Emphasize")
    icon_name = "it"
    snippet_source = "\\emph{$0}"


class LaTeXUnderlineAction(LaTeXTemplateAction):
    label = _("Underline")
    tooltip = _("Underline")
    icon_name = "underline"
    snippet_source = "\\underline{$0}"


class LaTeXSmallCapitalsAction(LaTeXTemplateAction):
    label = _("Small Capitals")
    tooltip = _("Small Capitals")
    icon_name = "sc"
    snippet_source = "\\textsc{$0}"


class LaTeXRomanAction(LaTeXTemplateAction):
    label = _("Roman")
    tooltip = _("Roman")
    icon_name = "rm"
    snippet_source = "\\textrm{$0}"


class LaTeXSansSerifAction(LaTeXTemplateAction):
    label = _("Sans Serif")
    tooltip = _("Sans Serif")
    icon_name = "sf"
    snippet_source = "\\textsf{$0}"


class LaTeXTypewriterAction(LaTeXTemplateAction):
    label = _("Typewriter")
    tooltip = _("Typewriter")
    icon_name = "tt"
    snippet_source = "\\texttt{$0}"


class LaTeXBlackboardBoldAction(LaTeXTemplateAction):
    label = _("Blackboard Bold")
    tooltip = _("Blackboard Bold")
    icon_name = "bb"
    packages = ["amsmath"]
    snippet_source = "\ensuremath{\mathbb{$0}}"


class LaTeXCaligraphyAction(LaTeXTemplateAction):
    label = _("Calligraphy")
    tooltip = _("Calligraphy")
    icon_name = "cal"
    snippet_source = "\ensuremath{\mathcal{$0}}"


class LaTeXFrakturAction(LaTeXTemplateAction):
    label = _("Fraktur")
    tooltip = _("Fraktur")
    icon_name = "frak"
    packages = ["amsmath"]
    snippet_source = "\ensuremath{\mathfrak{$0}}"


class LaTeXListMenuAction(LaTeXMenuAction):
    label = _("List")
    tooltip = _("List")


class LaTeXItemizeAction(LaTeXTemplateAction):
    label = _("Itemize")
    tooltip = _("Itemize")
    icon_name = "itemize"
    snippet_source = "\\begin{itemize}\n\t\\item $0\n\\end{itemize}"


class LaTeXListActionDefault(LaTeXItemizeAction):
    menu_tool_action = True
    label = _("List")
    tooltip = _("List")


class LaTeXEnumerateAction(LaTeXTemplateAction):
    label = _("Enumerate")
    tooltip = _("Enumerate")
    icon_name = "enumerate"
    snippet_source = "\\begin{enumerate}\n\t\\item $0\n\\end{enumerate}"


class LaTeXDescriptionAction(LaTeXTemplateAction):
    label = _("Description")
    tooltip = _("Description")
    icon_name = "description"
    snippet_source = "\\begin{description}\n\t\\item[$0]\n\\end{description}"

class LaTeXStructureMenuAction(LaTeXMenuAction):
    label = _("Structure")
    tooltip = _("Structure")

class LaTeXPartAction(LaTeXTemplateAction):
    label = _("Part")
    tooltip = _("Part")
    icon_name = "part"
    snippet_source = "\\part{$0}"


class LaTeXChapterAction(LaTeXTemplateAction):
    label = _("Chapter")
    tooltip = _("Chapter")
    icon_name = "chapter"
    snippet_source = "\\chapter{$0}"


class LaTeXSectionAction(LaTeXTemplateAction):
    label = _("Section")
    tooltip = _("Section")
    icon_name = "section"
    snippet_source = "\\section{$0}"


class LaTeXStructureActionDefault(LaTeXSectionAction):
    menu_tool_action = True
    label = _("Structure")
    tooltip = _("Structure")


class LaTeXSubsectionAction(LaTeXTemplateAction):
    label = _("Subsection")
    tooltip = _("Subsection")
    icon_name = "subsection"
    snippet_source = "\\subsection{$0}"


class LaTeXParagraphAction(LaTeXTemplateAction):
    label = _("Paragraph")
    tooltip = _("Paragraph")
    icon_name = "paragraph"
    snippet_source = "\\paragraph{$0}"


class LaTeXSubparagraphAction(LaTeXTemplateAction):
    label = _("Subparagraph")
    tooltip = _("Subparagraph")
    icon_name = "paragraph"
    snippet_source = "\\subparagraph{$0}"


class LaTeXGraphicsAction(LaTeXIconAction):
    label = _("Insert Graphics")
    accelerator = None
    tooltip = _("Insert Graphics")
    icon_name = "graphics"

    dialog = None

    def activate(self, context):
        if not self.dialog:
            self.dialog = InsertGraphicsDialog()
        source = self.dialog.run(context.active_editor.edited_file)
        if source:
            context.active_editor.insert(source)


class LaTeXTableAction(LaTeXIconAction):
    label = _("Insert Table or Matrix")
    accelerator = None
    tooltip = _("Insert Table or Matrix")
    icon_name = "table"

    dialog = None

    def activate(self, context):
        if not self.dialog:
            self.dialog = InsertTableDialog()
        source = self.dialog.run()
        if source:
            context.active_editor.insert(source)


class LaTeXListingAction(LaTeXIconAction):
    label = _("Insert Source Code Listing")
    accelerator = None
    tooltip = _("Insert Source Code Listing")
    icon_name = "listing"

    dialog = None

    def activate(self, context):
        if not self.dialog:
            self.dialog = InsertListingDialog()
        source = self.dialog.run(context.active_editor.edited_file)
        if source:
            context.active_editor.insert(source)

class LaTeXBuildAction(LaTeXIconAction):
    menu_tool_action = True

    label = _("Build")
    accelerator = None
    tooltip = _("Build")
    stock_id = Gtk.STOCK_CONVERT

    def activate(self, context):
        pass


class LaTeXBuildMenuAction(LaTeXMenuAction):
    label = _("Build")
    tooltip = _("Build")


class LaTeXBuildImageAction(LaTeXIconAction):
    label = _("Build Image")
    accelerator = None
    tooltip = _("Build an image from the LaTeX document")
    icon_name = "build-image"

    dialog = None

    def activate(self, context):
        if not self.dialog:
            self.dialog = BuildImageDialog()

        tool = self.dialog.run()
        if tool is not None:
            tool_view = context.find_view(None, "ToolView")

            if context.active_editor:
                ToolRunner().run(context.active_editor.file, tool, tool_view)


class LaTeXJustifyMenuAction(LaTeXMenuAction):
    label = _("Justify")
    tooltip = _("Justify")


class LaTeXJustifyLeftAction(LaTeXTemplateAction):
    label = _("Justify Left")
    tooltip = _("Justify Left")
    icon_name = "justify-left"
    snippet_source = "\\begin{flushleft}$0\\end{flushleft}"


class LaTeXJustifyCenterAction(LaTeXTemplateAction):
    label = _("Justify Center")
    tooltip = _("Justify Center")
    icon_name = "justify-center"
    snippet_source = "\\begin{center}$0\\end{center}"


class LaTeXJustifyActionDefault(LaTeXJustifyCenterAction):
    menu_tool_action = True
    label = _("Justify")
    tooltip = _("Justify")


class LaTeXJustifyRightAction(LaTeXTemplateAction):
    label = _("Justify Right")
    tooltip = _("Justify Right")
    icon_name = "justify-right"
    snippet_source = "\\begin{flushright}$0\\end{flushright}"


class LaTeXMathMenuAction(LaTeXMenuAction):
    label = _("Math")
    tooltip = _("Math")


class LaTeXMathAction(LaTeXTemplateAction):
    label = _("Mathematical Environment")
    tooltip = _("Mathematical Environment")
    icon_name = "math"
    snippet_source = "$ $0 $"


class LaTeXMathActionDefault(LaTeXMathAction):
    menu_tool_action = True
    label = _("Math")
    tooltip = _("Math")


class LaTeXDisplayMathAction(LaTeXTemplateAction):
    label = _("Centered Formula")
    tooltip = _("Centered Formula")
    icon_name = "displaymath"
    snippet_source = "\\[ $0 \\]"


class LaTeXEquationAction(LaTeXTemplateAction):
    label = _("Numbered Equation")
    tooltip = _("Numbered Equation")
    icon_name = "equation"
    snippet_source = """\\begin{equation}
    $0
\\end{equation}"""


class LaTeXUnEqnArrayAction(LaTeXTemplateAction):
    label = _("Array of Equations")
    tooltip = _("Array of Equations")
    icon_name = "uneqnarray"
    packages = ["amsmath"]
    snippet_source = """\\begin{align*}
    $0
\\end{align*}"""


class LaTeXEqnArrayAction(LaTeXTemplateAction):
    label = _("Numbered Array of Equations")
    tooltip = _("Numbered Array of Equations")
    icon_name = "eqnarray"
    packages = ["amsmath"]
    snippet_source = """\\begin{align}
    $0
\\end{align}"""

class FileDummyAction(Action):
    label = tooltip = stock_id = ''
    accelerator = None
    extensions = []

class ToolsDummyAction(Action):
    label = tooltip = stock_id = ''
    accelerator = None
    extensions = []

# ex:ts=4:et:
