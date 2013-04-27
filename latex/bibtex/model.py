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
bibtex.model

The model of BibTeX read from an XML file.
"""
import xml.etree.ElementTree as ElementTree

from ..resources import Resources


class Type(object):
    def __init__(self, name):
        self.name = name
        self.required_fields = []
        self.optional_fields = []

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class Field(object):
    def __init__(self, name, label):
        self.name = name
        self.label = label


class BibTeXModel(object):
    def __new__(cls):
        if not '_instance' in cls.__dict__:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        if not '_ready' in dir(self):
            # init object
            self._fields = {}
            self._types = {}

            # parse bibtex.xml
            self._bibtex = ElementTree.parse(Resources().get_data_file("bibtex.xml")).getroot()

            for field_e in self._bibtex.findall("fields/field"):
                id = field_e.get("id")
                self._fields[id] = Field(id, field_e.get("_label"))

            for type_e in self._bibtex.findall("types/type"):
                id = type_e.get("id")
                type = Type(id)

                for required_field_e in type_e.findall("required/field"):
                    field_id = required_field_e.get("id")
                    type.required_fields.append(self._fields[field_id])

                for optional_field_e in type_e.findall("optional/field"):
                    field_id = optional_field_e.get("id")
                    type.optional_fields.append(self._fields[field_id])

                self._types[id.lower()] = type

            self._types_list = None
            self._ready = True

    def find_type(self, name):
        """
        Find an entry type by its name
        """
        return self._types[name.lower()]

    @property
    def types(self):
        """
        List all entry types in sorted order
        """
        if self._types_list is None:
            self._types_list = list(self._types.values())
            self._types_list.sort()
        return self._types_list


# ex:ts=4:et:
