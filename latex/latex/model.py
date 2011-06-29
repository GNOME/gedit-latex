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

from logging import getLogger

from ..base.resources import Resources


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


class LanguageModel(object):
    """
    """

    __log = getLogger("LanguageModel")

    def __init__(self):
        self.commands = {}            # maps command names to Command elements

        self.__placeholders = {}
        self.__newcommands = []

        self.__log.debug("init")

    def find_command(self, prefix):
        """
        Find a command by a prefix. A prefix like 'be' would return the command '\begin'
        """
        return [command for name, command in self.commands.iteritems() if name.startswith(prefix)]

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
            #self.__log.debug("fill_placeholder: name=%s, child_elements=%s" % (name, child_elements))

            for placeholder in self.__placeholders[name]:
                placeholder.children = child_elements
        except KeyError:
            self.__log.error("fill_placeholder: placeholder '%s' not registered" % name)

    def set_newcommands(self, newcommands):

        # TODO: use sets

        self.__log.debug("set_newcommands: " + ",".join([c.name for c in newcommands]))

        for name in self.__newcommands:
            self.commands.__delitem__(name)

        for command in newcommands:
            self.commands[command.name] = command


from xml import sax


class LanguageModelParser(sax.ContentHandler):
    """
    SAX parser for the language model in latex.xml
    """

    # TODO: this should be a simple state machine

    __log = getLogger("LanguageModelParser")

    def parse(self, filename, language_model):
        self.__language_model = language_model

        self.__command = None
        self.__argument = None

        self.__log.debug("Parsing %s" % filename)

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


from copy import deepcopy
import pickle

from ..base import File


class LanguageModelFactory(object):
    """
    This singleton creates LanguageModel instances.

    If a serialized ('pickled') LanguageModel object exists, then a copy
    of this object is returned. Otherwise the XML file must be parsed.
    """

    __log = getLogger("LanguageModelFactory")

    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        if not '_ready' in dir(self):

            pickled_object = self.__find_pickled_object()

            if pickled_object:
                self.__language_model = pickled_object
            else:
                pkl_filename = Resources().get_user_file("latex.pkl")
                xml_filename = Resources().get_data_file("latex.xml")

                self.__language_model = LanguageModel()
                parser = LanguageModelParser()
                parser.parse(xml_filename, self.__language_model)

                pickle.dump(self.__language_model, open(pkl_filename, 'w'))

            self._ready = True

    def __find_pickled_object(self):
        pkl_file = File(Resources().get_user_file("latex.pkl"))
        xml_file = File(Resources().get_data_file("latex.xml"))

        if pkl_file.exists:
            if xml_file.mtime > pkl_file.mtime:
                self.__log.debug("Pickled object and XML file have different modification times")
            else:
                try:
                    self.__log.debug("Pickled object found: %s" % pkl_file.path)
                    return pickle.load(open(pkl_file.path))
                except:
                    return None
        else:
            self.__log.debug("No pickled object found")
        return None

    def create_language_model(self):
        """
        Return a new LanguageModel
        """
        return deepcopy(self.__language_model)

# ex:ts=4:et:
