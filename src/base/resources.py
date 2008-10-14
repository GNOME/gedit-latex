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
base.resources
"""

import logging
from os import makedirs
from os.path import expanduser, exists
from shutil import copyfile

from ..util import open_error


#
# init plugin resource locating
#

_PATH_SYSTEM = "/usr/lib/gedit-2/plugins/GeditLaTeXPlugin"
_PATH_USER = expanduser("~/.gnome2/gedit/plugins/GeditLaTeXPlugin")

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("resources")

_log.debug("Initializing resource locating")

_installed_system_wide = exists(_PATH_SYSTEM)
if _installed_system_wide:
	# ensure that we have a user plugin dir
	if not exists(_PATH_USER):
		makedirs(_PATH_USER)
	
	PLUGIN_PATH = _PATH_SYSTEM	# only used by build to expand $plugin
else:
	PLUGIN_PATH = _PATH_USER	# only used by build to expand $plugin


MODE_READONLY, MODE_READWRITE = 1, 2


def find_resource(relative_path, access_mode=MODE_READONLY):
	"""
	This locates a resource used by the plugin. The access mode determines where to 
	search for the relative path.
	
	@param relative_path: a relative path like 'icons/smiley.png'
	@param access_mode: MODE_READONLY|MODE_READWRITE
	
	@return: the full filename of the resource
	"""
	if access_mode == MODE_READONLY:
		#
		# locate a system-wide resource for read-only access
		#
		if _installed_system_wide:
			path = "%s/%s" % (_PATH_SYSTEM, relative_path)
		else:
			path = "%s/%s" % (_PATH_USER, relative_path)
		
		if not exists(path):
			_log.warning("File not found: %s" % path)
		
		return path
	
	elif access_mode == MODE_READWRITE:
		#
		# locate a user-specific resource for read/write access
		#
		path = "%s/%s" % (_PATH_USER, relative_path)
	
		if _installed_system_wide and not exists(path):
			# resource doesn't exist yet in the user's directory
			# copy the system-wide version		
			try:
				copyfile("%s/%s" % (_PATH_SYSTEM, relative_path), path)
			except IOError:
				_log.warning("Failed to copy resource to user directory: %s" % relative_path)
		return path

