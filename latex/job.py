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
base.job
"""

import dbus
import dbus.service
import dbus.glib
import multiprocessing
import logging


BUS_NAME = 'org.gedit.LaTeXPlugin.JobManager'
OBJECT_PATH = '/org/gedit/LaTeXPlugin/JobManager'


class Job(object):

    __log = logging.getLogger("Job")

    class NoneReturned(object):
        pass

    def __init__(self, argument=None):
        """
        @param arguments: a list of objects to be passed to the Job
        """
        self.__argument = argument
        self.__returned = self.NoneReturned()
        self.__change_listener = None

    def set_argument(self, argument):
        self.__argument = argument

    def schedule(self):
        """
        Run the Job as a subprocess
        """
        # create queue for communication
        self.__queue = multiprocessing.Queue()

        # run process
        self.__process = multiprocessing.Process(target=self.__start, args=(self.__queue,))

        # enqueue argument object
        self.__queue.put(self.__argument)

        # start process
        self.__process.start()

    def abort(self):
        """
        Abort the Job process
        """
        self.__process.terminate()

        # TODO: cleanup?

    def get_returned(self):
        """
        Get the objects returned by the Job
        """
        if type(self.__returned) is self.NoneReturned:
            # dequeue returned object
            self.__returned = self.__queue.get()
        return self.__returned

    def get_exception(self):
        return self.__exception

    @property
    def id(self):
        return id(self)

    def set_change_listener(self, job_change_listener):
        self.__change_listener = job_change_listener

    def __start(self, queue):
        """
        This is started as a subprocess in a separate address space
        """
        # register state change listener
        if not self.__change_listener is None:
            job_manager.add_listener(self.id, self.__change_listener)

        # notify state change
        job_manager.change_state(self.id, JobManager.STATE_STARTED)

        # dequeue argument object
        argument = queue.get()

        # run the job
        self.__exception = None
        try:
            returned = self._run(argument)
        except Exception as e:
            self.__log.error(e)
            self.__exception = e

        # enqueue returned object
        queue.put(returned)

        # notify state change
        job_manager.change_state(self.id, JobManager.STATE_COMPLETED)

        # deregister state change listener
        if not self.__change_listener is None:
            job_manager.remove_listener(self.id)

    def _run(self, arguments):
        """
        @return: a list of objects that should be made available after completion
        """
        pass


class JobChangeListener(object):
    """
    Callback oject for listening to the state changes of a Job
    """
    def _on_state_changed(self, state):
        pass


class GlobalJobChangeListener(object):
    """
    Callback oject for listening to the state changes of ALL Jobs
    """
    def _on_state_changed(self, job_id, state):
        pass


class JobManager(dbus.service.Object):

    STATE_STARTED, STATE_COMPLETED = 1, 2

    __log = logging.getLogger("JobManager")

    def __init__(self):
        bus_name = dbus.service.BusName(BUS_NAME, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, OBJECT_PATH)

        self.__global_listener = None
        self.__listeners = {}

        self.__log.debug("Created JobManager instance %s" % id(self))

    @dbus.service.method(dbus_interface="org.gedit.JobManagerInterface")
    def change_state(self, job_id, state):
        """
        The job with id <job_id> has changed its state to <state>
        """
        self.__log.debug("change_state(%s, %s)" % (job_id, state))

        # notify global listener
        if self.__global_listener is None:
            self.__log.warn("No global listener")
        else:
            self.__global_listener._on_state_changed(job_id, state)

        # notify listener if present
        try:
            self.__listeners[job_id]._on_state_changed(state)
        except KeyError:
            self.__log.warn("No listener for job %s" % job_id)

    def set_global_listener(self, global_job_change_listener):
        self.__global_listener = global_job_change_listener

    def add_listener(self, job_id, job_change_listener):
        self.__listeners[job_id] = job_change_listener

    def remove_listener(self, job_id):
        del self.__listeners[job_id]

    def dispose(self):
        """
        End life-cycle
        """
        self.__log.debug("dispose")


job_manager = JobManager()


# ex:ts=4:et:
