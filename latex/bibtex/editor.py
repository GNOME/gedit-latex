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
bibtex.editor
"""

BENCHMARK = True

import logging
if BENCHMARK: import time

from ..editor import Editor
from ..preferences import Preferences
from ..issues import Issue, IIssueHandler, MockIssueHandler
from ..util import verbose

from ..job import Job, JobChangeListener

from .parser import BibTeXParser
from .completion import BibTeXCompletionHandler
from .validator import BibTeXValidator

LOG = logging.getLogger(__name__)

class ParseJob(Job):
    def _run(self, arguments):
        file = arguments[0]
        content = arguments[1]
        self._parser = BibTeXParser()
        return self._parser.parse(content, file, MockIssueHandler())


class BibTeXEditor(Editor, IIssueHandler, JobChangeListener):

    extensions = [".bib"]

    @property
    def completion_handlers(self):
        self.__bibtex_completion_handler = BibTeXCompletionHandler()
        return [self.__bibtex_completion_handler]

    def __init__(self, tab_decorator, file):
        Editor.__init__(self, tab_decorator, file)
        self._parse_job = None

    def init(self, file, context):
        LOG.debug("init(%s)" % file)

        self._preferences = Preferences()

        self._file = file
        self._context = context

        style_scheme = self._text_buffer.get_style_scheme()
        w_style = style_scheme.get_style('def:warning')
        w_color = w_style.get_properties('background')[0]
        self.register_marker_type("bibtex-warning", w_color)

        e_style = style_scheme.get_style('def:error')
        e_color = e_style.get_properties('background')[0]
        self.register_marker_type("bibtex-error", e_color)

        self._issue_view = context.find_view(self, "IssueView")
        self._parser = BibTeXParser()
        self._validator = BibTeXValidator()
        self._outline_view = context.find_view(self, "BibTeXOutlineView")

        self._parse_job = ParseJob()
        self._parse_job.set_change_listener(self)

        # initially parse
        self.__parse()

    def on_save(self):
        """
        The file has been saved

        Update models
        """
        self.__parse()

#    def _on_state_changed(self, state):
#        #
#        # job.JobChangeListener._on_state_changed
#        #
#        if (state == JobManager.STATE_COMPLETED):
#            self._log.debug("Parser finished")
#
#            self._document = self._parse_job.get_returned()
#
#            #self._log.debug(str(self._document))
#
#            for entry in self._document.entries:
#                print entry.key
#
#            # FIXME: gedit crashes here with:
#            # gedit: Fatal IO error 11 (Resource temporarily unavailable) on X server :0.0.
#
#            self._log.debug("Validating...")
#            self._validator.validate(self._document, self._file, self)
#            self._log.debug("Validating finished")
#
#            self._outline_view.set_outline(self._document)
#
#
#    def __parse_async(self):
#
#        # reset highlight
#        self.remove_markers("bibtex-error")
#        self.remove_markers("bibtex-warning")
#
#        # reset issues
#        self._issue_view.clear()
#
#        self._log.debug("Starting parser job")
#
#        self._parse_job.set_argument([self._file, self.content])
#        self._parse_job.schedule()

    @verbose
    def __parse(self):
        """
        """
        LOG.debug("__parse")

        content = self.content

        # reset highlight
        self.remove_markers("bibtex-error")
        self.remove_markers("bibtex-warning")

        # reset issues
        self._issue_view.clear()

#        self.parse(self._file)

        if BENCHMARK:
            t = time.perf_counter()

        # parse document
        self._document = self._parser.parse(content, self._file, self)

        if BENCHMARK:
            LOG.info("BibTeXParser.parse: %f" % (time.perf_counter() - t))

        LOG.debug("Parsed %s bytes of content" % len(content))

        # validate
        if BENCHMARK:
            t = time.perf_counter()

        self._validator.validate(self._document, self._file, self)

        # 0.11
        if BENCHMARK:
            LOG.info("BibTeXValidator.validate: %f" % (time.perf_counter()
                                                       - t))

        self._outline_view.set_outline(self._document)

#    def _on_parser_finished(self, model):
#        """
#        """
#        self._document = model
#        self._outline_view.set_outline(self._document)

    def issue(self, issue):
        # overriding IIssueHandler.issue

        self._issue_view.append_issue(issue)

        if issue.file == self._file:
            if issue.severity == Issue.SEVERITY_ERROR:
                self.create_marker("bibtex-error", issue.start, issue.end)
            elif issue.severity == Issue.SEVERITY_WARNING:
                self.create_marker("bibtex-warning", issue.start, issue.end)

    def on_cursor_moved(self, offset):
        """
        The cursor has moved
        """
        if self._preferences.get("outline-connect-to-editor"):
            self._outline_view.select_path_by_offset(offset)

    def destroy(self):
        # unreference the window context
        del self._context

        # remove parse listener
        if self._parse_job != None:
            self._parse_job.set_change_listener(None)

        Editor.destroy(self)

# ex:ts=4:et:
