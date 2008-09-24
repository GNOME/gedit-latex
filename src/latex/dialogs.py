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
latex.dialogs
"""

from ..util import GladeInterface
from ..base.resources import find_resource


class ChooseMasterDialog(GladeInterface):
	"""
	Dialog for choosing a master file to a LaTeX fragment file
	"""
	
	_filename = find_resource("glade/choose_master_dialog.glade")
	
	def run(self, folder):
		"""
		Runs the dialog and returns the selected filename
		
		@param folder: a folder to initially place the file chooser
		"""
		dialog = self._find_widget("dialogSelectMaster")
		file_chooser_button = self._find_widget("filechooserbutton")
		file_chooser_button.set_current_folder(folder)
		
		if dialog.run() == 1:
			filename = file_chooser_button.get_filename()
		else:
			filename = None
		dialog.hide()
		
		return filename
	