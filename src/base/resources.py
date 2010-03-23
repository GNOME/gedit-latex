# -*- coding: utf-8 -*-

# This file is part of the Gedit LaTeX Plugin
#
# Copyright (C) 2009 Michael Zeising
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

Either the plugin is installed in ~/.gnome2/gedit/plugins/GeditLaTeXPlugin as
described in INSTALL or it's installed system-wide, e.g. by a .deb package.
For a system-wide installation everything but the pixmaps is copied to
/usr/lib/gedit-2/plugins/GeditLaTeXPlugin. And FHS requires to place the
pixmaps in /usr/share/gedit-2/plugins/GeditLaTeXPlugin.

To be backward compatibale when it's installed system-wide, we have to
look for pixmaps in _PATH_SYSTEM and _PATH_SHARE.
"""

import logging
from os import makedirs
from os.path import expanduser, exists
from shutil import copyfile

from ..util import open_error


logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("resources")

#
# init plugin resource locating
#

# TODO: switch to gedit.Plugin.get_data_dir()

_PATH_SYSTEM = "/usr/lib/gedit-2/plugins/GeditLaTeXPlugin"
_PATH_USER = expanduser("~/.gnome2/gedit/plugins/GeditLaTeXPlugin")

# FHS-compliant location for pixmaps
_PATH_SHARE = "/usr/share/gedit-2/plugins/GeditLaTeXPlugin"


_log.debug("Initializing resource locating")

_installed_system_wide = exists(_PATH_SYSTEM)
if _installed_system_wide:
	# ensure that we have a user plugin dir
	if not exists(_PATH_USER):
		_log.debug("Creating %s" % _PATH_USER)
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
			
			if not exists(path):
				# second chance: look in _PATH_SHARE
				path = "%s/%s" % (_PATH_SHARE, relative_path)
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

