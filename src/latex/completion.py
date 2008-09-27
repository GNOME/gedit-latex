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
latex.completion

LaTeX-specific completion classes
"""

from logging import getLogger

from ..base import ICompletionHandler, IProposal, Template


class LaTeXCommandProposal(IProposal):
	"""
	A proposal inserting a Template when activated
	"""
	icon = None
	
	def __init__(self, overlap, template, label):
		self._template = template
		self._label = label
		self._overlap = overlap
	
	@property
	def source(self):
		return self._template
	
	@property
	def label(self):
		return self._label
	
	@property
	def details(self):
		return None
	
	@property
	def overlap(self):
		return self._overlap
	

class LaTeXChoiceProposal(IProposal):
	"""
	A proposal inserting a simple string when activated
	"""
	icon = None
	
	def __init__(self, overlap, source, label, details):
		self._source = source
		self._details = details
		self._overlap = overlap
		self._label = label
	
	@property
	def source(self):
		return self._source
	
	@property
	def label(self):
		return self._label
	
	@property
	def details(self):
		return self._details
	
	@property
	def overlap(self):
		return self._overlap
	
	
from model import LanguageModelFactory, Command, Choice, MandatoryArgument, OptionalArgument
from parser import PrefixParser, Node


class LaTeXCompletionHandler(ICompletionHandler):
	"""
	This implements the LaTeX-specific code completion
	"""
	_log = getLogger("LaTeXCompletionHandler")
	
	trigger_keys = ["backslash", "braceleft"]
	prefix_delimiters = ["\\"]
	strip_delimiter = False			# don't remove the '\' from the prefix
	
	def __init__(self):
		self._log.debug("init")
		
		self._language_model = LanguageModelFactory().create_language_model()
		
	def set_outline(self, outline):
		"""
		Process a LaTeX outline model
		"""
		self._outline = outline
		
		# labels
		label_choices = [Choice(None, label.value) for label in outline.labels]
		self._language_model.fill_placeholder("Labels", label_choices)
		
		# colors
		color_choices = [Choice(None, color) for color in outline.colors]
		self._language_model.fill_placeholder("Colors", color_choices)
		
		# newcommands
		newcommands = []
		for n in outline.newcommands:
			command = Command(None, n.value)
			for i in range(n.numOfArgs):
				command.children.append(MandatoryArgument(None, "#%s" % (i + 1)))
			newcommands.append(command)
		self._language_model.set_newcommands(newcommands)
		
		# TODO: BibTeX entries
	
	def set_neighbors(self, tex_files, bib_files, graphic_files):
		"""
		"""
		tex_choices = [Choice(None, file.shortbasename) for file in tex_files]
		self._language_model.fill_placeholder("TexFiles", tex_choices)
		
		bib_choices = [Choice(None, file.shortbasename) for file in bib_files]
		self._language_model.fill_placeholder("BibFiles", bib_choices)
		
		graphic_choices = [Choice(None, file.basename) for file in graphic_files]
		self._language_model.fill_placeholder("ImageFiles", graphic_choices)
	
	def complete(self, prefix):
		"""
		Try to complete a given prefix
		"""
		self._log.debug("complete: '%s'" % prefix)
		
		#proposals = [LaTeXTemplateProposal(Template("Hello[${One}][${Two}][${Three}]"), "Hello[Some]"), LaTeXProposal("\\world")]
		
		fragment = Node(Node.DOCUMENT)
		parser = PrefixParser()
		
		try:
			parser.parse(prefix, fragment)
			
			modelParser = PrefixModelParser(self._language_model)
			proposals = modelParser.parse(fragment)	
			
			self._log.debug("Generated %s proposals" % len(proposals))
			
			return proposals
			
		except Exception, e:
			self._log.debug(e)
		
		return []


from . import LaTeXSource


class PrefixModelParser(object):
	"""
	This parses the dcoument model of a prefix and generates proposals accordingly
	
	This is used by the LatexProposalGenerator class
	"""
	
	# FIXME: Completion doesn't work at \includegraphics[]{_} but at \includegraphics{_} 
	
	_log = getLogger("PrefixModelParser")
	
	def __init__(self, language_model):
		self.__language_model = language_model
	
	def __create_proposals_from_commands(self, commands, overlap):
		"""
		Generate proposals for commands
		"""
		proposals = []
		
		for command in commands:
			label = command.name
			templateSource = "\\" + command.name
			
			for argument in command.children:
				if type(argument) is MandatoryArgument:
					label += "{<i>%s</i>}" % argument.label
					templateSource += "{${%s}}" % argument.label
				elif type(argument) is OptionalArgument:
					label += "[<i>%s</i>]" % argument.label
					templateSource += "[${%s}]" % argument.label
			
			if command.package:
				label += " <small><b>%s</b></small>" % command.package
			
			proposal = LaTeXCommandProposal(overlap, LaTeXSource(Template(templateSource), [command.package]), label)
			proposals.append(proposal)
		
		return proposals
	
	def __create_proposals_from_choices(self, choices, overlap):
		"""
		Generate proposals for argument choices
		"""
		proposals = []
		
		for choice in choices:
			label = choice.value
			if choice.package:
				label += " <small><b>%s</b></small>" % choice.package
				
			proposal = LaTeXChoiceProposal(overlap, LaTeXSource(choice.value, [choice.package]), label, choice.details)
			proposals.append(proposal)
		
		return proposals
	
	def parse(self, prefixFragment):
		"""
		Returns choices
		"""
		
		# we suppose that the last node must be the command
		
		commandNode = prefixFragment[-1]
		if commandNode.type != Node.COMMAND:
			return []
		
		commandName = commandNode.value
		
		if len(commandNode) == 0:
			# command has no arguments
			
			if len(commandName) == 0:
				# no name, so propose all commands
				commands = self.__language_model.commands.values()
				overlap = 1	    # only "\"
			else:
				commands = self.__language_model.find_command(commandName)
				
				if len(commands) == 1 and commands[0].name == commandName:
					# don't propose when only one command is found and that one
					# matches the typed one
					return []
				
				overlap = len(commandName) + 1 	    # "\begi"
				
			return self.__create_proposals_from_commands(commands, overlap)
		
		
		try:
			# get the model of the command
			storedCommand = self.__language_model.commands[commandName]
		
			# push arguments of the command model on a stack
			stack = []
			stack.extend(storedCommand.children)
			stack.reverse()
			
			# walk the arguments of the prefix model
			for argumentNode in commandNode:
				
				storedArgument = None
				
				if argumentNode.type == Node.MANDATORY_ARGUMENT:
					
					# skip all arguments on stack until {}
					try:
						while True:
							storedArgument = stack.pop()
							if type(storedArgument) is MandatoryArgument:
								break
					except IndexError:
						self._log.debug("Signatures don't match")
						return []
				
				elif argumentNode.type == Node.OPTIONAL_ARGUMENT:
					
					storedArgument = stack.pop()
					
					if not type(storedArgument) is OptionalArgument:
						self._log.debug("Signatures don't match")
						return []
					
				# now we should have the right argument in {storedArgument}
				
				choices = storedArgument.children
				
				# filter argument matching the already typed argument text
				
				argumentValue = argumentNode.innerText
				
				if len(argumentValue):
					choices = [choice for choice in choices if choice.value.startswith(argumentValue)]
					overlap = len(argumentValue)
				else:
					overlap = 0
				
				return self.__create_proposals_from_choices(choices, overlap)
			
		except KeyError:
			self._log.debug("Command not found: %s" % commandName)
			return []
				
