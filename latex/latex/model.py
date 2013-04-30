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
latex.model

The LaTeX language model used for code completion.
"""

import copy
import logging

from ..resources import Resources

LOG = logging.getLogger(__name__)

class Element(object):
    """
    """
    TYPE_COMMAND, TYPE_MANDATORY_ARGUMENT, TYPE_OPTIONAL_ARGUMENT, TYPE_CHOICE, TYPE_PLACEHOLDER = 1, 2, 3, 4, 5

    def __init__(self, package, type):
        """
        @param package: the name of the LaTeX package providing this Element
        @param type: one of TYPE_*
        """
        self.package = package
        self.type = type
        self._children = []

    @property
    def children(self):
        return self._children

    def append_child(self, child):
        self._children.append(child)


class Command(Element):
    def __init__(self, package, name):
        Element.__init__(self, package, Element.TYPE_COMMAND)
        self.name = name

    @property
    def first_mandatory_argument(self):
        for node in self.children:
            if node.type == Element.TYPE_MANDATORY_ARGUMENT:
                return node
        raise IndexError

    @property
    def first_optional_argument(self):
        for node in self.children:
            if node.type == Element.TYPE_OPTIONAL_ARGUMENT:
                return node
        raise IndexError


class Argument(Element):
    def get_children(self):
        """
        Override the children property of Element to be able to evaluate Placeholders
        allowed as children of Arguments
        """
        children = []

        for node in self._children:
            if node.type == Element.TYPE_PLACEHOLDER:
                children.extend(node.children)
            else:
                children.append(node)
        return children

    def set_children(self, children):
        self._children = children

    children = property(get_children, set_children)


class MandatoryArgument(Argument):
    def __init__(self, package, label):
        Argument.__init__(self, package, Element.TYPE_MANDATORY_ARGUMENT)
        self.label = label


class OptionalArgument(Argument):
    def __init__(self, package, label):
        Argument.__init__(self, package, Element.TYPE_OPTIONAL_ARGUMENT)
        self.label = label


class Choice(Element):
    def __init__(self, package, value, details=None):
        Element.__init__(self, package, Element.TYPE_CHOICE)
        self.value = value
        self.details = details


class Placeholder(Element):
    def __init__(self, name):
        Element.__init__(self, None, Element.TYPE_PLACEHOLDER)
        self.name = name

    def get_children(self):
        return self._children

    def set_children(self, children):
        self._children = children

    children = property(get_children, set_children)


#LanguageModel is pickled to save startup time...
#using pickle is dangerous. If you add or change the instance members of this class
#that need to persis through pickle, then INCREMENT THE VERSION
LANGUAGE_MODEL_VERSION = 1

class LanguageModel(object):
    """
    """

    REF_CMDS = set(("ref","eqref","pageref"))

    def __init__(self):
        self.commands = {}            # maps command names to Command elements
        self.VERSION = LANGUAGE_MODEL_VERSION

        self.__placeholders = {}
        self.__newcommands = []

        #some latex specific helpers.
        self.__new_ref_commands = {}

    def find_command(self, prefix):
        """
        Find a command by a prefix. A prefix like 'be' would return the command '\begin'
        """
        return [command for name, command in self.commands.items() if name.startswith(prefix)]

    def register_placeholder(self, placeholder):
        """
        Register a placeholder under its name. There may be multiple
        placeholder nodes for one name.
        """
        try:
            nodes = self.__placeholders[placeholder.name]
            nodes.append(placeholder)
        except KeyError:
            self.__placeholders[placeholder.name] = [placeholder]

    def fill_placeholder(self, name, child_elements):
        """
        Attach child elements to a placeholder
        """
        try:
            for placeholder in self.__placeholders[name]:
                placeholder.children = child_elements
        except KeyError:
            LOG.info("fill_placeholder: placeholder '%s' not registered" % name)

    def is_ref_command(self, cmd_name):
        return (cmd_name in self.REF_CMDS) or (cmd_name in self.__new_ref_commands) 

    def set_newcommands(self, outlinenodes):
        LOG.debug("set newcommands")

        #remove old state
        self.__new_ref_commands = {}
        for name in self.__newcommands:
            del(self.commands[name])
        self.__newcommands = []

        for o in outlinenodes:
            #if this is a redefinition of an existing node then use that node as
            #the completion helper
            if o.oldcmd and o.oldcmd in self.commands:
                LOG.info("Detected redefined \\newcommand: %s -> %s" % (o.value, o.oldcmd))
                #copy the old command so we retain its argument completion but change
                #the display name
                old = copy.copy(self.commands[o.oldcmd])
                old.name = o.value

                self.commands[o.value] = old
                self.__newcommands.append(o.value)

                if o.oldcmd in self.REF_CMDS:
                    self.__new_ref_commands[o.value] = 1

            else:
                #add a generic completer
                command = Command(None, o.value)
                for i in range(o.numOfArgs):
                    command.children.append(MandatoryArgument(None, "#%s" % (i + 1)))

                self.commands[command.name] = command
                self.__newcommands.append(command.name)

from xml import sax

class LanguageModelParser(sax.ContentHandler):
    """
    SAX parser for the language model in latex.xml
    """

    # TODO: this should be a simple state machine

    def parse(self, filename, language_model):
        self.__language_model = language_model

        self.__command = None
        self.__argument = None

        LOG.debug("parsing %s" % filename)

        sax.parse(filename, self)

    def startElement(self, name, attrs):
        try:
            package = attrs["package"]
        except KeyError:
            package = None

        if name == "command":
            name = attrs["name"]
            self.__command = Command(package, name)
            self.__language_model.commands[name] = self.__command

        elif name == "argument":
            try:
                label = attrs["label"]
            except KeyError:
                label = ""

            try:
                if attrs["type"] == "optional":
                    self.__argument = OptionalArgument(package, label)
                else:
                    self.__argument = MandatoryArgument(package, label)
            except KeyError:
                self.__argument = MandatoryArgument(package, label)

            self.__command.children.append(self.__argument)

        elif name == "choice":
            choice = Choice(package, attrs["name"])
            self.__argument.append_child(choice)

        elif name == "placeholder":
            placeholder = Placeholder(attrs["key"])
            self.__argument.append_child(placeholder)
            self.__language_model.register_placeholder(placeholder)


import pickle

from ..file import File


class LanguageModelFactory(object):
    """
    This singleton creates LanguageModel instances.

    If a serialized ('pickled') LanguageModel object exists, then a copy
    of this object is returned. Otherwise the XML file must be parsed.
    """

    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        if not '_ready' in dir(self):

            pickled_object = self.__find_pickled_object()

            if pickled_object:
                LOG.debug("language model: pickled object loaded")
                self.language_model = pickled_object
            else:
                LOG.debug("language model: no pickled object loaded")
                pkl_filename = Resources().get_user_file("latex.pkl")
                xml_filename = Resources().get_data_file("latex.xml")

                self.language_model = LanguageModel()
                parser = LanguageModelParser()
                parser.parse(xml_filename, self.language_model)

                pickle.dump(self.language_model, open(pkl_filename, 'wb'))
                LOG.info("Pickling language model")

            self._ready = True

    def __find_pickled_object(self):
        pkl_file = File(Resources().get_user_file("latex.pkl"))
        xml_file = File(Resources().get_data_file("latex.xml"))

        if pkl_file.exists:
            if xml_file.mtime > pkl_file.mtime:
                LOG.debug("Pickled object and XML file have different modification times")
            else:
                try:
                    obj = pickle.load(open(pkl_file.path, "rb"))
                    if obj.VERSION == LANGUAGE_MODEL_VERSION:
                        return obj
                    else:
                        LOG.info("Language model obsolete")
                except:
                    LOG.info("Invalid language model", exc_info=True)

        return None

    def get_language_model(self):
        return self.language_model

# ex:ts=4:et:
