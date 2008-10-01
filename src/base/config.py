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

from ..latex.actions import LaTeXMenuAction, LaTeXNewAction, LaTeXCommentAction, LaTeXSpellCheckAction, LaTeXChooseMasterAction


# TODO: extensions and UI path should be asked from Action objects (build UI like for tool actions)


ACTION_OBJECTS = { "LaTeXMenuAction" : LaTeXMenuAction(), 
				   "LaTeXNewAction" : LaTeXNewAction(),
				   "LaTeXCommentAction" : LaTeXCommentAction(),
				   "LaTeXSpellCheckAction" : LaTeXSpellCheckAction(),
				   "LaTeXChooseMasterAction" : LaTeXChooseMasterAction() }

ACTION_EXTENSIONS = { None : ["LaTeXNewAction"],
					  ".tex" : ["LaTeXMenuAction", "LaTeXCommentAction", "LaTeXSpellCheckAction", "LaTeXChooseMasterAction"] }

from ..tools import Tool, Job
from ..tools.postprocess import GenericPostProcessor, RubberPostProcessor


# TODO: this should come from configuration

TOOLS = [ Tool("LaTeX → PDF", [".tex"], [Job("rubber --inplace --maxerr -1 --pdf --short --force --warn all \"$filename\"", True, RubberPostProcessor), Job("gnome-open $shortname.pdf", True, GenericPostProcessor)], "Create a PDF from LaTeX source"),
		  Tool("Cleanup LaTeX Build", [".tex"], [Job("rm -f $directory/*.aux $directory/*.log", True, GenericPostProcessor)], "Remove LaTeX build files") ]


from ..latex.views import LaTeXSymbolMapView, LaTeXIssueView, LaTeXOutlineView


WINDOW_SCOPE_VIEWS = { ".tex" : {"LaTeXSymbolMapView" : LaTeXSymbolMapView } }

EDITOR_SCOPE_VIEWS = { ".tex" : {"LaTeXIssueView" : LaTeXIssueView, 
								 "LaTeXOutlineView" : LaTeXOutlineView} }

from ..latex.editor import LaTeXEditor


EDITORS = {".tex" : LaTeXEditor}
