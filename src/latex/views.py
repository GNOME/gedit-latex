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
latex.views

LaTeX-specific views
"""

import gtk
from logging import getLogger

from ..base.interface import View


class LaTeXConsistencyView(View):
    """
    Checking consistency of a LaTeX document means parsing and validating it.
    
    This view is file-specific
    """
    
    _log = getLogger("LaTeXConsistencyView")
    
    def __init__(self):
        self._log.debug("__init__")
        View.__init__(self)
    
    @staticmethod
    @property
    def position(self):
        return View.POSITION_BOTTOM
    
    @staticmethod
    @property
    def label(self):
        return "Consistency"
    
    @staticmethod
    @property
    def icon(self):
        return gtk.STOCK_CONVERT
    
    @staticmethod
    @property
    def scope():
        return View.SCOPE_EDITOR
    
    
    def clear(self):
        pass
    
    def append_issue(self, issue):
        self._log.debug("append_issue: " + str(issue))
        
        
class LaTeXSymbolMapView(View):
    """
    """
    _log = getLogger("LaTeXSymbolMapView")
    
    def __init__(self):
        self._log.debug("__init__")
        View.__init__(self)
    
    @staticmethod
    @property
    def position(self):
        return View.POSITION_SIDE
    
    @staticmethod
    @property
    def label(self):
        return "Symbols"
    
    @staticmethod
    @property
    def icon(self):
        return gtk.STOCK_CONVERT
    
    @staticmethod
    @property
    def scope(self):
        return View.SCOPE_WINDOW
    
        
        
        