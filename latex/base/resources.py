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
base.resources
"""

import logging
import os.path
import shutil

from ..util import open_error

_log = logging.getLogger("resources")

_PATH_ME = os.path.realpath(os.path.dirname(__file__))
_PATH_SYSTEM = "/usr/share/gedit/plugins/latex"
_PATH_USER = os.path.expanduser("~/.local/share/gedit/plugins/latex")
_PATH_SRCDIR = os.path.abspath(os.path.join(_PATH_ME,"..","..","data"))

# the order is important, for development it is useful to symlink
# the plugin into ~/.local/share/gedit/plugin and run it. In that case
# the first location to check for resources is the data dir in the
# source directory
#
# beyond that case, by preferring the local copy to the system one, it
# allows the user to customize things cleanly
_PATH_RO_RESOURCES = [p for p in (
    _PATH_SRCDIR, _PATH_USER, _PATH_SYSTEM) if os.path.exists(p)]

_log.debug("RO locations: %s" % ",".join(_PATH_RO_RESOURCES ))
_log.debug("RW location: %s" % _PATH_SYSTEM)

_installed_system_wide = os.path.exists(_PATH_SYSTEM)
if _installed_system_wide:
    # ensure that we have a user plugin dir
    if not os.path.exists(_PATH_USER):
        _log.debug("Creating %s" % _PATH_USER)
        os.makedirs(_PATH_USER)
    PLUGIN_PATH = _PATH_SYSTEM      # FIXME: only used by build to expand $plugin
else:
    PLUGIN_PATH = _PATH_USER

MODE_READONLY, MODE_READWRITE = 1, 2

def find_resource(relative_path, access_mode=MODE_READONLY):
    """
    This locates a resource used by the plugin. The access mode determines where to
    search for the relative path.

    @param relative_path: a relative path like 'icons/smiley.png'
    @param access_mode: MODE_READONLY|MODE_READWRITE

    @return: the full filename of the resource
    """
    _log.debug("Finding: %s (%d)" % (relative_path, access_mode))
    if access_mode == MODE_READONLY:
        # locate a resource for read-only access. Prefer user files
        # to system ones. See comment above
        for p in _PATH_RO_RESOURCES:
            path = "%s/%s" % (p, relative_path)
            if os.path.exists(path):
                return path

        _log.critical("File not found: %s" % path)
        return None

    elif access_mode == MODE_READWRITE:
        # locate a user-specific resource for read/write access
        path = "%s/%s" % (_PATH_USER, relative_path)
        if os.path.exists(path):
            return path

        if _installed_system_wide:
            # resource doesn't exist yet in the user's directory
            # copy the system-wide version
            rw_source = "%s/%s" % (_PATH_SYSTEM, relative_path)
        else:
            # we are in the sourcedir
            rw_source = "%s/%s" % (_PATH_SRCDIR, relative_path)

        try:
            _log.info("Copying file to user path %s -> %s" % (rw_source, path))
            assert(rw_source != path)
            shutil.copyfile(rw_source, path)
        except IOError:
            _log.critical("Failed to copy resource to user directory: %s -> %s" % (rw_source, path))
        except AssertionError:
            _log.critical("Source and dest are the same. Bad programmer")

        return path


# ex:ts=4:et:
