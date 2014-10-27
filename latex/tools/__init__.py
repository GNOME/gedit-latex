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
tools

A tool is what we called a 'build profile' before. 'Tool' is more generic.
It can be used for cleaning up, converting files, for building PDFs etc.
"""

import logging

from gi.repository import Gtk, Gedit

from ..resources import Resources
from ..action import Action

LOG = logging.getLogger(__name__)

class Tool(object):
    """
    The model of a tool. This is to be stored in preferences.
    """
    def __init__(self, label, jobs, description, accelerator, extensions=[]):
        """
        @param label: a label used when displaying the Tool in the UI
        @param jobs: a list of Job objects
        @param description: a descriptive string used as tooltip
        @param accelerator: a key combination for activating this tool
        @param extensions: a list of file extensions for which this Tool can be used
        """
        self.label = label
        self.jobs = jobs
        self.description = description
        self.extensions = extensions
        self.accelerator = accelerator

    def __str__(self):
        return "Tool{%s}" % self.label


class Job(object):
    """
    A Job is one command to be executed in a Tool

    Command templates may contain the following placeholders:

     * $filename : the full filename of the processed file
     * $directory : the parent directory of the processed file
     * $shortname : the filename of the processed file without extension ('/dir/doc' for '/dir/doc.tex')
    """
    def __init__(self, command_template, must_succeed, post_processor):
        """
        Construct a Job

        @param command_template: a template string for the command to be executed
        @param must_succeed: if True this Job may cause the whole Tool to fail
        @param post_processor: a class implementing IPostProcessor
        """
        self._command_template = command_template
        self._must_succeed = must_succeed
        self._post_processor = post_processor

    @property
    def command_template(self):
        return self._command_template

    @property
    def must_succeed(self):
        return self._must_succeed

    @property
    def post_processor(self):
        return self._post_processor


class ToolAction(Action):
    """
    This hooks Tools in the UI. A ToolAction is instantiated for each registered Tool.
    """

    def __init__(self, tool):
        self._tool = tool
        self._runner = ToolRunner()

    @property
    def label(self):
        return self._tool.label

    @property
    def stock_id(self):
        return Gtk.STOCK_EXECUTE

    @property
    def accelerator(self):
        return None

    @property
    def tooltip(self):
        return self._tool.description

    def activate(self, context):
        LOG.debug("tool activate: %s" % self._tool)

        if context.active_editor:
            decorator = context._window_decorator
            doc = decorator.window.get_active_document()
            self.saving_id = doc.connect("saved",self.run_tool,context,doc)
            decorator.save_file()
        else:
            LOG.error("tool activate: no active editor")
            
    def run_tool(self, document, context, doc):
        tool_view = context.find_view(context.active_editor, "ToolView")

        self._runner.run(context.active_editor.file, self._tool, tool_view)
        LOG.debug("run tool on: %s" % context.active_editor.file)

        # destroy the save listener, or else we get a compile on any save
        doc.disconnect(self.saving_id)



from os import chdir
from .util import Process
from string import Template


class ToolRunner(Process):
    """
    This runs a Tool in a subprocess
    """

    def run(self, file, tool, issue_handler):
        """
        @param file: a File object
        @param tool: a Tool object
        @param issue_handler: an object implementing IStructuredIssueHandler
        """
        self._file = file
        self._stdout_text = ""
        self._stderr_text = ""
        self._job_iter = iter(tool.jobs)

        # add alert to the statusbar
        self._statusbar = Gedit.App.get_default().get_active_window().get_statusbar()
        self._msg_id = self._statusbar.push(1,'Compiling document ...')

        # init the IStructuredIssueHandler
        self._issue_handler = issue_handler
        self._issue_handler.clear()
        self._root_issue_partition = self._issue_handler.add_partition("<b>%s</b>" % tool.label, "running", None)
        self._issue_partitions = {}
        for job in tool.jobs:
            self._issue_partitions[job] = self._issue_handler.add_partition(job.command_template, "running", self._root_issue_partition)

        # change working directory to prevent issues with relative paths
        chdir(file.dirname)

        # enable abort
        self._issue_handler.set_abort_enabled(True, self.abort)

        # run
        self.__proceed()

    def __proceed(self):
        try:
            self._job = next(self._job_iter)

            command_template = Template(self._job.command_template)
            command = command_template.safe_substitute({"filename" : self._file.path,
                                                        "shortname" : self._file.shortname,
                                                        "directory" : self._file.dirname,
                                                        "plugin_path" : Resources().get_system_dir()})

            self._issue_handler.set_partition_state(self._issue_partitions[self._job], "running")

            self.execute(command)
        except StopIteration:
            # Tool finished successfully
            self._issue_handler.set_partition_state(self._root_issue_partition, "succeeded")
            # disable abort

            # FIXME: CRASHES
            # self._issue_handler.set_abort_enabled(False, None)

            self._on_tool_succeeded()

    def _on_stdout(self, text):
        """
        """
        LOG.debug("tool stdout: " + text)
        self._stdout_text += text

    def _on_stderr(self, text):
        """
        """
        LOG.debug("tool stderr: " + text)
        self._stderr_text += text

    def _on_abort(self):
        """
        """
        # disable abort
        self._issue_handler.set_abort_enabled(False, None)
        # mark Tool and all Jobs as aborted
        self._issue_handler.set_partition_state(self._root_issue_partition, "aborted")
        self._issue_handler.set_partition_state(self._issue_partitions[self._job], "aborted")
        for job in self._job_iter:
            self._issue_handler.set_partition_state(self._issue_partitions[job], "aborted")

    def _on_exit(self, condition):
        """
        """
        LOG.debug("tool exit")

        assert self._job

        # create post-processor instance
        post_processor = self._job.post_processor()

        # run post-processor
        post_processor.process(self._file, self._stdout_text, self._stderr_text, condition)

        # show issues
        self._issue_handler.append_issues(self._issue_partitions[self._job], post_processor.issues)

        # remove alert
        self._statusbar.remove(1,self._msg_id)

        if post_processor.successful:
            self._issue_handler.set_partition_state(self._issue_partitions[self._job], "succeeded")
            self.__proceed()
        else:
            self._issue_handler.set_partition_state(self._issue_partitions[self._job], "failed")
            if self._job.must_succeed:
                # whole Tool failed
                self._issue_handler.set_partition_state(self._root_issue_partition, "failed")
                # disable abort
                self._issue_handler.set_abort_enabled(False, None)

                self._on_tool_failed()
            else:
                self.__proceed()

    def _on_tool_succeeded(self):
        """
        The Tool has finished successfully

        To be overridden by subclass
        """

    def _on_tool_failed(self):
        """
        The Tool has failed

        To be overridden by subclass
        """

# ex:ts=4:et:
