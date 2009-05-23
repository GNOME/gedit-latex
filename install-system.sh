#!/bin/sh

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

#
# install the plugin system-wide
#

PLUGINS_LIB="/usr/lib/gedit-2/plugins"
PLUGINS_SHARE="/usr/share/gedit-2/plugins"
NAME="GeditLaTeXPlugin"

# ensure that all directories exist
mkdir --parents $PLUGINS_LIB/$NAME
mkdir --parents $PLUGINS_SHARE/$NAME

# copy plugin definition
cp $NAME.gedit-plugin $PLUGINS_LIB

# copy pixmaps to share
cp --recursive icons $PLUGINS_SHARE/$NAME/icons

# copy all other resources to lib 
cp *.xml $PLUGINS_LIB/$NAME
cp --recursive src $PLUGINS_LIB/$NAME/src
cp --recursive glade $PLUGINS_LIB/$NAME/glade
cp --recursive util $PLUGINS_LIB/$NAME/util
