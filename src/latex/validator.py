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
latex.validator
"""

from logging import getLogger
from os.path import exists

from ..base import File
from ..issues import Issue
from ..util import escape
from parser import Node
from environment import Environment


class LaTeXValidator(object):
	"""
	This validates the following aspects by walking the document model 
	and using the outline:
	
	 * unused labels
	 * unclosed environments, also "\[" and "\]"
	"""
	
	_log = getLogger("LaTeXValidator")
	
	def __init__(self):
		self._environment = Environment()
	
	def validate(self, document_node, outline, issue_handler):
		"""
		Validate a LaTeX document
		
		@param document_node: the root node of the document tree
		@param outline: a LaTeX outline object
		@param issue_handler: an object implementing IIssueHandler
		"""
		
		self._log.debug("validate")
		
		#~ # TODO: this is dangerous, the outline object could be outdated		
		#~ self._outline = outline
		
		# prepare a map for checking labels
		self._labels = {}
		for label in outline.labels:
			self._labels[label.value] = [label, False]	
		
		self._environStack = []
		
		self._checkRefs = True
		
		self._run(document_node, issue_handler)
		
		# evaluate label map
		for label, used in self._labels.values():
			if not used:
				# FIXME: we need to know in which File the label was defined!
				issue_handler.issue(Issue("Label <b>%s</b> is never used" % escape(label.value), label.start, label.end, label.file, Issue.SEVERITY_WARNING))
		
	def _run(self, parentNode, issue_handler):
		"""
		Recursive method validation
		"""
		for node in parentNode:
			recurse = True
#			if node.type == Node.DOCUMENT:
#				
#				self._log.debug("DOCUMENT: %s" % node.value)
#				
#				# the document node contains the File object as value
#				self._file = node.value
				
			if node.type == Node.COMMAND:
				if node.value == "begin":
					try:
						# push environment on stack
						environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						self._environStack.append((environ, node.start, node.lastEnd))
					except IndexError:
						issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
						
				elif node.value == "end":
					try:
						# check environment
						environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						try:
							tEnviron, tStart, tEnd = self._environStack.pop()
							if tEnviron != environ:
								issue_handler.issue(Issue("Environment <b>%s</b> has to be ended before <b>%s</b>" % (escape(tEnviron), escape(environ)), node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
						except IndexError:
							issue_handler.issue(Issue("Environment <b>%s</b> has no beginning" % escape(environ), node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
					except IndexError:
						issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
						
				elif node.value == "[":
					# push eqn env on stack
					self._environStack.append(("[", node.start, node.end))
				
				elif node.value == "]":
					try:
						tEnviron, tStart, tEnd = self._environStack.pop()
						if tEnviron != "[":
							issue_handler.issue(Issue("Environment <b>%s</b> has to be ended before <b>]</b>" % escape(tEnviron), node.start, node.end, node.file, Issue.SEVERITY_ERROR))
					except IndexError:
						issue_handler.issue(Issue("Environment <b>%s</b> has no beginning" % escape(environ), node.start, node.end, node.file, Issue.SEVERITY_ERROR))
				
				elif node.value == "ref" or node.value == "eqref" or node.value == "pageref":
					# mark label as used
					try:
						label = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						try:
							self._labels[label][1] = True
						except KeyError:
							issue_handler.issue(Issue("Label <b>%s</b> has not been defined" % escape(label), node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
					except IndexError:
						issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
						
				elif self._checkRefs and (node.value == "includegraphics"):
					try:
						# check referenced image file
						target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						if len(target) > 0:
							if File.is_absolute(target):
								filename = target
							else:
								file = File.create_from_relative_path(target, node.file.dirname)
								filename = file.path
							
							# an image may be specified without the extension
							potential_extensions = ["", ".eps", ".pdf", ".jpg", ".jpeg", ".gif", ".png"]
							
							found = False
							for ext in potential_extensions:
								if exists(filename + ext):
									found = True
									break
							
							if not found:
								issue_handler.issue(Issue("Image <b>%s</b> could not be found" % escape(target), node.start, node.lastEnd, node.file, Issue.SEVERITY_WARNING))
						else:
							issue_handler.issue(Issue("No image file specified", node.start, node.lastEnd, node.file, Issue.SEVERITY_WARNING))
					except IndexError:
						issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
						
				elif self._checkRefs and (node.value == "include" or node.value == "input"):
					# check referenced tex file
					try:
						target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						if len(target) > 0:
							if File.is_absolute(target):
								filename = target
							else:
								file = File.create_from_relative_path(target, node.file.dirname)
								filename = file.path
							
							# an input may be specified without the extension
							potential_extensions = ["", ".tex"]
							
							found = False
							for ext in potential_extensions:
								if exists(filename + ext):
									found = True
									break
							
							if not found:
								issue_handler.issue(Issue("Document <b>%s</b> could not be found" % escape(filename), node.start, node.lastEnd, node.file, Issue.SEVERITY_WARNING))
					except IndexError:		# firstOfType failed
						# this happens on old-style syntax like "\input myfile"
						issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
								
				elif self._checkRefs and node.value == "bibliography":
					try:
						# check referenced BibTeX file(s)
						value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText							
						for target in value.split(","):
							if File.is_absolute(target):
								filename = target
							else:
								file = File.create_from_relative_path(target, node.file.dirname)
								filename = file.path
							
							# a bib file may be specified without the extension
							potential_extensions = ["", ".bib"]
							
							found = False
							for ext in potential_extensions:
								if exists(filename + ext):
									found = True
									break
							
							if not found:
								issue_handler.issue(Issue("Bibliography <b>%s</b> could not be found" % escape(filename), node.start, node.lastEnd, node.file, Issue.SEVERITY_WARNING))
					except IndexError:		# firstOfType failed
						issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
						
				elif node.value == "newcommand":
					# don't validate in newcommand definitions
					recurse = False
				
				elif node.value == "bibliographystyle":
					try:
						# check if style exists
						value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
						
						if not self._environment.file_exists("%s.bst" % value):
							issue_handler.issue(Issue("Bibliography style <b>%s</b> could not be found" % escape(value), node.start, node.lastEnd, node.file, Issue.SEVERITY_WARNING))
					except IndexError:
						issue_handler.issue(Issue("Malformed command", node.start, node.lastEnd, node.file, Issue.SEVERITY_ERROR))
						
			if recurse:
				self._run(node, issue_handler)
				
	#~ def __del__(self):
		#~ print "Properly destroyed %s" % self
				
				
