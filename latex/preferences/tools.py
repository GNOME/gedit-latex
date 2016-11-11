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

import logging
import uuid
from xml.etree import ElementTree
import os

from gi.repository import GObject

from ..resources import Resources
from ..tools import Tool, Job
from ..tools.postprocess import GenericPostProcessor, RubberPostProcessor, LaTeXPostProcessor
from ..util import singleton, open_error

LOG = logging.getLogger(__name__)

def str_to_bool(x):
    """
    Converts a string to a boolean value
    """
    if type(x) is bool:
        return x
    elif type(x) is str or type(x) is str:
        try:
            return {"false" : False, "0" : False, "true" : True, "1" : True}[x.strip().lower()]
        except KeyError:
            LOG.error("str_to_bool: unsupported value %s" % x)
    else:
        LOG.error("str_to_bool: unsupported type %s" % type(x))

@singleton
class ToolPreferences(GObject.GObject):

    __gsignals__ = {
        "tools-changed": (
            GObject.SignalFlags.RUN_LAST, None, []),
    }

    # maps names to classes
    POST_PROCESSORS = {"GenericPostProcessor" : GenericPostProcessor,
                       "LaTeXPostProcessor" : LaTeXPostProcessor,
                       "RubberPostProcessor" : RubberPostProcessor}

    def __init__(self):
        GObject.GObject.__init__(self)
        self.__tool_objects = None
        self.__tool_ids = None
        self.__tools_changed = False

        filename = Resources().get_user_file("tools.xml")
        try:
            self.__tools = ElementTree.parse(filename).getroot()
            LOG.debug("Found %s" % filename)
        except (ElementTree.ParseError, FileNotFoundError) as exc:
            if isinstance(exc, ElementTree.ParseError):
                i = 0
                while True:
                    destname = "%s.%d" % (filename, i)
                    if not os.path.exists(destname):
                        break
                    i += 1
                os.rename(filename, destname)
                open_error(_("The file “%s” is corrupted and cannot be "
                            "parsed. It was moved to “%s”, and the Latex "
                            "Plugin will now fallback to the default tools.")
                            % (filename, destname))

            filename = Resources().get_data_file("tools.xml")

        self.__tools = ElementTree.parse(filename).getroot()
        LOG.debug("ToolPreferences constructed")

    def __notify_tools_changed(self):
        self.emit("tools-changed")

    @property
    def tools(self):
        """
        Return all Tools
        """
        self.__tool_ids = {}

        tools = []

        for tool_element in self.__tools.findall("tool"):
            jobs = []
            for job_element in tool_element.findall("job"):
                command = '' if job_element.text is None else job_element.text.strip()
                jobs.append(Job(command, str_to_bool(job_element.get("mustSucceed")), self.POST_PROCESSORS[job_element.get("postProcessor")]))

            assert not tool_element.get("extensions") is None

            extensions = tool_element.get("extensions").split()
            accelerator = tool_element.get("accelerator")
            id = tool_element.get("id")
            tool = Tool(tool_element.get("label"), jobs, tool_element.get("description"), accelerator, extensions)
            self.__tool_ids[tool] = id

            tools.append(tool)

        return tools

    def __find_tool_element(self, id):
        """
        Find the tool element with the given id
        """
        for element in self.__tools.findall("tool"):
            if element.get("id") == id:
                return element
        LOG.warning("<tool id='%s'> not found" % id)
        return None

    def save_or_update_tool(self, tool):
        """
        Save or update the XML subtree for the given Tool

        @param tool: a Tool object
        """
        tool_element = None
        if tool in self.__tool_ids:
            # find tool tag
            LOG.debug("Tool element found, updating...")

            id = self.__tool_ids[tool]
            tool_element = self.__find_tool_element(id)
        else:
            # create new tool tag
            LOG.debug("Creating new Tool...")

            id = str(uuid.uuid4())
            self.__tool_ids[tool] = id

            tool_element = ElementTree.SubElement(self.__tools, "tool")
            tool_element.set("id", id)
        
        tool_element.set("label", tool.label)
        tool_element.set("description", tool.description)
        tool_element.set("extensions", " ".join(tool.extensions))
        if tool.accelerator is None:
            if "accelerator" in list(tool_element.attrib.keys()):
                del tool_element.attrib["accelerator"]
        else:
            tool_element.set("accelerator", tool.accelerator)

        # remove all jobs
        for job_element in tool_element.findall("job"):
            tool_element.remove(job_element)

        # append new jobs
        for job in tool.jobs:
            job_element = ElementTree.SubElement(tool_element, "job")
            job_element.set("mustSucceed", str(job.must_succeed))
            job_element.set("postProcessor", job.post_processor.name)
            job_element.text = job.command_template

        self.__tools_changed = True
        self.__notify_tools_changed()

    def swap_tools(self, tool_1, tool_2):
        """
        Swap the order of two Tools
        """
        # grab their ids
        id_1 = self.__tool_ids[tool_1]
        id_2 = self.__tool_ids[tool_2]

        if id_1 == id_2:
            LOG.warning("Two tools have the same id. Please modify tools.xml to have unique id's.")
            return

        LOG.debug("Tool IDs are {%s: %s, %s, %s}" % (tool_1.label, id_1, tool_2.label, id_2))

        tool_element_1 = None
        tool_element_2 = None

        # find the XML elements and current indexes of the tools
        i = 0
        for tool_element in self.__tools:
            if tool_element.get("id") == id_1:
                tool_element_1 = tool_element
                index_1 = i
            elif tool_element.get("id") == id_2:
                tool_element_2 = tool_element
                index_2 = i

            if not (tool_element_1 is None or tool_element_2 is None):
                break

            i += 1

        LOG.debug("Found XML elements, indexes are {%s: %s, %s, %s}" % (tool_1.label, index_1, tool_2.label, index_2))

        # successively replace each of them by the other in the XML model
        self.__tools.remove(tool_element_1)
        self.__tools.insert(index_1, tool_element_2)

        LOG.debug("Replaced first tool by second in list")

        self.__tools.remove(tool_element_2)
        self.__tools.insert(index_2, tool_element_1)

        LOG.debug("Replaced second tool by first in list")

        # notify changes
        self.__tools_changed = True
        self.__notify_tools_changed()

    def delete_tool(self, tool):
        """
        Delete the given Tool

        @param tool: a Tool object
        """
        try:
            id = self.__tool_ids[tool]
            tool_element = self.__find_tool_element(id)
            self.__tools.remove(tool_element)

            del self.__tool_ids[tool]

            self.__tools_changed = True
        except KeyError as e:
            LOG.error("delete_tool: %s" % e)

        self.__notify_tools_changed()

    def save(self):
        """
        Save the preferences to XML
        """
        if self.__tools_changed:
            LOG.debug("Saving tools...")

            tree = ElementTree.ElementTree(self.__tools)
            tree.write(Resources().get_user_file("tools.xml"), encoding="utf-8")

            self.__tools_changed = False


# ex:ts=4:et:
