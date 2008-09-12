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
latex.validator
"""

class LaTeXValidator(object):
	"""
	This validates the following aspects by walking the document model 
	and using the outline:
	
	 * unused labels
	 * unclosed environments, also "\[" and "\]"
	"""
	
	def __init__(self):
		self._environment = Environment()
	
	def validate(self, documentNode, outline, baseDir=None):
		self._outline = outline
		
		# prepare structures
		
		self._labels = {}
		for label in outline.labels:
			self._labels[label.value] = [label, False]	
		
		self._issues = []
		self._envionStack = []
		
		self._checkRefs = bool(baseDir)
		self._baseDir = baseDir
		
		self._run(documentNode, documentNode.value)
		
		# evaluate structures
		
		for label, used in self._labels.values():
			if not used:
				self._issue_handler.issue(Issue("Label <b>%s</b> is never used" % label.value, Issue.VALIDATE_WARNING, 
												label.start, label.end, documentNode.value))
		
		return self._issues
		
	def _run(self, parentNode, filename):
		for node in parentNode:
			recurse = True
			if node.type == Node.DOCUMENT:
				filename = node.value
				
			elif node.type == Node.COMMAND:
				if node.value == "begin":
					# push environment on stack
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					self._envionStack.append((environ, node.start, node.lastEnd))
					
				elif node.value == "end":
					# check environment
					environ = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					try:
						tEnviron, tStart, tEnd = self._envionStack.pop()
						if tEnviron != environ:
							self._issue_handler.issue(Issue("Environment <b>%s</b> has to be ended before <b>%s</b>" % (tEnviron, environ), 
													Issue.VALIDATE_ERROR, node.start, node.lastEnd, filename))
					except IndexError:
						self._issue_handler.issue(Issue("Environment <b>%s</b> has no beginning" % environ, Issue.VALIDATE_ERROR, 
												node.start, node.lastEnd, filename))
				
				elif node.value == "[":
					# push eqn env on stack
					self._envionStack.append(("[", node.start, node.end))
				
				elif node.value == "]":
					try:
						tEnviron, tStart, tEnd = self._envionStack.pop()
						if tEnviron != "[":
							self._issue_handler.issue(Issue("Environment <b>%s</b> has to be ended before <b>]</b>" % tEnviron, 
													Issue.VALIDATE_ERROR, node.start, node.end, filename))
					except IndexError:
						self._issue_handler.issue(Issue("Environment <b>%s</b> has no beginning" % environ, Issue.VALIDATE_ERROR, 
												node.start, node.end, filename))
				
				elif node.value == "ref" or node.value == "eqref" or node.value == "pageref":
					# mark label as used
					label = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					try:
						self._labels[label][1] = True
					except KeyError:
						self._issue_handler.issue(Issue("Label <b>%s</b> has not been defined" % label, Issue.VALIDATE_ERROR, 
												node.start, node.lastEnd, filename))
				
				elif self._checkRefs and (node.value == "includegraphics"):
					# check referenced image file
					target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					if target[0] == "/":
						filename = target
					else:
						filename = "%s/%s" % (self._baseDir, target)
					
					if not exists(filename):
						self._issue_handler.issue(Issue("Image <b>%s</b> could not be found" % target, Issue.VALIDATE_WARNING, 
												node.start, node.lastEnd, filename))
				
				elif self._checkRefs and (node.value == "include" or node.value == "input"):
					# check referenced tex file
					target = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					if len(target):
						if target[0] == "/":
							filename = "%s.tex" % target
						else:
							filename = "%s/%s.tex" % (self._baseDir, target)
						
						if not exists(filename):
							self._issue_handler.issue(Issue("Document <b>%s</b> could not be found" % target, Issue.VALIDATE_WARNING, 
													node.start, node.lastEnd, filename))
				
				elif self._checkRefs and node.value == "bibliography":
					# check referenced BibTeX file(s)
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					for target in value.split(","):
						if target[0] == "/":
							filename = target + ".bib"
						else:
							filename = "%s/%s.bib" % (self._baseDir, target)
						
						if not exists(filename):
							self._issue_handler.issue(Issue("Bibliography <b>%s</b> could not be found" % filename, Issue.VALIDATE_WARNING, 
													node.start, node.lastEnd, filename))
				
				elif node.value == "newcommand":
					# don't validate in newcommand definitions
					recurse = False
				
				elif node.value == "bibliographystyle":
					# check if style exists
					value = node.firstOfType(Node.MANDATORY_ARGUMENT).innerText
					
					if not self._environment.fileExists("%s.bst" % value):
						self._issue_handler.issue(Issue("Bibliography style <b>%s</b> could not be found" % value, Issue.VALIDATE_WARNING, 
													node.start, node.lastEnd, filename))
				
				
			if recurse:
				self._run(node, filename)