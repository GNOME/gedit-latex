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
tools

A tool is what we called a 'build profile' before. 'Tool' is more generic.
It can be used for cleaning up, converting files, for building PDFs etc.
"""

from logging import getLogger


class Tool(object):
	"""
	The model of a tool. This is to be stored in preferences.
	"""
	def __init__(self, label, extensions, jobs, description):
		self._label = label
		self._extensions = extensions
		self._jobs = jobs
		self._description = description
	
	@property
	def label(self):
		"""
		A label used for this tool
		"""
		return self._label
	
	@property
	def description(self):
		"""
		A label used for this tool
		"""
		return self._description
	
	@property
	def extensions(self):
		"""
		The extensions this tool applies for (return None for every extension)
		"""
		return self._extensions
	
	@property
	def jobs(self):
		return self._jobs
	
	def __str__(self):
		return "Tool{%s}" % self._label
	
	
class Job(object):
	"""
	A Job forms one command to be executed in a Tool
	"""
	def __init__(self, command_template, must_succeed):
		self._command_template = command_template
		self._must_succeed = must_succeed
	
	@property
	def command_template(self):
		return self._command_template
	
	@property
	def must_succeed(self):
		return self._must_succeed


import gtk

from ..base import IAction

	
class ToolAction(IAction):
	"""
	This hooks Tools in the UI. A ToolAction is instantiated for each registered Tool.
	"""
	
	_log = getLogger("ToolAction")
	
	def init(self, tool):
		self._tool = tool
		self._tool_view = None
		
		self._runner = ToolRunner()
	
	@property
	def label(self):
		return self._tool.label
	
	@property
	def stock_id(self):
		return gtk.STOCK_CONVERT
	
	@property
	def accelerator(self):
		return None
	
	@property
	def tooltip(self):
		return self._tool.description
	
	def activate(self, context):
		self._log.debug("activate: " + str(self._tool))
		
		if not self._tool_view:
			self._tool_view = context.views["ToolView"]
		
		if context.active_editor:
			self._runner.run(context.active_editor.file, self._tool, self._tool_view)
			self._log.debug("activate: " + str(context.active_editor.file))
		

from util import Process
from string import Template


class ToolRunner(Process):
	"""
	This runs a Tool
	"""
	
	_log = getLogger("ToolProcessor")
	
	def run(self, file, tool, view):
		# init issue handler
		#self._issue_handler = structured_issue_handler
		#self._issue_handler.reset()
		#parent_id = self._issue_handler.add_section(tool.label)
		
		self._file = file
		self._job_iter = iter(tool.jobs)
		
		self._proceed()
	
	def _proceed(self):
		try:
			self._job = self._job_iter.next()
			
			command_template = Template(self._job.command_template)
			command = command_template.safe_substitute({"filename" : self._file.path, 
														"shortname" : self._file.shortname,
														"directory" : self._file.dirname})
			
			Process.run(self, command)
		except StopIteration:
			# finished
			return
	
	def _stdout(self, text):
		"""
		"""
		self._log.error("_stdout: " + text)
		
	def _stderr(self, text):
		"""
		"""
		self._log.debug("_stderr: " + text)
	
	def _abort(self):
		"""
		"""
		self._log.debug("_abort")
	
	def _exit(self, condition):
		"""
		"""
		self._log.debug("_exit")
		
		assert self._job
		
		if condition:
			if self._job.must_succeed:
				# tool failed
				pass
			else:
				self._proceed()
		else:
			self._proceed()
			


