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
issues
"""

from logging import getLogger


class IIssueHandler(object):
    """
    A class implementing this interface handles issues
    """

    def clear(self):
        """
        Remove all partitions and issues
        """
        raise NotImplementedError

    def issue(self, issue):
        """
        An issue has occured
        """
        raise NotImplementedError


class MockIssueHandler(IIssueHandler):
    """
    This is used by the BibTeXDocumentCache
    """
    __log = getLogger("MockIssueHandler")

    def clear(self):
        pass

    def issue(self, issue):
        self.__log.debug(str(issue))


class IStructuredIssueHandler(object):
    def clear(self):
        """
        Remove all partitions and issues
        """
        raise NotImplementedError

    def add_partition(self, label, state, parent_partition_id):
        """
        Add a new partition

        @param label: a label used in the UI
        @param state: the initial state descriptor for the partition
        @param parent_partition_id: the partition under which this one should be
                created (None for top-level)

        @return: a unique id for the partition
        """
        raise NotImplementedError

    def set_partition_state(self, partition_id, state):
        """
        @param partition_id: a partition id as returned by add_partition
        @param state: any string
        """
        raise NotImplementedError

    def set_abort_enabled(self, enabled, method):
        """
        @param enabled: if True a job may be aborted
        @param method: a method that is may be called to abort a running job
        """
        raise NotImplementedError

    def append_issues(self, partition_id, issues):
        """
        An issue occured

        @param issue: an Issue object
        @param partition: a partition id as returned by add_partition
        """
        raise NotImplementedError


class MockStructuredIssueHandler(IStructuredIssueHandler):
    """
    Used by the PreviewRenderer
    """
    def clear(self):
        pass

    def add_partition(self, label, state, parent_partition_id):
        pass

    def set_partition_state(self, partition_id, state):
        pass

    def append_issues(self, partition_id, issues):
        pass

    def set_abort_enabled(self, enabled, method):
        pass


class Issue(object):
    """
    An issue can be a warning, an error, an info or a task that occures or is
    recognized during parsing and validation of a source file
    """

    SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_INFO, SEVERITY_TASK = 1, 2, 3, 4

    POSITION_OFFSET, POSITION_LINE = 1, 2

    def __init__(self, message, start, end, file, severity, position_type=POSITION_OFFSET):
        """
        @param message: a str in Pango markup
        @param start: the start offset of the issue
        @param end: the end offset
        @param file: the File object representing the file the issue occured in
        @param severity: one of SEVERITY_*
        """
        self.message = message
        self.start = start
        self.end = end
        self.file = file
        self.severity = severity
        self.position_type = position_type

    def __str__(self):
        return "Issue{'%s', %s, %s, %s, %s}" % (self.message, self.start, self.end, self.file, self.severity)

# ex:ts=4:et:
