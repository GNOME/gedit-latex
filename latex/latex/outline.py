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
latex.outline
"""

from logging import getLogger

from .parser import Node
from ..issues import Issue


class OutlineNode(list):

    ROOT, STRUCTURE, LABEL, NEWCOMMAND, REFERENCE, GRAPHICS, PACKAGE, TABLE, NEWENVIRONMENT = list(range(9))

    def __init__(self, type, start=None, end=None, value=None, level=None, foreign=False, numOfArgs=None, file=None, **kwargs):
        """
        numOfArgs        only used for NEWCOMMAND type
        """
        self.type = type
        self.start = start
        self.end = end
        self.value = value
        self.level = level
        self.foreign = foreign
        self.numOfArgs = numOfArgs
        self.file = file

        self.oldcmd = kwargs.get("oldcmd")

    @property
    def xml(self):
        if self.type == self.ROOT:
            return "<root>%s</root>" % "".join([child.xml for child in self])
        elif self.type == self.STRUCTURE:
            return "<structure level=\"%s\" headline=\"%s\">%s</structure>" % (self.level, self.value,
                                                                                "".join([child.xml for child in self]))


class Outline(object):

    def __init__(self):
        self.rootNode = OutlineNode(OutlineNode.ROOT, level=0)
        self.labels = []            # OutlineNode objects
        self.bibliographies = []    # File objects
        self.colors = []
        self.packages = []           # OutlineNode objects
        self.newcommands = []        # OutlineNode objects
        self.newenvironments = []    # OutlineNode objects

        self.new_ref_commands = {}

    REF_CMDS = set(("ref","eqref","pageref"))
    def is_ref_command(self, cmd_name):
        return (cmd_name in self.REF_CMDS) or (cmd_name in self.new_ref_commands) 

from ..file import File
from ..preferences import Preferences


class LaTeXOutlineGenerator(object):

    _log = getLogger("LaTeXOutlineGenerator")

    # TODO: foreign flag is not necessary

    _STRUCTURE_LEVELS = { "part" : 1, "part*" : 1,
                          "chapter" : 2, "chapter*" : 2,
                          "section" : 3, "section*" : 3,
                          "subsection" : 4, "subsection*" : 4,
                          "subsubsection" : 5, "subsubsection*" : 5,
                          "paragraph" : 6,
                          "subparagraph" : 7 }

#    def __init__(self):
#        # TODO: read config
#        self.cfgLabelsInTree = True
#        self.cfgTablesInTree = True
#        self.cfgGraphicsInTree = True

    def generate(self, documentNode, issue_handler):
        """
        Generates an outline model from a document model and returns a list
        of list of issues if some occured.
        """

        # setup
        self.cfgLabelsInTree = Preferences().get("outline-show-labels")
        self.cfgTablesInTree = Preferences().get("outline-show-tables")
        self.cfgGraphicsInTree = Preferences().get("outline-show-graphics")

        self._outline = Outline()
        self._stack = [self._outline.rootNode]

        self._labelCache = {}

#        self._file = documentNode.value        # this is updated when a DOCUMENT occurs

        self._walk(documentNode, issue_handler)

        return self._outline

    def _walk(self, parentNode, issue_handler, foreign=False):
        """
        Recursively walk a node in the document model

        foreign        if True this node is a child of a reference node, so it's coming
                    from an expanded reference
        """

        childForeign = foreign

        for node in parentNode:
#            if node.type == Node.DOCUMENT:
#                self._file = node.value
            if node.type == Node.COMMAND:
                if node.value in list(self._STRUCTURE_LEVELS.keys()):
                    try:
                        headline = node.firstOfType(Node.MANDATORY_ARGUMENT).innerMarkup
                        level = self._STRUCTURE_LEVELS[node.value]
                        outlineNode = OutlineNode(OutlineNode.STRUCTURE, node.start, node.lastEnd, headline, level, foreign, file=node.file)

                        while self._stack[-1].level >= level:
                            self._stack.pop()

                        self._stack[-1].append(outlineNode)
                        self._stack.append(outlineNode)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed structure command", node.start, node.end, node.file, Issue.SEVERITY_ERROR))

                elif node.value == "label":
                    try:
                        value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText

                        if value in list(self._labelCache.keys()):
                            start, end = self._labelCache[value]
                            issue_handler.issue(Issue("Label <b>%s</b> has already been defined" % value, start, end, node.file, Issue.SEVERITY_ERROR))
                        else:
                            self._labelCache[value] = (node.start, node.lastEnd)

                            labelNode = OutlineNode(OutlineNode.LABEL, node.start, node.lastEnd, value, foreign=foreign, file=node.file)

                            self._outline.labels.append(labelNode)
                            if self.cfgLabelsInTree:
                                self._stack[-1].append(labelNode)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))

#                elif node.value == "begin":
#                    environment = str(node.filter(Node.MANDATORY_ARGUMENT)[0][0])
#                    if environment == "lstlisting":
#                        # look for label in listing environment
#                        try:
#                            # TODO: Node should have a method like toDict() or something
#                            optionNode = node.filter(Node.OPTIONAL_ARGUMENT)[0]
#                            option = "".join([str(child) for child in optionNode])
#                            for pair in option.split(","):
#                                key, value = pair.split("=")
#                                if key.strip() == "label":
#                                    labelNode = OutlineNode(OutlineNode.LABEL, node.start, node.end, value.strip())
#                                    outline.labels.append(labelNode)
#                                    if self.cfgLabelsInTree:
#                                        stack[-1].append(labelNode)
#                        except IndexError:
#                            pass

                elif node.value == "usepackage":
                    try:
                        package = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
                        packageNode = OutlineNode(OutlineNode.PACKAGE, node.start, node.lastEnd, package, file=node.file)
                        self._outline.packages.append(packageNode)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.end, node.file, Issue.SEVERITY_ERROR))

                elif self.cfgTablesInTree and node.value == "begin":
                    try:
                        environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
                        if environ == "tabular":
                            tableNode = OutlineNode(OutlineNode.TABLE, node.start, node.lastEnd, "", foreign=foreign, file=node.file)
                            self._stack[-1].append(tableNode)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))

                elif self.cfgGraphicsInTree and node.value == "includegraphics":
                    try:
                        target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
                        graphicsNode = OutlineNode(OutlineNode.GRAPHICS, node.start, node.lastEnd, target, foreign=foreign, file=node.file)
                        self._stack[-1].append(graphicsNode)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))

                elif node.value == "bibliography":
                    try:
                        value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
                        for bib in value.split(","):
                            self._outline.bibliographies.append(File("%s/%s.bib" % (node.file.dirname, bib)))
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))

                elif node.value == "definecolor" or node.value == "xdefinecolor":
                    try:
                        name = str(node.firstOfType(Node.MANDATORY_ARGUMENT)[0])
                        self._outline.colors.append(name)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))

                elif node.value == "newcommand":
                    try:
                        name = str(node.firstOfType(Node.MANDATORY_ARGUMENT)[0])[1:]    # remove "\"
                        try:
                            nArgs = int(node.filter(Node.OPTIONAL_ARGUMENT)[0].innerText)
                        except IndexError:
                            nArgs = 0
                        except Exception:
                            issue_handler.issue(Issue("Malformed newcommand", node.start, node.end, node.file, Issue.SEVERITY_ERROR))
                            nArgs = 0

                        #if the command has only one argument, be smart and see if it is a redefinition of an
                        #existing latex command
                        oldcmd = None
                        if nArgs == 1:
                            oldcommandnode = None
                            newcommandsnode = node.filter(Node.MANDATORY_ARGUMENT)[1]
                            #find the command that takes the '#1' argument
                            for i in newcommandsnode.filter(Node.COMMAND):
                                for j in i.filter(Node.MANDATORY_ARGUMENT):
                                    if j.innerText == "#1":
                                        oldcommandnode = i
                            if oldcommandnode:
                                oldcmd = i.value

                        ncNode = OutlineNode(OutlineNode.NEWCOMMAND, node.start, node.lastEnd, name, numOfArgs=nArgs, file=node.file, oldcmd=oldcmd)
                        self._outline.newcommands.append(ncNode)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))

                    # don't walk through \newcommand
                    continue

                elif node.value in ["newenvironment", "newtheorem"]:
                    try:
                        name = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
                        #try:
                        #    n_args = int(node.firstOfType(Node.OPTIONAL_ARGUMENT).innerText)
                        #except IndexError:
                        #    n_args = 0
                        ne_node = OutlineNode(OutlineNode.NEWENVIRONMENT, node.start, node.lastEnd, name, numOfArgs=0, file=node.file)
                        self._outline.newenvironments.append(ne_node)
                    except IndexError:
                        issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))

                elif node.value == "include" or node.value == "input":
                    childForeign = True

            self._walk(node, issue_handler, childForeign)


# ex:ts=4:et:
