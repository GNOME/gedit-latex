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
latex.completion

LaTeX-specific completion classes
"""

from logging import getLogger
from gi.repository import GdkPixbuf

from ..resources import Resources
from ..completion import ICompletionHandler, Proposal


class LaTeXCommandProposal(Proposal):
    """
    A proposal inserting a Template when activated
    """

    def __init__(self, overlap, snippet, label):
        self._snippet = snippet
        self._label = label
        self._overlap = overlap
        self._icon = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("i_command.png"))

    @property
    def source(self):
        return self._snippet

    @property
    def label(self):
        return self._label

    @property
    def details(self):
        return None

    @property
    def icon(self):
        return self._icon

    @property
    def overlap(self):
        return self._overlap


class LaTeXChoiceProposal(Proposal):
    """
    A proposal inserting a simple string when activated
    """

    def __init__(self, overlap, source, label, details):
        self._source = source
        self._details = details
        self._overlap = overlap
        self._label = label
        self._icon = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("i_choice.png"))

    @property
    def source(self):
        return self._source

    @property
    def label(self):
        return self._label

    @property
    def details(self):
        return self._details

    @property
    def icon(self):
        return self._icon

    @property
    def overlap(self):
        return self._overlap


from .model import LanguageModelFactory, Choice, MandatoryArgument, OptionalArgument
from .parser import PrefixParser, Node

from ..bibtex.cache import BibTeXDocumentCache


class LaTeXCompletionHandler(ICompletionHandler):
    """
    This implements the LaTeX-specific code completion
    """
    _log = getLogger("LaTeXCompletionHandler")

    trigger_keys = ["backslash", "braceleft"]
    prefix_delimiters = ["\\"]

    def __init__(self):
        self._log.debug("init")
        #get the language_model singleton
        self._language_model = LanguageModelFactory().get_language_model()
        self._bibtex_document_cache = BibTeXDocumentCache()

    def set_outline(self, outline):
        """
        Process a LaTeX outline model

        @param outline: a latex.outline.Outline instance
        """

        # labels
        label_choices = [Choice(None, label.value) for label in outline.labels]
        self._language_model.fill_placeholder("Labels", label_choices)

        # colors
        color_choices = [Choice(None, color) for color in outline.colors]
        self._language_model.fill_placeholder("Colors", color_choices)

        # newcommands
        self._language_model.set_newcommands(outline.newcommands)

        # newenvironments
        newenvironments = []
        for n in outline.newenvironments:
            choice = Choice(None, n.value)
            newenvironments.append(choice)
        self._language_model.fill_placeholder("Newenvironments", newenvironments)

        #
        # bibtex entries
        #
        try:

            entry_choices = []

            for bib_file in outline.bibliographies:
                try:
                    bibtex_document = self._bibtex_document_cache.get_document(bib_file)

                    # generate choices from entries

                    for entry in bibtex_document.entries:

                        # build table data for DetailsPopup
                        rows = []
                        for field in entry.fields:
                            rows.append([field.name, field.valueMarkup])

                        entry_choices.append(Choice(None, entry.key, rows))

                except OSError:
                    # BibTeX file not found
                    self._log.error("Not found: %s" % bib_file)

            # attach to placeholders in CommandStore
            self._language_model.fill_placeholder("Bibitems", entry_choices)

        except IOError:
            self._log.debug("Failed to provide BibTeX completion due to IOError")


    def set_neighbors(self, tex_files, bib_files, graphic_files):
        """
        Populate the lists of neighbor files

        @param tex_files: list of neighbor TeX files
        @param bib_files: list of neighbor BibTeX files
        @param graphic_files: list of neighbor graphics
        """
        tex_choices = [Choice(None, file.shortbasename) for file in tex_files]
        self._language_model.fill_placeholder("TexFiles", tex_choices)

        bib_choices = [Choice(None, file.shortbasename) for file in bib_files]
        self._language_model.fill_placeholder("BibFiles", bib_choices)

        graphic_choices = [Choice(None, file.basename) for file in graphic_files]
        self._language_model.fill_placeholder("ImageFiles", graphic_choices)

    def complete(self, prefix):
        """
        Try to complete a given prefix
        """
        self._log.debug("complete: '%s'" % prefix)

        #proposals = [LaTeXTemplateProposal(Template("Hello[${One}][${Two}][${Three}]"), "Hello[Some]"), LaTeXProposal("\\world")]

        fragment = Node(Node.DOCUMENT)
        parser = PrefixParser()

        try:
            parser.parse(prefix, fragment)

            modelParser = PrefixModelParser(self._language_model)
            proposals = modelParser.parse(fragment)

            self._log.debug("Generated %s proposals" % len(proposals))

            return proposals

        except Exception as e:
            self._log.debug(e)

        return []


from ..preferences import Preferences
from . import LaTeXSource


class PrefixModelParser(object):
    """
    This parses the document model of a prefix and generates proposals accordingly

    This is used by the LaTeXCompletionHandler class
    """

    _log = getLogger("PrefixModelParser")

    def __init__(self, language_model):
        self.__language_model = language_model
        self.__light_foreground = Preferences().get("light-foreground-color")

    def __create_proposals_from_commands(self, commands, overlap):
        """
        Generate proposals for commands
        """
        proposals = []

        for command in commands:
            label = command.name
            snippet = "\\" + command.name

            for idx, argument in enumerate(command.children):
                if type(argument) is MandatoryArgument:
                    label += "{<span color='%s'>%s</span>}" % (self.__light_foreground, argument.label)
                    snippet += "{${%s:%s}}" % (idx+1, argument.label)
                elif type(argument) is OptionalArgument:
                    label += "[<span color='%s'>%s</span>]" % (self.__light_foreground, argument.label)
                    snippet += "[${%s:%s}]" % (idx+1, argument.label)

            if command.package:
                label += " <small><b>%s</b></small>" % command.package

            # workaround for latex.model.Element.package may be None
            # TODO: latex.model.Element.package should be a list of packages
            if command.package is None:
                packages = []
            else:
                packages = [command.package]
            proposal = LaTeXCommandProposal(overlap, LaTeXSource(snippet, packages), label)
            proposals.append(proposal)

        return proposals

    def __create_proposals_from_choices(self, choices, overlap):
        """
        Generate proposals for argument choices
        """
        proposals = []

        for choice in choices:
            label = choice.value
            if choice.package:
                label += " <small><b>%s</b></small>" % choice.package

            # see above
            if choice.package is None:
                packages = []
            else:
                packages = [choice.package]
            proposal = LaTeXChoiceProposal(overlap, LaTeXSource(choice.value, packages), label, choice.details)
            proposals.append(proposal)

        return proposals

    def parse(self, prefixFragment):
        """
        Returns choices
        """

        # root node of the prefix model must be COMMAND
        commandNode = prefixFragment[-1]
        if commandNode.type != Node.COMMAND:
            return []

        commandName = commandNode.value

        if len(commandNode) == 0:
            # command has no arguments...

            if len(commandName) == 0:
                # no name, so propose all commands
                commands = list(self.__language_model.commands.values())
                overlap = 1        # only "\"
            else:
                commands = self.__language_model.find_command(commandName)

                if len(commands) == 1 and commands[0].name == commandName:
                    # don't propose when only one command is found and that one
                    # matches the typed one
                    return []

                overlap = len(commandName) + 1         # "\begi"

            return self.__create_proposals_from_commands(commands, overlap)

        # ...command has arguments

        try:
            self._log.debug(commandNode.xml)

            # find the language model of the command
            storedCommand = self.__language_model.commands[commandName]


            try:
                argumentNode, storedArgument = self.__match_argument(commandNode, storedCommand)
            except Exception as e:
                self._log.error(e)
                return []


            choices = storedArgument.children

            # filter argument matching the already typed argument text

            argumentValue = argumentNode.innerText

            if len(argumentValue):
                choices = [choice for choice in choices if choice.value.startswith(argumentValue)]
                overlap = len(argumentValue)
            else:
                overlap = 0
            return self.__create_proposals_from_choices(choices, overlap)

        except KeyError:
            self._log.debug("Command not found: %s" % commandName)
            return []

    def __match_argument(self, command, model_command):
        """
        @param command: the parsed command Node
        @param model_command: the according model command
        @return: (matched argument, model argument)
        """
        # push the arguments of the model command on a stack
        model_argument_stack = []
        model_argument_stack.extend(model_command.children)
        model_argument_stack.reverse()

        for argument in command:
            if argument.type == Node.MANDATORY_ARGUMENT:

                # optional arguments in the model may be skipped
                while True:
                    try:
                        model_argument = model_argument_stack.pop()
                        if model_argument.type != Node.OPTIONAL_ARGUMENT:
                            break
                    except IndexError:
                        # no more optional arguments to skip - signatures can't match
                        raise Exception("Signatures don't match")

                if not argument.closed:
                    return (argument, model_argument)

            elif argument.type == Node.OPTIONAL_ARGUMENT:
                model_argument = model_argument_stack.pop()

                if model_argument.type != Node.OPTIONAL_ARGUMENT:
                    raise Exception("Signatures don't match")

                if not argument.closed:
                    return (argument, model_argument)

        raise Exception("No matching model argument found")


# ex:ts=4:et:
