# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2008 Michael Zeising
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
tools.util
"""

import os
import signal
import subprocess
import fcntl
import gobject


class Process(object):
	"""
	This runs a command in a child process
	"""
	
	# intervall of polling stdout of the child process
	_POLL_INTERVAL = 250
	
	
	def abort(self):
		"""
		Abort the running process
		"""
		if self._process:
			gobject.source_remove(self._id_exit)
			gobject.source_remove(self._id_stdout)
			gobject.source_remove(self._id_stderr)
			
			try:
				os.kill(self._process.pid, signal.SIGTERM)
				
				self._abort()
			except OSError, e:
				self._log.error("Failed to abort job: %s" % e)
	
	def run(self, command):
		# run child process
		self._process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
										stderr=subprocess.PIPE)
		
		# unblock pipes
		fcntl.fcntl(self._process.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
		fcntl.fcntl(self._process.stderr, fcntl.F_SETFL, os.O_NONBLOCK)
		
		# monitor process and pipes
		self._id_stdout = gobject.timeout_add(self._POLL_INTERVAL, self._on_stdout)
		self._id_stderr = gobject.timeout_add(self._POLL_INTERVAL, self._on_stderr)
		self._id_exit = gobject.child_watch_add(self._process.pid, self._on_exit)
			
	def _on_stdout(self):
		try:
			s = self._process.stdout.read()
			if len(s):
				self._stdout(s)
		except IOError:
			pass
		return True
	
	def _on_stderr(self):
		try:
			s = self._process.stderr.read()
			if len(s):
				self._stderr(s)
		except IOError:
			pass
		return True
	
	def _on_exit(self, pid, condition):
		gobject.source_remove(self._id_exit)
		gobject.source_remove(self._id_stdout)
		gobject.source_remove(self._id_stderr)
		
		# read remaining output
		self._on_stdout()
		self._on_stderr()
		
		self._exit(condition)
		
	def _stdout(self, text):
		"""
		To be overridden
		"""
		
	def _stderr(self, text):
		"""
		To be overridden
		"""
	
	def _abort(self):
		"""
		To be overridden
		"""
	
	def _exit(self, condition):
		"""
		To be overridden
		"""
		
		