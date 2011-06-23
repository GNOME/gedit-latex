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
PDF live preview

@author: Dan Mihai Ile (mihai007)
         Yannick Voglaire (yannickv)
"""

import os
import cairo
import logging

from gi.repository import Gedit, Gtk, Gdk, GObject, Pango

from ..preferences import Preferences
from ..base import File		

"""
TODO:
- Make the "padding" in PreviewPanel a constant defined at the beginning. 
  It is used in too many places with the explicit value "2".
- Replace the popup menu items by Actions from latex/actions.py, and add 
  these also to the "Embedded Preview" menu (Next page, Previous page, 
  Toggle continuous, Document properties, Open in default viewer).
- Add toolbar items to check and modify the zoom status and page number.
- ...
"""


class LaTeXPreviews:
	"""
	Class that manages all tab's preview panels.
	"""
	
	_log = logging.getLogger("LaTeXPreviews")
	
	ZOOM_IN, ZOOM_OUT = range(2)
	SCROLL_UP, SCROLL_DOWN, SCROLL_LEFT, SCROLL_RIGHT = range(4)
	
	def __init__(self, context):
		"""
		Initializes the PDF preview.
		"""
		
		self._preferences = Preferences()
		
		self._context = context

		# keep track of all gedit tabs that have preview enabled
		self.__pane_position_id = {}
		self.split_views = {}
		self.preview_panels = {}


	def is_shown(self, tab):
		return (tab in self.split_views)
		
		
	def toggle(self, tab, compiled_file_path):
		"""
		Enables/disables the preview window for the tab "tab".
		@param tab: the tab to toggle the preview of
		@param compiled_file_path: the path to the compiled file
		"""

		# If we already have a preview for this tab, remove it
		if self.is_shown(tab):
			self.hide(tab)
		# Otherwise, start the preview
		else:
			self.show(tab, compiled_file_path)


	def show(self, tab, compiled_file_path):
		"""
		Creates the actual split view.
		@param tab: the tab to show the preview in
		@param compiled_file_path: the path to the compiled file
		"""
		
		if self.is_shown(tab):
			if self.preview_panels[tab].file_path != compiled_file_path:
				self.update_file_path(tab, compiled_file_path)
			return
		
		# Get the preferred width for the pdf preview (default: (A4 width (scale 1) + scrollbar) (=620) + shadow)
		preview_width = int(self._preferences.get("PdfPreviewWidth", 623))
		
		# Here we assume that the tab only contains the scrolled window containing the view
		# (actually another plugin could have added another view in the tab...)
		old_scrolled_view = tab.get_children()[0]
		tab.remove(old_scrolled_view)

		preview_panel = None
		
		# If the same pdf is already opened for another source file,
		# we use the same panel for both
		for tabb in self.preview_panels:
			if self.preview_panels[tabb].file_path == compiled_file_path:
				preview_panel = self.preview_panels[tabb]
				preview_panel.get_panel().get_parent().remove(preview_panel.get_panel())
				
				total_width = self.split_views[tabb].get_property("max-position")
				position = self.split_views[tabb].get_position()
				preview_width = total_width - position
				
				break
			
		# If not, create the panel
		if preview_panel == None:
			preview_panel = PreviewPanel(self, compiled_file_path)

		self.preview_panels[tab] = preview_panel

		# Create the Paned object which will contain the old view and the preview
		self.split_views[tab] = Gtk.HPaned()

		# Add the two scrolled windows to our Paned object.
		# Ask that when the window is resized, the preview keep the same size
		self.split_views[tab].pack1(old_scrolled_view, True, True)
		self.split_views[tab].pack2(preview_panel.get_panel(), False, True)

		# Request the preferred width for the preview
		self.split_views[tab].get_child2().set_size_request(preview_width, -1)

		# Monitor the handle position to keep the document centered
		self.__pane_position_id[tab] = self.split_views[tab].connect("notify::position", self.__pane_moved)

		# Add the Paned object to the tab
		tab.pack_start(self.split_views[tab], True, True, 0)
		
		tab.show_all()
		preview_panel.get_panel().grab_focus()


	def hide(self, tab):
		"""
		Ends the preview for the tab "tab".
		@param tab: the tab to hide the preview of
		"""
		
		original_view = self.split_views[tab].get_child1()

		preview_panel = self.preview_panels[tab]
		self.preview_panels.pop(tab)

		destroy_panel = True
		for tabb in self.preview_panels:
			if self.preview_panels[tabb] == preview_panel:
				self._log.debug("Found another split view for the same output file, not destroying this panel.")
				destroy_panel = False
				panel = preview_panel.get_panel()
				parent = panel.get_parent()
				parent.remove(panel)
				self.split_views[tabb].pack2(panel, False, True)
				self.split_views[tabb].set_position(parent.get_position())
				break
		if destroy_panel:
			preview_panel.destroy()
		
		self.split_views[tab].disconnect(self.__pane_position_id[tab])
		del self.__pane_position_id[tab]
		tab.remove(self.split_views[tab])
		
		original_view.reparent(tab)
		
		self.split_views.pop(tab)
		
		tab.show_all()
		
	
	def reparent(self, tab):
		"""
		Attaches the panel corresponding to "tab" to the split view 
		corresponding to "tab". A same panel is shared between all 
		split views corresponding to a single compiled file.
		Called by GeditWindowDecorator.adjust().
		"""
		
		panel = self.preview_panels[tab].get_panel()
		parent = panel.get_parent()
		if parent != self.split_views[tab]:
			parent.remove(panel)
			self.split_views[tab].pack2(panel, False, True)
			self.split_views[tab].set_position(parent.get_position())


	def update_file_path(self, tab, compiled_file_path):
		"""
		Updates the compiled file path for the preview.
		Called on "Save as...".
		"""

		old_path = self.preview_panels[tab].file_path
		if compiled_file_path == old_path:
			return
		
		complete_update_needed = False
		for tabb in self.preview_panels:
			if (tabb != tab and self.preview_panels[tabb].file_path == old_path) \
					or self.preview_panels[tabb].file_path == compiled_file_path:
				complete_update_needed = True
		if complete_update_needed:
			self.hide(tab)
			self.show(tab, compiled_file_path)
			return
			
		self.preview_panels[tab].update_file_path(compiled_file_path)


	def zoom(self, tab, direction):
		"""
		Called by src.latex.LaTeXPreviewZoom{In,Out}Action.
		"""
		
		if not self.is_shown(tab):
			return
		
		if direction == self.ZOOM_IN:
			self.preview_panels[tab].zoom_in()
		elif direction == self.ZOOM_OUT:
			self.preview_panels[tab].zoom_out()


	def scroll(self, tab, direction):
		"""
		Called by src.latex.LaTeXPreviewScroll{Up,Down,Left,Right}Action.
		"""
		
		if not self.is_shown(tab):
			return
		
		if direction == self.SCROLL_UP:
			self.preview_panels[tab].scroll_up()
		elif direction == self.SCROLL_DOWN:
			self.preview_panels[tab].scroll_down()
		elif direction == self.SCROLL_LEFT:
			self.preview_panels[tab].scroll_left()
		elif direction == self.SCROLL_RIGHT:
			self.preview_panels[tab].scroll_right()


	def sync_view(self, tab, source_file, line, column, output_file):
		"""
		Called by the editor to view the corresponding output.
		"""

		if not self.is_shown(tab):
			self.show(tab, output_file)
			# When we are in this case, as opening the preview 
			# takes some time, calling directly sync_view does nothing.
			# Thus we wait for the panel to be opened to send the call.
			while Gtk.events_pending():
				Gtk.main_iteration(False)
			self.__sync_handler = GObject.idle_add(self.__sync_view, tab, source_file, line, column, output_file)
			return
		
		self.preview_panels[tab].sync_view(source_file, line, column, output_file)
		self.preview_panels[tab].get_panel().grab_focus()
		
	
	def __sync_view(self, tab, source_file, line, column, output_file):
		self.preview_panels[tab].sync_view(source_file, line, column, output_file)
		self.preview_panels[tab].get_panel().grab_focus()
		GObject.source_remove(self.__sync_handler)
				
	
	def sync_edit(self, source_file, output_file, line, column, offset, context):
		"""
		Called by the (internal) viewer to edit the corresponding source.
		"""
		
		self._log.debug("Sync edit. Source:%s, Output:%s, Line:%d, Column:%d, Offset:%d, Context:%s" % (source_file, output_file, line, column, offset, context))
		
		if not File.is_absolute(source_file):
			file = File.create_from_relative_path(source_file, File(output_file).dirname)
		else:
			file = File(source_file)
		self._context.activate_editor(file)
		
		# wait for the editor to be adjusted
		while Gtk.events_pending():
			Gtk.main_iteration(False)

		editor = self._context.active_editor
		
		if type(editor) == type(None):
			# This happens when we are in a .toc file for example.
			return

		# show the preview
		# this gives the focus to the preview, but we were syncing 
		# view to source so we do it before giving the focus to the editor
		tab = self._context._window_decorator._active_tab_decorator.tab
		self.show(tab, output_file)

		# sync the editor
		editor._text_buffer.goto_line(line - 1)
		editor._text_view.scroll_to_cursor()

		editor._text_view.grab_focus()
		
		
	def __pane_moved(self, pane, paramspec):
		"""
		Saves the width of the preview each time it is modified.
		"""

		total_width = pane.get_property("max-position")
		position = pane.get_position()
		preview_width = total_width - position
		self._preferences.set("PdfPreviewWidth", preview_width)
		
	
	def destroy(self):
		self._log.debug("destroy")
		del self._context
		del self._preferences
		for tab in self.split_views:
			# unlikely but...
			self.hide(tab)
			
	def __del__(self):
		self._log.debug("Properly destroyed %s" % self)



class PreviewDocument:
	"""
	Class that abstracts document methods for a future pdf and ps support.
	Currently only pdf. The goal is to keep calls to external libraries 
	confined in this class.
	"""

	_log = logging.getLogger("PreviewDocument")
	
	TYPE_PDF = 0
	TYPE_PS = 1
	
	def __init__(self, document_path):
		"""
		Initializes the ps or pdf document with name document_path.
		"""

		# TODO: Handle errors
		# TODO: Support postscript documents

		self._log.debug("Initialize %s" % self)
		
		self.__document_path = document_path
		self.document_loaded = False
		if self.__document_path.endswith(".pdf"):
			try:
				import poppler
			except:
				self._log.warning("Error loading poppler (python-poppler not installed ?).")
				self.__document_type = None
				self.__document = None
				return
			self.__document_type = self.TYPE_PDF
			self.__document = poppler.document_new_from_file("file://%s" % self.__document_path, None)
			self.document_loaded = True
		elif self.__document_path.endswith(".ps"):
			self.__document_type = self.TYPE_PS
			self.__document = None
		else:
			self.__document_type = None
			self.__document = None
		self.__pages = {}


	def is_pdf(self):
		return (self.__document_type == self.TYPE_PDF)
		
		
	def is_ps(self):
		return (self.__document_type == self.TYPE_PS)
		
	
	def get_document_path(self):
		return "file://%s" % self.__document_path
		
		
	def get_n_pages(self):
		if not self.__document_type is None:
			return self.__document.get_n_pages()
		else:
			return None


	def get_page(self, index):
		if not self.__document_type is None:
			if index not in self.__pages:
				# There seems to be a huge memory leak in this call. 
				# This is why we save the page in a local variable, 
				# in order not to call pypoppler_document_get_page() too often.
				self.__pages[index] = self.__document.get_page(index)
			return self.__pages[index]
		else:
			return None


	def get_size_from_page(self, page):
		if not self.__document_type is None:
			return page.get_size()
		else:
			return None


	def free_page(self, page):
		if self.__document_type == self.TYPE_PDF:
			import ctypes
			glib = ctypes.CDLL("libgobject-2.0.so.0")
			glib.g_object_unref(hash(page))
			del page
		else:
			# Was necessary with libspectre: spectre_page_free(page)
			pass


	def get_page_size(self, index):
		page = self.get_page(index)
		if page is None:
			return None
		size = self.get_size_from_page(page)
		#~ self.free_page(page)
		return size


	def render_page(self, rc, index):
		if self.__document_type == self.TYPE_PDF:
			return self.get_page(index).render(rc)
		else:
			return None
	
	
	def render_page_to_pixbuf(self, index, x, y, width, height, scale, rotation, pixbuf):
		if self.__document_type == self.TYPE_PDF:
			return self.get_page(index).render_to_pixbuf(x, y, width, height, scale, rotation, pixbuf)
		else:
			return None
	
	
	def get_property(self, name):
		if self.__document_type == self.TYPE_PDF:
			return self.__document.get_property(name)
			
	
	def permissions_to_text_list(self, permissions):
		if self.__document_type == self.TYPE_PDF:
			import poppler
			perm = []
			if permissions & poppler.PERMISSIONS_OK_TO_PRINT:
				perm.append("print")
			if permissions & poppler.PERMISSIONS_OK_TO_MODIFY:
				perm.append("modify")
			if permissions & poppler.PERMISSIONS_OK_TO_COPY:
				perm.append("copy")
			if permissions & poppler.PERMISSIONS_OK_TO_ADD_NOTES:
				perm.append("add notes")
			if permissions & poppler.PERMISSIONS_OK_TO_FILL_FORM:
				perm.append("fill forms")
			return perm
		else:
			return str(permissions)
	
	
	def page_layout_to_text(self, layout):
		if self.__document_type == self.TYPE_PDF:
			import poppler
			if layout == poppler.PAGE_LAYOUT_UNSET:
				return "Unset"
			elif layout == poppler.PAGE_LAYOUT_SINGLE_PAGE:
				return "Single page, advancing flips the page"
			elif layout == poppler.PAGE_LAYOUT_ONE_COLUMN:
				return "One column, continuous scrolling"
			elif layout == poppler.PAGE_LAYOUT_TWO_COLUMN_LEFT:
				return "Two columns, odd-numbered pages to the left"
			elif layout == poppler.PAGE_LAYOUT_TWO_COLUMN_RIGHT:
				return "Two columns, odd-numbered pages to the right"
			elif layout == poppler.PAGE_LAYOUT_TWO_PAGE_LEFT:
				return "Two pages, odd-numbered pages to the left"
			elif layout == poppler.PAGE_LAYOUT_TWO_PAGE_RIGHT:
				return "Two pages, odd-numbered pages to the right"
			else:
				return str(layout)
		else:
			return str(layout)
	
	
	def page_mode_to_text(self, mode):
		if self.__document_type == self.TYPE_PDF:
			import poppler
			if mode == poppler.PAGE_MODE_UNSET:
				return "Unset"
			elif mode == poppler.PAGE_MODE_NONE:
				return "None"
			elif mode == poppler.PAGE_MODE_USE_OUTLINES:
				return "Use outlines"
			elif mode == poppler.PAGE_MODE_USE_THUMBS:
				return "Use thumbs"
			elif mode == poppler.PAGE_MODE_FULL_SCREEN:
				return "Full screen"
			elif mode == poppler.PAGE_MODE_USE_OC:
				return "Use OC"
			elif mode == poppler.PAGE_MODE_USE_ATTACHMENTS:
				return "Use attachments"
			else:
				return str(mode)
		else:
			return str(mode)
	
	
	def viewer_preferences_to_text_list(self, preferences):
		if self.__document_type == self.TYPE_PDF:
			import poppler
			pref = []
			if preferences & poppler.VIEWER_PREFERENCES_UNSET:
				pref.append("Unset")
			if preferences & poppler.VIEWER_PREFERENCES_HIDE_TOOLBAR:
				pref.append("Hide toolbar")
			if preferences & poppler.VIEWER_PREFERENCES_HIDE_MENUBAR:
				pref.append("Hide menubar")
			if preferences & poppler.VIEWER_PREFERENCES_HIDE_WINDOWUI:
				pref.append("Hide window UI")
			if preferences & poppler.VIEWER_PREFERENCES_FIT_WINDOW:
				pref.append("Fit window")
			if preferences & poppler.VIEWER_PREFERENCES_CENTER_WINDOW:
				pref.append("Center window")
			if preferences & poppler.VIEWER_PREFERENCES_DISPLAY_DOC_TITLE:
				pref.append("Display document title")
			if preferences & poppler.VIEWER_PREFERENCES_DIRECTION_RTL:
				pref.append("Direction right-to-left")
			return pref
		else:
			return str(preferences)


	def open_in_external_viewer(self):
		"""
		Opens the document in the default external viewer.
		"""
		
		# Should it be configurable ? The gnome defaults should be what 
		# the user wants for a gnome program normally...
		import os
		os.system("gnome-open \"%s\"" % self.get_document_path())
		
		
	def get_page_links(self, page_index):
		if self.__document_type == self.TYPE_PDF:
			import poppler
			
			# python-poppler version 0.10.* and before, do not support 
			# actions (at least not in a usable way)
			[maj, min, rev] = poppler.pypoppler_version
			if int(min) < 12:
				return []
			
			page = self.get_page(page_index)
			lm = page.get_link_mapping()
			width, height = self.get_size_from_page(page)
			
			links = []
			for link in lm:
				# area is in PDF coordinates (bottom-left based), so we
				# first convert them to top-left based page coordinates
				area = link.area
				(x1, y1, x2, y2) = area.x1, height - area.y2, area.x2, height - area.y1
				
				# Handle title ?
				type = None
				dest = None
				if isinstance(link.action, poppler.ActionGotoDest):
					named_dest = link.action.dest.named_dest
					links.append(PreviewDocumentLinkGotoDest(self, page, x1, y1, x2, y2, named_dest))
				elif isinstance(link.action, poppler.ActionNamed):
					named_dest = link.action.named_dest
					links.append(PreviewDocumentLinkNamed(self, page, x1, y1, x2, y2, named_dest))
				elif isinstance(link.action, poppler.ActionUri):
					uri = link.action.uri
					links.append(PreviewDocumentLinkURI(self, page, x1, y1, x2, y2, uri))
				else:
					self._log.debug("Action not handled: %s" % link.action)
				
			return links
			
	
	def find_named_dest(self, name):
		if self.__document_type == self.TYPE_PDF:
			return self.__document.find_dest(name)
			
	
	def __del__(self):
		# We use glib.g_object_unref to destroy poppler pages and documents.
		# This reduces memory leakage (a lot ?).
		# Due to bugs #316722 and #509408 (on launchpad) in python-poppler.

		self._log.debug("Destroy %s" % self)
		
		if not self.document_loaded:
			return
			
		try:
			import ctypes
			glib = ctypes.CDLL("libgobject-2.0.so.0")
		except:
			try:
				import ctypes
				glib = ctypes.CDLL("libgobject-2.0.so")
			except:
				self.__pages = {}
				self.__document = None
				return
		
		for page in self.__pages:
			# The information in the log is in the event ctypes crashes
			self._log.debug("Destroying poppler page %d, %s, hash %s" % (page, type(self.__pages[page]), hash(self.__pages[page])))
			glib.g_object_unref(hash(self.__pages[page]))
		self.__pages = {}
		
		self._log.debug("Destroying poppler document %s, hash %s" % (type(self.__document), hash(self.__document)))
		glib.g_object_unref(hash(self.__document))
		self.__document = None
			
			
			
class PreviewDocumentLink:
	
	ACTION_GOTO_DEST = 0
	ACTION_URI = 1
	ACTION_NAMED = 2
	
	def __init__(self, document, page, x1, y1, x2, y2):
		self.type = None
		self._document = document
		self.page = page
		self.x1 = x1
		self.y1 = y1
		self.x2 = x2
		self.y2 = y2


	def activate(self, preview_panel):
		pass
		
	
	@property
	def tooltip(self):
		return ""



class PreviewDocumentLinkGotoDest(PreviewDocumentLink):
	
	_log = logging.getLogger("PreviewDocumentLinkGotoDest")
	
	def __init__(self, document, page, x1, y1, x2, y2, named_dest):
		PreviewDocumentLink.__init__(self, document, page, x1, y1, x2, y2)
		self.type = self.ACTION_GOTO_DEST
		self.named_dest = named_dest
		
		
	def activate(self, preview_panel):
		dest = self._document.find_named_dest(self.named_dest)
		
		page = dest.page_num - 1
		page_width, page_height = self._document.get_page_size(page)
		vert_pos = page_height - dest.top - 5
		preview_panel.go_to_page_and_position(page, vert_pos)
		
		self._log.debug("Activate link: %s" % self.named_dest)


	@property
	def tooltip(self):
		dest = self._document.find_named_dest(self.named_dest)
		return "Go to page %d" % dest.page_num



class PreviewDocumentLinkURI(PreviewDocumentLink):
	
	_log = logging.getLogger("PreviewDocumentLink")
	
	def __init__(self, document, page, x1, y1, x2, y2, uri):
		PreviewDocumentLink.__init__(self, document, page, x1, y1, x2, y2)
		self.type = self.ACTION_URI
		self.uri = uri
		
		
	def activate(self, preview_panel):
		import os
		os.system("gnome-open \"%s\"" % self.uri)
		
		self._log.debug("Activate link: %s" % self.uri)


	@property
	def tooltip(self):
		return "Browse URI %s" % self.uri



class PreviewDocumentLinkNamed(PreviewDocumentLink):
	
	_log = logging.getLogger("PreviewDocumentLinkNamed")
	
	def __init__(self, document, page, x1, y1, x2, y2, named_dest):
		PreviewDocumentLink.__init__(self, document, page, x1, y1, x2, y2)
		self.type = self.ACTION_NAMED
		self.named_dest = named_dest
		# possibilities: GoForward, GoBack, Find, GoToPage, NextPage, ...
		# GoForward and GoBack (used by beamer class for example, and
		# implemented in Acrobat Reader but not evince) would 
		# necessitate the introduction of a "history" of moves in the 
		# document.
		
		
	def activate(self, preview_panel):
		self._log.debug("Activate link: %s" % self.named_dest)


	@property
	def tooltip(self):
		return "Named destination %s" % self.named_dest



class PreviewLink(Gtk.EventBox):
	"""
	The sensitive area in the preview corresponding to a document link."
	"""
	
	def __init__(self, preview_panel, document_link):
		GObject.GObject.__init__(self)

		self.__preview_panel = preview_panel
		self.doc_link = document_link

		scale = self.__preview_panel.scale
		width = int((self.doc_link.x2 - self.doc_link.x1 + 1) * scale)
		height = int((self.doc_link.y2 - self.doc_link.y1 + 1) * scale)
		
		self.set_size_request(width, height)
		self.set_visible_window(False)
		
		self.__handlers = [ self.connect("button-press-event", self.__on_button_press),
							self.connect("button-release-event", self.__on_button_release),
							self.connect("motion-notify-event", self.__on_motion),
							self.connect("enter-notify-event", self.__on_enter),
							self.connect("leave-notify-event", self.__on_leave) ]
		
		
	def update(self):
		# Called when changing scale of the preview
		scale = self.__preview_panel.scale
		width = int((self.doc_link.x2 - self.doc_link.x1 + 1) * scale)
		height = int((self.doc_link.y2 - self.doc_link.y1 + 1) * scale)
		
		self.set_size_request(width, height)

		
	def __on_button_press(self, widget, event):
		# prevent the signal from being passed to the preview panel,
		# except for Ctrl+Left button for synctex
		if event.button == 1 and not (event.get_state() & Gdk.ModifierType.CONTROL_MASK):
			return True
		else:
			return False
		

	def __on_button_release(self, widget, event):
		if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
			return False
			
		self.__preview_panel.set_cursor(PreviewPanel.CURSOR_DEFAULT)
		self.__preview_panel.get_scrolled_window().set_tooltip_text(None)		
		self.doc_link.activate(self.__preview_panel)
		return True		
	

	def __on_motion(self, widget, event):
		# prevent the signal from being passed to the preview panel
		return True
		
		
	def __on_enter(self, widget, event):
		self.__preview_panel.set_cursor(PreviewPanel.CURSOR_LINK)
		self.__preview_panel.get_scrolled_window().set_tooltip_text(self.doc_link.tooltip)		
		

	def __on_leave(self, widget, event):
		self.__preview_panel.set_cursor(PreviewPanel.CURSOR_DEFAULT)
		self.__preview_panel.get_scrolled_window().set_tooltip_text(None)
		
		
	def destroy(self):
		for handler in self.__handlers:
			self.disconnect(handler)
		self.__preview_panel = None
		


class PreviewDrag:
	"""
	Class that manages the dragging of the preview.
	"""
	
	def __init__(self, preview_panel):
		self.__preview_panel = preview_panel
		self.__in_drag = False
		self.__handler = None
		self.__last_x = 0
		self.__last_y = 0


	def is_in_drag(self):
		return self.__in_drag
		
		
	def start(self, hscroll, vscroll, x, y):
		self.__in_drag = True
		self.__preview_panel.set_cursor(PreviewPanel.CURSOR_DRAG)

		self.__initial_hscroll = hscroll
		self.__initial_vscroll = vscroll
		self.__initial_x = x
		self.__initial_y = y
		
	
	def stop(self):
		self.__in_drag = False
		self.__preview_panel.set_cursor(PreviewPanel.CURSOR_DEFAULT)
		
		self.free_handlers()
	
	
	def update(self, x, y):
		self.__last_x = x
		self.__last_y = y
		
		# Schedule the actual move for a time where the computer 
		# has nothing better to do. The function __do_drag
		# always returns False, so that it is only executed once, 
		# even if it has been queued many times. This results in the 
		# view really following the mouse, and not lagging behind 
		# trying to execute every single mouse move.
		self.__handler = GObject.idle_add(self.__do_drag)
		

	def __do_drag(self):
		if self.__in_drag == True:
			hadj = self.__preview_panel.get_hadjustment()
			vadj = self.__preview_panel.get_vadjustment()

			new_hscroll = self.__initial_hscroll - (self.__last_x - self.__initial_x)
			new_vscroll = self.__initial_vscroll - (self.__last_y - self.__initial_y)

			new_hscroll = max(0, min(hadj.upper - hadj.page_size, new_hscroll))
			new_vscroll = max(0, min(vadj.upper - vadj.page_size, new_vscroll))
				
			hadj.set_value(new_hscroll)
			vadj.set_value(new_vscroll)
		return False


	def free_handlers(self):
		if not self.__handler is None:
			GObject.source_remove(self.__handler)
			self.__handler = None

	
	def destroy(self):
		self.free_handlers()
		self.__preview_panel = None

	
	
class GlassDrag:
	"""
	Class that manages the dragging of the magnifying glass.
	"""
	
	def __init__(self, preview_panel):
		self.__preview_panel = preview_panel
		self.__in_drag = False
		self.__handler = None
		self.__last_x = 0
		self.__last_y = 0


	def is_in_drag(self):
		return self.__in_drag
		
		
	def start(self, magnifying_glass, x, y):
		self.__in_drag = True
		self.__preview_panel.set_cursor(PreviewPanel.CURSOR_EMPTY)
		
		self.__magnifying_glass = magnifying_glass

		page, x_in_page, y_in_page = self.__preview_panel.get_page_and_position_from_pointer(x, y)

		self.__magnifying_glass.set_page_and_position(page, x_in_page, y_in_page)
		self.__magnifying_glass.show()

	
	def stop(self):
		self.__in_drag = False
		self.__preview_panel.set_cursor(PreviewPanel.CURSOR_DEFAULT)

		self.free_handlers()

		self.__magnifying_glass.hide()
	
	
	def update(self, root_x, root_y, x, y):
		self.__last_root_x = root_x
		self.__last_root_y = root_y

		self.__last_x = x
		self.__last_y = y
		
		# Schedule the actual move for a time where the computer 
		# has nothing better to do. The function __do_drag
		# always returns False, so that it is only executed once, 
		# even if it has been queued many times. This results in the 
		# view really following the mouse, and not lagging behind 
		# trying to execute every single mouse move.
		self.__handler = GObject.idle_add(self.__do_drag)


	def __do_drag(self):
		if self.__in_drag == True:
			page, x_in_page, y_in_page = self.__preview_panel.get_page_and_position_from_pointer(self.__last_x, self.__last_y)
			
			self.__magnifying_glass.set_page_and_position(page, x_in_page, y_in_page)
			self.__magnifying_glass.move_center_to(int(self.__last_root_x), int(self.__last_root_y))
			
			self.__magnifying_glass.refresh()
		return False


	def free_handlers(self):
		if not self.__handler is None:
			GObject.source_remove(self.__handler)
			self.__handler = None

	
	def destroy(self):
		self.free_handlers()
		self.__magnifying_glass = None
		self.__preview_panel = None

	
	
class SyncRectangle:
	"""
	Class that manages the highlighted rectangle in the preview
	when synchroning through synctex. Initialized in
	PreviewPanel.__init__() and used in PreviewPanel.sync_view()
	and PreviewPanel.__on_expose().
	"""

	def __init__(self):
		self.show_me = False
		self.__handler = None
		
		
	def show(self, page, x, y, width, height, drawing_area, scale):
		if self.__handler != None:
			self.hide()

		self.show_me = True
		
		self.page = page
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.drawing_area = drawing_area
		self.scale = scale
		
		self.__handler = GObject.timeout_add(1000, self.hide)
		
		self.drawing_area.window.invalidate_rect( \
					(int(self.x*self.scale)-4, \
									  int(self.y*self.scale)-4, \
									  int(self.width*self.scale)+8, \
									  int(self.height*self.scale)+8), \
					False)
		
		
	def hide(self):
		self.show_me = False
		GObject.source_remove(self.__handler)
		
		self.drawing_area.window.invalidate_rect( \
					(int(self.x*self.scale)-4, \
									  int(self.y*self.scale)-4, \
									  int(self.width*self.scale)+8, \
									  int(self.height*self.scale)+8), \
					False)
		
		return False
		
	def draw(self, cr, page):
		if self.show_me == True and self.page == page:
			cr.set_line_width(2)
			cr.set_source_rgb(255, 0, 0)
			cr.rectangle(self.x, self.y, self.width, self.height)
			cr.stroke()

		
		
class PreviewPanel:
	"""
	This class contains a view of the compiled file. A Gtk.Vbox is created
	that contains all visible elements, accessible through get_panel().
	If the file is not found or an error is triggered during the 
	preview generation a default display is shown.
	"""

	_log = logging.getLogger("PreviewPanel")
	
	ZOOM_NORMAL = 0
	ZOOM_FIT_WIDTH = 1
	ZOOM_FIT_PAGE = 2
	
	VIEW_CONTINUOUS = 0
	VIEW_SINGLE_PAGE = 1
	
	CURSOR_DEFAULT = 0
	CURSOR_EMPTY = 1
	CURSOR_DRAG = 2
	CURSOR_LINK = 3
	
	EVENT_CREATE = 0
	EVENT_RESIZE = 1
	EVENT_CHANGE_PAGE = 2
	EVENT_UPDATE_FILE = 3
	EVENT_TOGGLE_CONTINUOUS = 4
	
	DELAY_ZOOM = True
	
	def __init__(self, latex_previews, compiled_file_path):
		"""
		Creates a PreviewPanel given a compiled file path
		@param compiled_file_path: the path to the compiled file
		"""
		
		self._log.debug("Initialize")
		
		self._preferences = Preferences()

		self.__latex_previews = latex_previews
		
		self.__scale = float(self._preferences.get("PdfPreviewScale", 1.0))
		self.__scale_list = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0]

		self.__zoom_type = int(self._preferences.get("PdfPreviewZoomType", self.ZOOM_NORMAL))
		if self.__zoom_type not in [self.ZOOM_NORMAL, self.ZOOM_FIT_WIDTH, self.ZOOM_FIT_PAGE]:
			self.__zoom_type = self.ZOOM_NORMAL
		
		if int(self._preferences.get("PdfPreviewTypeOfView", self.VIEW_CONTINUOUS)) == self.VIEW_CONTINUOUS:
			self.__type_of_view = self.VIEW_CONTINUOUS
		else:
			self.__type_of_view = self.VIEW_SINGLE_PAGE
		
		# by default the document width and height is an A4 document
		self.__page_width = {}
		self.__page_height = {}
		(self.__page_width[0], self.__page_height[0]) = (595, 842)
		
		# the position of each page in the scrolled window
		self.__page_position = {}
		
		# Thickness of the shadow under each page
		# The real shadow has thickness self.__scale times this
		self.__shadow_thickness = 3.0
		
		# TODO preview message should be externalised and translatable
		self.__no_preview_message = "Preview not available..."
		self.__compiled_file_path = compiled_file_path
		self.__document = None

		# keep track of vertical scroll changes in the preview document
		self.__last_vertical_scroll_position = 0
		# same for the horizontal changes, starting centered
		self.__last_horizontal_scroll_position = None
		self.__last_horizontal_scroll_page_size = None
		
		self.__last_update_time = 0
		
		self.__drawing_areas = {}

		self.__vadj_changed_id = None
		self.__hadj_changed_id = None
		self.__vadj_value_id = None
		self.__hadj_value_id = None

		self.__expose_id = {}

		self.__mouse_handlers = []
		
		# Only used in "single page" type of view
		self.__current_page = 0

		# See self.__on_scroll()
		self.__scroll_up_count = 0
		self.__scroll_down_count = 0
		
		self.__preview_drag = PreviewDrag(self)
		self.__glass_drag = GlassDrag(self)
		
		self.__magnifying_glass = None
		
		self.__links = {}
		
		self.__sync_rectangle = SyncRectangle()

		# Cursors. Used in self.set_cursor().
		self.__cursor_default = None
		self.__cursor_drag = Gdk.Cursor.new(Gdk.CursorType.HAND1)
		self.__cursor_empty = Gdk.Cursor.new(Gdk.CursorType.BLANK_CURSOR)
		self.__cursor_link = Gdk.Cursor.new(Gdk.CursorType.HAND2)

		# TODO: very nasty hack to detect changes in pdf file
		# this is a 1000ms loop, there should be an event generated
		# by the plugin to notify that pdf file was updated
		self.__file_update_count = 0
		self.__check_changes_id = GObject.timeout_add(250, self.__check_changes)
		
		# the panel that will contain all visible elements
		# for the moment only the scrolled window, but there could be 
		# a toolbar for example
		self.__panel = Gtk.VBox()
		self.__panel.set_flags(Gtk.CAN_FOCUS)
		self.__connect_keyboard_events()

		# create the visible elements on the panel
		self.__create_scrolled_window()
		self.__update_scrolled_window(self.EVENT_CREATE)


	@property
	def scale(self):
		return self.__scale
		
		
	def __on_key_press(self, widget, event):
		key = Gdk.keyval_name(event.keyval)
		
		if key == "Tab":
			self.__latex_previews._context.active_editor._text_view.grab_focus()
		elif key == "Up":
			self.scroll_up()
		elif key == "Down":
			self.scroll_down()
		elif key == "Left":
			self.scroll_left()
		elif key == "Right":
			self.scroll_right()
		elif key == "plus":
			self.zoom_in()
		elif key == "minus":
			self.zoom_out()
		elif key == "equal":
			self.zoom_to(1.0, self.ZOOM_NORMAL)
		elif key == "Page_Up":
			if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
				self.go_to_page(-1, True)
			else:
				# We do it manually... should be in a method 
				# (self.scroll(type) with type in [TYPE_UP, TYPE_DOWN, 
				# TYPE_PAGE_UP, etc.] for example)
				vadj = self.get_vadjustment()
				vadj.set_value(max(vadj.lower, vadj.value - vadj.page_increment))
				if self.__type_of_view == self.VIEW_SINGLE_PAGE:
					self.__decide_page_change(vadj, Gdk.ScrollDirection.UP)
		elif key == "Page_Down":
			if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
				self.go_to_page(1, True)
			else:
				# We do it manually... should be in a method
				vadj = self.get_vadjustment()
				vadj.set_value(min(vadj.upper - vadj.page_size, vadj.value + vadj.page_increment))
				if self.__type_of_view == self.VIEW_SINGLE_PAGE:
					self.__decide_page_change(vadj, Gdk.ScrollDirection.DOWN)
		elif key == "Home":
			if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
				self.go_to_page(0)
			else:
				vadj = self.get_vadjustment()
				vadj.set_value(vadj.lower)
		elif key == "End":
			if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
				self.go_to_page(-1)
			else:
				vadj = self.get_vadjustment()
				vadj.set_value(vadj.upper - vadj.page_size)
		else:
			return False
			
		return True
		
		
	def __create_scrolled_window(self):
		"""
		Creates the scrolled window that will contain the pages.
		"""
		
		scrolled_window = Gtk.ScrolledWindow()
		scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self.__panel.pack_start(scrolled_window, True, True, 0)

		# the VBox inside the scrolled window, that will contain the pages
		pages = Gtk.VBox(spacing=2) # here we ask for a padding equal to 2

		# pack the VBox in an EventBox to be able to receive 
		# events like "button-release-event" and "motion-notify-event"
		event_box = Gtk.EventBox()
		event_box.add(pages)
		scrolled_window.add_with_viewport(event_box)

		vadj = scrolled_window.get_vadjustment()
		hadj = scrolled_window.get_hadjustment()

		self.__vadj_changed_id = vadj.connect('changed', self.__on_vert_adj_changed)
		self.__vadj_value_id = vadj.connect("notify::value", self.__on_vert_adj_value_changed)

		self.__hadj_changed_id = hadj.connect('changed', self.__on_horiz_adj_changed)
		self.__hadj_value_id = hadj.connect("notify::value", self.__on_horiz_adj_value_changed)
		
		
	def __update_scrolled_window(self, event):
		"""
		Creates all visible elements on the panel, cleaning it
		from previous existing elements first.
		If resize_only == True, then only resize the drawing areas.
		"""
		
		try: # try to create a preview for the document
			self.__create_preview_panel(event)
		except Exception, exc: # if unable, then show a default document view
			self._log.warning("Error while creating preview panel: %s, %s, %s" % (type(exc), exc, exc.args))
			self._log.warning("Creating default panel")
			if not self.__document is None:
				# to prevent a possible crash due to ctypes trying to free memory not allocated
				self.__document.document_loaded = False
			self.__create_default_panel()

	
	@property
	def file_path(self):
		return self.__compiled_file_path
		
		
	def update_file_path(self, file_path):
		"""
		Updates the file path of the compiled document.
		Called by LatexPreview.update_file_path() on "Save as...".
		"""
		
		self.__compiled_file_path = file_path
		self.__update_scrolled_window(self.EVENT_UPDATE_FILE)
		
		
	def __check_changes(self):
		"""
		Check the compiled file for the last modification time and call for
		preview redraw it file has a more recent modification timestamp
		@return: True so that the method will be called again by GObject.timeout_add
		"""
		
		TIMES = 3
		
		# A hack again: self.__file_update_count is there to make sure 
		# that the file hasn't been modified since at least TIMES times 
		# the time between two calls of this method, so that we're 
		# pretty sure that compilation is finished. 
		#
		# (For example, we check for a file change every 250 ms. 
		# If the file has not changed for 4 times 250 ms, we assume 
		# that compilation is finished. Although this sums up to 
		# 1 second, this is finer than checking 1 time after 1 second, 
		# because in the latter case, it may take up to 2 seconds 
		# to be sure that we can update, whereas for the former 
		# it takes up to 1.25 second. The interval of 1 second is 
		# arbitrary, but with a shorter one, we face the problem that 
		# when the compilation process involves bibtex or other 
		# programs, the main output doesn't change while the 
		# auxiliary files are updated (.toc, .aux, etc.), so we could 
		# think that compilation is finished although it is not, and 
		# end up with a broken output file.)
		try:
			file_time = os.path.getmtime(self.__compiled_file_path)
			if self.__last_update_time < file_time:
				self.__file_update_count = TIMES
				self.__last_update_time = file_time
			elif self.__file_update_count > 0:
				self.__file_update_count -= 1
				if self.__file_update_count == 0: 
					self.__update_scrolled_window(self.EVENT_UPDATE_FILE)
			return True
		except:
			return True


	def __on_horiz_adj_value_changed(self, adj, scroll):
		"""
		Called when the value of the horizontal scrollbar is changed. 
		Saves that value to be able to restore it after a zoom in/out.
		"""
		
		if adj.page_size > 50:
			self.__last_horizontal_scroll_position = adj.value
			self.__last_horizontal_scroll_page_size = adj.page_size
		else:
			self.__last_horizontal_scroll_position = None


	def __on_horiz_adj_changed(self, adj):
		"""
		Called when any property of the horizontal scrollbar other 
		than the value is changed. Uses the value stored in 
		self.__last_horizontal_scroll_position (by 
		self.__on_horiz_adj_value_changed(), self.zoom_in/out()) 
		to scroll to the previous position after a zoom in/out or a 
		refresh.
		"""
				
		zoom_type = self.get_zoom_type()
		if zoom_type == self.ZOOM_FIT_WIDTH:
			self.zoom_fit_width()
		elif zoom_type == self.ZOOM_FIT_PAGE:
			self.zoom_fit_page()

		if self.__last_horizontal_scroll_position == None:
			total = adj.upper - adj.lower - adj.page_size - 2 * self.__shadow_thickness * self.__scale
			adj.value = max(0.0, adj.lower + total / 2)
		else:
			new_value = self.__last_horizontal_scroll_position - (adj.page_size - self.__last_horizontal_scroll_page_size) / 2
			if new_value < adj.lower:
				adj.value = adj.lower
			elif new_value > adj.upper - adj.page_size:
				adj.value = adj.upper - adj.page_size
			else:
				adj.value = new_value


	def __on_vert_adj_value_changed(self, adj, scroll):
		"""
		Called when the value of the vertical scrollbar is changed. 
		Saves that value to be able to restore it after a zoom in/out
		or after toggling continuous/single page type of view.
		"""

		self.__last_vertical_scroll_position = adj.value


	def __on_vert_adj_changed(self, adj):
		"""
		Called when any property of the vertical scrollbar other 
		than the value is changed. Uses the value stored in 
		self.__last_vertical_scroll_position (by 
		self.__on_vert_adj_value_changed(), self.zoom_in/out(), or
		self.toggle_continuous()) to scroll to the previous 
		position after a zoom in/out or after toggling 
		continuous/single page type of view.
		"""

		zoom_type = self.get_zoom_type()
		if zoom_type == self.ZOOM_FIT_PAGE:
			self.zoom_fit_page()

		if self.__last_vertical_scroll_position < (adj.upper - adj.page_size):
			adj.set_value(self.__last_vertical_scroll_position)
			

	def __update_drawing_area(self, dwg, i, j, default, event):
		"""
		Does the tasks that __create_page and __update_page have in common.
		@param dwg: the drawing area to update
		@param i: the index of dwg in self.__drawing_areas
		@param j: the index in self.__document of the page to render on dwg
		@param default: True if default panel, False if not
		"""
		
		if default: # default panel
			if event != self.EVENT_RESIZE:
				if i in self.__expose_id:
					dwg.disconnect(self.__expose_id[i])
				self.__expose_id[i] = dwg.connect("expose-event", self.__on_expose_default)
			# TODO: If there was a preview panel before, maybe we 
			# should keep the old sizes. But as the preview panel had a 
			# problem (since we ended up in the default panel), maybe 
			# these lengths are bad...
			(self.__page_width[i], self.__page_height[i]) = (595, 842)
		else: # preview panel
			if event != self.EVENT_RESIZE:
				if i in self.__expose_id:
					dwg.disconnect(self.__expose_id[i])
				self.__expose_id[i] = dwg.connect("expose-event", self.__on_expose, i, j)
			(self.__page_width[i], self.__page_height[i]) = self.__document.get_page_size(j)

		dwg.set_size_request(int((self.__page_width[i] + 2 * self.__shadow_thickness) * self.__scale), 
							 int((self.__page_height[i] + 2 * self.__shadow_thickness) * self.__scale))

		# Save each page's position in the scrolled_window for the popup 
		# menu "Next/Previous page". Actually it is the page position 
		# minus the padding, so that self.__page_position[i] is exactly 
		# between the end of page i-1 (2 pixels higher) and the 
		# beginning page i (2 pixels lower).
		if i == 0:
			self.__page_position[i] = 0
		else:
			# don't forget to take the padding into account (+ 4)
			self.__page_position[i] = self.__page_position[i-1] + int((self.__page_height[i-1] + 2 * self.__shadow_thickness) * self.__scale) + 4

		
	def __create_page(self, i, j, pages, default):
		"""
		Creates a drawing area at index i in self.__drawing_areas, to 
		render page j of self.__document, and adds it to the VBox pages.
		@param i: the index in self.__drawing_areas
		@param j: the index in self.__document of the page to render
		@param pages: the VBox containing the (alignments containging the) drawing areas
		@param default: True if default panel, False if not
		"""
		
		dwg = Gtk.DrawingArea()
		self.__drawing_areas[i] = dwg

		self.__update_drawing_area(dwg, i, j, default, False)
		
		fixed = Gtk.Fixed()
		fixed.put(dwg, 0, 0)

		self.__links[i] = []
		if not default:
			page_links = self.__document.get_page_links(j)
			for doc_link in page_links:
				link = PreviewLink(self, doc_link)
				self.__links[i].append(link)
				x, y = int(doc_link.x1 * self.__scale), int(doc_link.y1 * self.__scale)
				fixed.put(link, x, y)

		# keep the page in the (horizontal) middle of the scrolled window
		align = Gtk.Alignment.new(0.5, 0.5, 0, 0)
		# if in single page type of view, center the page vertically
		expand = (self.__type_of_view == self.VIEW_SINGLE_PAGE)
		pages.pack_start(align, expand, False, 1)
		
		align.add(fixed)
		
		self._log.debug("Created drawing area %d for page %d" % (i, j))
		
		
	def __update_page(self, i, j, pages, default, event):
		"""
		Updates the drawing area at index "i" in self.__drawing_areas, 
		to render page "j" of self.__document, and add it to the VBox "pages".
		@param i: the index in self.__drawing_areas
		@param j: the index in self.__document of the page to render
		@param pages: the VBox containing the (alignments containging the) drawing areas
		@param default: True if default panel, False if not
		"""
		
		dwg = self.__drawing_areas[i]

		self.__update_drawing_area(dwg, i, j, default, event)
		
		if event == self.EVENT_RESIZE:
			for link in self.__links[i]:
				x, y = int(link.doc_link.x1 * self.__scale), int(link.doc_link.y1 * self.__scale)
				link.get_parent().move(link, x, y)
				link.update()
		else:
			fixed = dwg.get_parent()
			
			for link in self.__links[i]:
				link.destroy()
				fixed.remove(link)
				del link
			self.__links[i] = []
			
			if not default:
				page_links = self.__document.get_page_links(j)
				for doc_link in page_links:
					link = PreviewLink(self, doc_link)
					self.__links[i].append(link)
					x, y = int(doc_link.x1 * self.__scale), int(doc_link.y1 * self.__scale)
					fixed.put(link, x, y)
		
		if event == self.EVENT_TOGGLE_CONTINUOUS:
			# if in single page type of view, center the page vertically
			expand = (self.__type_of_view == self.VIEW_SINGLE_PAGE) # True if in single page
			pages.set_child_packing(dwg.get_parent().get_parent(), expand, False, 1, Gtk.PACK_START)
		
		self._log.debug("Updated drawing area %d for page %d" % (i, j))


	def __delete_last_page(self, pages):
		"""
		Deletes the last drawing_area from the VBox "pages".
		@return: False if there was no drawing area to delete, True else.
		"""
		
		last = len(self.__drawing_areas) - 1
		if last == -1:
			return False
		
		self.__drawing_areas[last].disconnect(self.__expose_id[last])

		# Remove links, if any
		fixed = self.__drawing_areas[last].get_parent()
		for link in self.__links[last]:
			link.destroy()
			fixed.remove(link)
			del link
		del self.__links[last]

		# The drawing areas are contained in Fixed, which are contained 
		# in Alignments, which are contained in the VBox "pages". 
		# We thus have to remove the alignments.
		pages.remove(self.__drawing_areas[last].get_parent().get_parent())
		
		del self.__expose_id[last]
		del self.__drawing_areas[last]
		
		self._log.debug("Deleted last drawing area (index %d)" % last)

		
	
	def __get_mean_page_size(self):
		"""
		Computes the mean size of a drawing area.
		"""
		
		# The mean size taken by a page in the scrolled window
		n = len(self.__drawing_areas)
		if n == 0:
			return 0
		elif n == 1:
			penultimate_position = 0
		else:
			penultimate_position = self.__page_position[n-1]
		mean_page_size = (penultimate_position + int((self.__page_height[n-1] + 2 * self.__shadow_thickness) * self.__scale) + 4)/n
		
		return mean_page_size
		

	def __create_default_panel(self):
		"""
		Creates a default document view.
		"""
		
		if self.__mouse_handlers != []:
			self.__disconnect_mouse_events()
		if not self.__document is None:
			self.__document = None

		scrolled_window = self.get_scrolled_window()
		viewport = scrolled_window.get_children()[0]
		eventbox = viewport.get_children()[0]
		pages = eventbox.get_children()[0]

		old_n = len(pages.get_children())
		
		if old_n == 0: # we should really create the page
			self.__create_page(0, self.__current_page, pages, True)
		else: # we should update the first page and delete the others
			self.__update_page(0, self.__current_page, pages, True, False)
			for i in range(old_n - 1):
				self.__delete_last_page(pages)
		
		self.__mean_page_size = self.__get_mean_page_size()
		
		scrolled_window.show_all()
		scrolled_window.queue_draw()


	def __create_preview_panel(self, event):
		"""
		Creates a view of all document pages.
		"""
		
		if self.__mouse_handlers == []:
			self.__connect_mouse_events()		
		
		if event in [self.EVENT_CREATE, self.EVENT_UPDATE_FILE] or self.__document == None:
			self.__document = PreviewDocument(self.__compiled_file_path)
			if self.__document == None or not self.__document.document_loaded:
				# TODO: Raise our own exception
				raise Exception, "Error when opening the output file %s" % self.__compiled_file_path
			self.__last_update_time = os.path.getmtime(self.__compiled_file_path)

		old_n = len(self.__drawing_areas)
		new_n = self.__document.get_n_pages()
		
		# get the VBox containing all the pages
		scrolled_window = self.get_scrolled_window()
		viewport = scrolled_window.get_children()[0]
		eventbox = viewport.get_children()[0]
		pages = eventbox.get_children()[0]
		
		zoom_type = self.get_zoom_type()
		if zoom_type == self.ZOOM_FIT_WIDTH:
			if self.DELAY_ZOOM:
				scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
			else:
				scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
			self.__scale = self.__get_fit_width_scale()
		elif zoom_type == self.ZOOM_FIT_PAGE and self.__type_of_view == self.VIEW_SINGLE_PAGE:
			scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
			#~ scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
			self.__scale = self.__get_fit_page_scale()
		elif zoom_type == self.ZOOM_FIT_PAGE and self.__type_of_view == self.VIEW_CONTINUOUS:
			scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
			self.__scale = self.__get_fit_page_scale()			
		else:
			scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
			
		# create or update all document pages, 
		# or only one if in "single page" type of view
		if self.__type_of_view == self.VIEW_CONTINUOUS: # continuous
			for i in range(min(old_n, new_n)):
				self.__update_page(i, i, pages, False, event)
			for i in range(new_n - old_n):
				self.__create_page(old_n + i, old_n + i, pages, False)
			for i in range(old_n - new_n):
				self.__delete_last_page(pages)
		else: # single page
			if old_n == 0:
				self.__create_page(0, self.__current_page, pages, False)
			else:
				self.__update_page(0, self.__current_page, pages, False, event)
				for i in range(old_n - 1):
					self.__delete_last_page(pages)

		self.__mean_page_size = self.__get_mean_page_size()

		if event in [self.EVENT_CREATE, self.EVENT_UPDATE_FILE]:
			if self.__magnifying_glass != None:
				self.__magnifying_glass.destroy()
				self.__magnifying_glass = None
			self.__magnifying_glass = MagnifyingGlass(self.__scale, self.__document)
		elif event in [self.EVENT_RESIZE]:
			self.__magnifying_glass.set_preview_scale(self.__scale)
		
		scrolled_window.show_all()
		scrolled_window.queue_draw()
		
		
	def get_panel(self):
		"""
		Returns the current panel available for display.
		@return: the current panel available for display
		"""
		
		return self.__panel


	def get_scrolled_window(self):
		"""
		Returns the scrolled window containing the preview.
		@return: the scrolled window containing the preview
		"""
		
		return self.__panel.get_children()[0]
		
	
	def get_vadjustment(self):
		"""
		Returns the vertical adjustment of the scrolled window 
		containing the preview.
		"""
		
		scrolled_window = self.get_scrolled_window()
		return scrolled_window.get_vadjustment()
		
		
	def get_hadjustment(self):
		"""
		Returns the horizontal adjustment of the scrolled window 
		containing the preview.
		"""
		
		scrolled_window = self.get_scrolled_window()
		return scrolled_window.get_hadjustment()
		
		
	def __on_expose(self, widget, event, i, j):
		"""
		Redraws a portion of the document area that is exposed.
		@param widget: 
		@param event: 
		@param i: page index in self.__drawing_areas
		@param j: page to render, i.e. page index in self.__document
		"""
		
		cr = self.__initialize_cairo_page(widget, event, i)
		self.__document.render_page(cr, j)
		self.__create_page_border(cr, i)
		
		self.__sync_rectangle.draw(cr, j)


	def __on_expose_default(self, widget, event):
		"""
		Redraws a portion of the default document area that is exposed.
		"""
		
		cr = self.__initialize_cairo_page(widget, event, 0)
		self.__create_page_border(cr, 0)
		
		# draw the default message in the center of the page
		cr.set_source_rgb(0.5, 0.5, 0.5)
		cr.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
		cr.set_font_size(32)
		x_bearing, y_bearing, width, height = cr.text_extents(self.__no_preview_message)[:4]
		cr.move_to((self.__page_width[0] / 2) - width / 2 - x_bearing, (self.__page_height[0] / 2) - height / 2 - y_bearing)
		cr.show_text(self.__no_preview_message)


	def __on_button_press(self, widget, event):
		"""
		Called when a mouse button is pressed in the scrolled window.
		Starts dragging the view if button 2, pops up a menu if 
		button 3.
		"""
		
		if event.type != Gdk.EventType.BUTTON_PRESS:
			return False

		self.__panel.grab_focus()
 
		if event.button == 1:
			x = event.x
			y = event.y
			
			if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
				self.__sync_edit(x,y)
			else:
				self.__glass_drag.start(self.__magnifying_glass, x, y)

			return True
			
		elif event.button == 2:
			scrolled_window = self.get_scrolled_window()

			hscroll = scrolled_window.get_hadjustment().value
			vscroll = scrolled_window.get_vadjustment().value
			
			x = event.x - hscroll
			y = event.y - vscroll

			self.__preview_drag.start(hscroll, vscroll, x, y)
			
			return True

		elif event.button == 3:
			popup_menu = Gtk.Menu()

			#TODO: Set labels manually.
			menu_zoom_in = Gtk.ImageMenuItem(Gtk.STOCK_ZOOM_IN)
			popup_menu.add(menu_zoom_in)
			menu_zoom_in.connect_object("event", self.__on_popup_clicked, "zoom_in", event.time)

			menu_zoom_out = Gtk.ImageMenuItem(Gtk.STOCK_ZOOM_OUT)
			popup_menu.add(menu_zoom_out)
			menu_zoom_out.connect_object("event", self.__on_popup_clicked, "zoom_out", event.time)
			
			menu_previous_page = Gtk.ImageMenuItem(Gtk.STOCK_GO_UP)
			popup_menu.add(menu_previous_page)
			menu_previous_page.connect_object("event", self.__on_popup_clicked, "previous_page", event.time)
			
			menu_next_page = Gtk.ImageMenuItem(Gtk.STOCK_GO_DOWN)
			popup_menu.add(menu_next_page)
			menu_next_page.connect_object("event", self.__on_popup_clicked, "next_page", event.time)
			
			menu_continuous = Gtk.CheckMenuItem("Continuous")
			popup_menu.add(menu_continuous)
			menu_continuous.connect_object("event", self.__on_popup_clicked, "continuous", event.time)

			menu_properties = Gtk.MenuItem("Properties...")
			popup_menu.add(menu_properties)
			menu_properties.connect_object("event", self.__on_popup_clicked, "properties", event.time)
			
			menu_reload = Gtk.MenuItem("Reload")
			popup_menu.add(menu_reload)
			menu_reload.connect_object("event", self.__on_popup_clicked, "reload", event.time)			
			
			menu_open = Gtk.MenuItem("Open in default viewer")
			popup_menu.add(menu_open)
			menu_open.connect_object("event", self.__on_popup_clicked, "open", event.time)
			
			if self.__type_of_view == self.VIEW_CONTINUOUS:
				menu_continuous.set_active(True)
			else:
				menu_continuous.set_active(False)
			
			popup_menu.show_all()
			popup_menu.popup(None, None, None, event.button, event.time)

			return True
			
		return False


	def __on_motion(self, widget, event):
		"""
		Called when the mouse moves and a button is pressed.
		Saves the position of the mouse during dragging and queue the 
		actual move of the view for an idle time.
		"""
		
		if self.__preview_drag.is_in_drag():
			scrolled_window = self.get_scrolled_window()

			hadj = scrolled_window.get_hadjustment()
			vadj = scrolled_window.get_vadjustment()
			
			x = event.x - hadj.value
			y = event.y - vadj.value

			self.__preview_drag.update(x, y)
			
		elif self.__magnifying_glass.is_shown():
			root_window = widget.get_screen().get_root_window()
			root_x, root_y, mods = root_window.get_pointer()

			x = event.x
			y = event.y
			
			self.__glass_drag.update(root_x, root_y, x, y)

		return False


	def __on_button_release(self, widget, event):
		"""
		Called when a mouse button is released after having been
		clicked in the scrolled window. Ends the drag or the magnifying 
		glass.
		"""
		
		if self.__preview_drag.is_in_drag():
			self.__preview_drag.stop()
		
		if self.__glass_drag.is_in_drag():
			self.__glass_drag.stop()
			
		return False


	def set_cursor(self, curs):
		"""
		Sets the cursor visible or invisible according to the variable 
		"visible" being True or False, and if visible, sets the cursor 
		to a hand if in_drag is True.
		"""
		
		if curs == self.CURSOR_EMPTY:
			cursor = self.__cursor_empty
		elif curs == self.CURSOR_DRAG:
			cursor = self.__cursor_drag
		elif curs == self.CURSOR_LINK:
			cursor = self.__cursor_link
		else:
			cursor = self.__cursor_default
		
		self.get_scrolled_window().window.set_cursor(cursor)

	
	def __on_popup_clicked(self, widget, event, time):
		"""
		Called when a popup menu item is clicked on.
		"""
		
		# the test on the time is there only to circumvent a strange behaviour: 
		# when right clicking and releasing directly the button, the first 
		# menu item is "activated" (i.e. clicked) AND the menu stays open...
		#TODO: Find out why this doesn't happen in other programs, and fix this properly.
		if event.type == Gdk.BUTTON_RELEASE and event.time - time > 200:
			if widget == "zoom_in":
				self.zoom_in()
			elif widget == "zoom_out":
				self.zoom_out()
			elif widget == "previous_page":
				self.go_to_page(-1, True)
			elif widget == "next_page":
				self.go_to_page(1, True)
			elif widget == "continuous":
				self.toggle_continuous()
			elif widget == "properties":
				self.__properties_dialog = DocumentPropertiesDialog(self.__document)
			elif widget == "reload":
				self.__update_scrolled_window(self.EVENT_UPDATE_FILE)
			elif widget == "open":
				self.__document.open_in_external_viewer()
		return False


	def __on_scroll(self, scrolled_window, event):
		"""
		Monitors the scroll events, to go to next/previous page when 
		in single page type of view and the user scrolls further 
		as he already reached the end of the view.		
		In addition, Ctrl+Scroll triggers zoom in/out, and Alt+Scroll
		triggers Next/Previous page.
		"""

		if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
			if event.direction == Gdk.ScrollDirection.DOWN:
				self.zoom_out()
				return True
			elif event.direction == Gdk.ScrollDirection.UP:
				self.zoom_in()
				return True
		elif event.get_state() & Gdk.ModifierType.MOD1_MASK:
			if event.direction == Gdk.ScrollDirection.DOWN:
				self.go_to_page(1, True)
				return True
			elif event.direction == Gdk.ScrollDirection.UP:
				self.go_to_page(-1, True)
				return True

		if self.__type_of_view == self.VIEW_SINGLE_PAGE:
			vadj = scrolled_window.get_vadjustment()
			if (self.__decide_page_change(vadj, event.direction)):
				# If we changed page, return True so that we don't take 
				# into account the last scroll (that triggered the page 
				# change), to prevent scrolling further on the new page.
				return True
		
		return False
				

	def __decide_page_change(self, vadj, direction):
		"""
		According to vadj.value, direction, and 
		self.__scroll_up/down_count, decide wether to change page 
		or not. 
		Two mouse wheel "clicks" are necessary to go to next/previous 
		page.
		Only one is needed when it does fit.
		See self.__on_scroll() for more	information.
		@return: True if we changed page, False if not.
		"""
		
		if vadj.lower == vadj.upper - vadj.page_size:
			max_scroll_count = 1
		else:
			max_scroll_count = 2
		
		if vadj.value == vadj.lower and direction == Gdk.ScrollDirection.UP and self.__current_page != 0:
			self.__scroll_up_count += 1
			if self.__scroll_up_count == max_scroll_count:
				self.go_to_page(-1, True)
				self.__scroll_up_count = 0
				self.__last_vertical_scroll_position = vadj.upper - vadj.page_size
				vadj.value = vadj.upper - vadj.page_size
				return True
		elif vadj.value == vadj.upper - vadj.page_size and direction == Gdk.ScrollDirection.DOWN and self.__current_page != self.__document.get_n_pages() - 1:
			self.__scroll_down_count += 1
			if self.__scroll_down_count == max_scroll_count:
				self.go_to_page(1, True)
				self.__scroll_down_count = 0
				self.__last_vertical_scroll_position = vadj.lower
				vadj.value = vadj.lower
				return True
		else:
			self.__scroll_up_count = 0
			self.__scroll_down_count = 0
		
		return False


	def __initialize_cairo_page(self, widget, event, i):
		"""
		Initializes cairo to draw in the given widget, and draws the 
		background and the shadow of page "i".
		"""
		
		cr = widget.window.cairo_create()
		
		# do not draw too much for nothing
		region = Gdk.region_rectangle(event.area)
		cr.region(region)
		cr.clip()
		
		# set the zoom factor for the whole drawing
		cr.scale(self.__scale, self.__scale)

		# shadow (must be under the rest of the drawing)
		st = self.__shadow_thickness
		cr.set_line_width(st)
		cr.set_source_rgb(0.4, 0.4, 0.4)
		cr.move_to(self.__page_width[i] + 0.5 + st / 2, st)
		cr.line_to(self.__page_width[i] + 0.5 + st / 2, self.__page_height[i] + st / 2)
		cr.line_to(st, self.__page_height[i] + st / 2)
		cr.stroke()

		# background
		cr.set_source_rgb(1, 1, 1)
		cr.rectangle(0, 0, self.__page_width[i], self.__page_height[i])
		cr.fill()
		
		return cr


	def __create_page_border(self, cr, i):
		"""
		Method that draws a border around the document page.
		"""

		# border (strangely, the white background is 1 pixel wider 
		# than self.__page_width[i] * self.__scale, so we draw the right border 
		# one pixel further to the right)
		cr.set_line_width(1 / self.__scale)
		
		cr.set_source_rgb(0, 0, 0)
		cr.rectangle(0, 0, self.__page_width[i] + 1 / self.__scale, self.__page_height[i])
		cr.stroke()

	
	def __get_fit_width_scale(self):
		hadj = self.get_hadjustment()
		avail_width = hadj.page_size
		doc_width = self.__page_width[0] + 2 * self.__shadow_thickness + 4
		
		return avail_width / doc_width
		
		
	def __get_fit_page_scale(self):
		hadj = self.get_hadjustment()
		vadj = self.get_vadjustment()
		avail_width = hadj.page_size
		avail_height = vadj.page_size
		doc_width = self.__page_width[0] + 2 * self.__shadow_thickness + 4
		doc_height = self.__page_height[0] + 2 * self.__shadow_thickness + 4
		
		return min(avail_width / doc_width, avail_height / doc_height)
		
		
	def __get_scale_pos(self, scale):
		"""
		Method that gets the position i in self.__scale_list such that 
		scale is between self.__scale_list[i] and 
		self.__scale_list[i+1].
		"""
		
		pos = 0
		last = len(self.__scale_list) - 1
		for i in range(last):
			if self.__scale_list[i] <= scale and scale < self.__scale_list[i+1]:
				pos = i
		if scale >= self.__scale_list[last]:
			pos = last
				
		return pos
		
		
	def __get_next_scale(self):
		"""
		Method that computes the next scale in the scale list, with
		Fit width and Fit page inserted at the right positions.
		"""
		
		scale = self.__scale
		zoom_type = self.__zoom_type
		pos = self.__get_scale_pos(scale)
		last = len(self.__scale_list) - 1
		
		if pos == last:
			return scale, zoom_type
		
		fit_width = self.__get_fit_width_scale()
		fit_page = self.__get_fit_page_scale()
		
		fit_width_candidate = False
		fit_page_candidate = False
		if scale < fit_width and fit_width < self.__scale_list[pos+1]:
			fit_width_candidate = True
		if scale < fit_page and fit_page < self.__scale_list[pos+1]:
			fit_page_candidate = True
		
		if fit_width_candidate and fit_page_candidate:
			if fit_width <= fit_page:
				return fit_width, self.ZOOM_FIT_WIDTH
			else:
				return fit_page, self.ZOOM_FIT_PAGE
		elif fit_width_candidate:
			return fit_width, self.ZOOM_FIT_WIDTH
		elif fit_page_candidate:
			return fit_page, self.ZOOM_FIT_PAGE
		else:
			return self.__scale_list[pos+1], self.ZOOM_NORMAL

		
	def __get_previous_scale(self):
		"""
		Method that computes the previous scale in the scale list, with
		Fit width and Fit page inserted at the right positions.
		"""
		
		scale = self.__scale
		pos = self.__get_scale_pos(scale)
		first = 0
		if scale == self.__scale_list[first]:
			return scale, self.ZOOM_NORMAL
		if scale == self.__scale_list[pos]:
			pos -= 1
				
		fit_width = self.__get_fit_width_scale()
		fit_page = self.__get_fit_page_scale()
		
		fit_width_candidate = False
		fit_page_candidate = False
		if scale > fit_width and fit_width > self.__scale_list[pos]:
			fit_width_candidate = True
		if scale > fit_page and fit_page > self.__scale_list[pos]:
			fit_page_candidate = True
		
		if fit_width_candidate and fit_page_candidate:
			if fit_width > fit_page:
				return fit_width, self.ZOOM_FIT_WIDTH
			else:
				return fit_page, self.ZOOM_FIT_PAGE
		elif fit_width_candidate:
			return fit_width, self.ZOOM_FIT_WIDTH
		elif fit_page_candidate:
			return fit_page, self.ZOOM_FIT_PAGE
		else:
			return self.__scale_list[pos], self.ZOOM_NORMAL


	def get_zoom_type(self):
		return self.__zoom_type
			
		
	def set_zoom_type(self, zoom_type):
		self.__zoom_type = zoom_type
		self._preferences.set("PdfPreviewZoomType", zoom_type)


	def zoom_to(self, scale, zoom_type):
		"""
		Method that zooms the preview from old_scale to scale.
		"""

		self.__new_scale = scale
		self.__new_zoom_type = zoom_type
		if self.DELAY_ZOOM:
			self.__zoom_to_id = GObject.idle_add(self.__do_zoom_to)
		else:
			self.__do_zoom_to()
		
	
	def __do_zoom_to(self):
		scale = self.__new_scale
		zoom_type = self.__new_zoom_type
		old_scale = self.__scale
		old_zoom_type = self.__zoom_type
		
		self.set_zoom_type(zoom_type)
		if zoom_type == self.ZOOM_FIT_WIDTH:
			scale = self.__get_fit_width_scale()
		elif zoom_type == self.ZOOM_FIT_PAGE:
			scale = self.__get_fit_page_scale()

		if old_scale == scale:
			return

		self.__scale = scale
		self._preferences.set("PdfPreviewScale", scale)
		
		# Save the horizontal scroll position before initializing
		# and restore it after, to prevent the document from being centered
		# if it was not before
		hadj = self.get_hadjustment()
		last_pos = hadj.value
		last_size = hadj.page_size		
		last_upper = hadj.upper
		last_lower = hadj.lower

		# Keep the vertical scrollbar at the same position in the document
		# up to the error due to the space between the pages, which is not scaled
		vertical_scroll_position = self.__last_vertical_scroll_position * scale / old_scale
		self.__last_vertical_scroll_position = vertical_scroll_position

		self.__update_scrolled_window(self.EVENT_RESIZE)
		
		# If there was no horizontal scroll bar before zooming in, center the document
		if last_upper - last_lower == last_size and scale > old_scale:
			self.__last_horizontal_scroll_position = None
		else:
			# Keep the center of the view centered after zooming
			self.__last_horizontal_scroll_position = max(0.0, ((last_pos + (last_size / 2)) * (scale / old_scale)) - (hadj.page_size / 2))
			self.__last_horizontal_scroll_page_size = last_size
			
		return False # to execute the method only once even if queued many times
		

	def zoom_in(self):
		"""
		Method that zooms in the pdf preview.
		"""

		scale, zoom_type = self.__get_next_scale()
		self.zoom_to(scale, zoom_type)


	def zoom_out(self):
		"""
		Method that zooms out the pdf preview.
		"""

		scale, zoom_type = self.__get_previous_scale()
		self.zoom_to(scale, zoom_type)


	def zoom_fit_width(self):
		
		scale = self.__get_fit_width_scale()
		self.zoom_to(scale, self.ZOOM_FIT_WIDTH)

		
	def zoom_fit_page(self):
		
		scale = self.__get_fit_page_scale()
		self.zoom_to(scale, self.ZOOM_FIT_PAGE)

		
	def scroll_up(self):
		"""
		Method that scrolls up the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		event = Gdk.Event(Gdk.SCROLL)
		event.direction = Gdk.ScrollDirection.UP
		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-event", event)


	def scroll_down(self):
		"""
		Method that scrolls down the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		event = Gdk.Event(Gdk.SCROLL)
		event.direction = Gdk.ScrollDirection.DOWN
		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-event", event)


	def scroll_left(self):
		"""
		Method that scrolls down the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		event = Gdk.Event(Gdk.SCROLL)
		event.direction = Gdk.ScrollDirection.LEFT
		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-event", event)


	def scroll_right(self):
		"""
		Method that scrolls down the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		event = Gdk.Event(Gdk.SCROLL)
		event.direction = Gdk.ScrollDirection.RIGHT
		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-event", event)


	def get_free_horiz_space(self, page_index):
		"""
		Method that computes the free space available between the left 
		border of the scrolled window and the left border of the 
		drawing area with index "page_index".
		"""
		
		adj = self.get_hadjustment()
		scrolled_window_width = adj.upper - adj.lower
		drawing_area_width = (self.__page_width[page_index] + 2 * self.__shadow_thickness) * self.__scale
		return (scrolled_window_width - drawing_area_width) / 2
		
		
	def get_free_vert_space(self):
		"""
		Method that computes the free space available between the top 
		border of the scrolled window and the top border of the first
		drawing area.
		"""
		
		adj = self.get_vadjustment()
		scrolled_window_height = adj.upper - adj.lower
		
		# The variables self._page_position[i] give the y value which 
		# is exactly in the middle of the free space between drawing 
		# area i-1 and drawing area i. That is, the real page position 
		# is self.__page_position[i] + the padding, which is equal to 2 
		# here.
		if self.__type_of_view == self.VIEW_CONTINUOUS: # continuous
			n = self.__document.get_n_pages()
			drawing_areas_height = (self.__page_position[n-1] - 2) + (self.__page_height[n-1] + 2 * self.__shadow_thickness) * self.__scale + 2
		else: # single page
			n = 1
			drawing_areas_height = (self.__page_height[0] + 2 * self.__shadow_thickness) * self.__scale
			
		return (scrolled_window_height - drawing_areas_height) / 2
		
		
	def get_page_and_position_from_pointer(self, x, y):
		"""
		Method that computes the page number and the coordinates in 
		that page (at scale 1), given the coordinates of the mouse 
		pointer in the scrolled window.
		"""
		
		scrolled_window = self.get_scrolled_window()
		hadj = scrolled_window.get_hadjustment()
		vadj = scrolled_window.get_vadjustment()

		if self.__type_of_view == self.VIEW_CONTINUOUS: # continuous
			page_index = self.get_page_at_position(y)
			page_to_render = page_index
		else: # single page
			page_index = 0
			page_to_render = self.__current_page

		free_left_space = self.get_free_horiz_space(page_index)
		free_top_space = self.get_free_vert_space()
		x_in_page = (x - free_left_space) / self.__scale
		y_in_page = (y - (self.__page_position[page_index] + 2) - free_top_space) / self.__scale # 2 is for the padding

		return page_to_render, x_in_page, y_in_page
		
		
	def get_page_at_position(self, position):
		"""
		Method that computes the number of the page at vertical scroll 
		position "position".
		"""
		
		if self.__document is None:
			return 0
		
		# Make a first guess for the page number, 
		# using the mean size of a page in this document
		page = int(position / self.__mean_page_size)
		n = self.__document.get_n_pages()
		if page > n - 1:
			page = n - 1
			
		while not ((page == 0 or self.__page_position[page] <= position) and (page == (n - 1) or self.__page_position[page+1] >= position)):
			if self.__page_position[page] > position:
				page -= 1
			else:
				page += 1

		return page
		

	def get_current_page(self):
		"""
		Method that computes the current page number.
		If in single page type of view, returns the value of 
		self.__current_page.
		If in continuous type of view, reads the vertical scroll 
		position and returns the number of the page which is at that 
		precise position in the scrolled window. 
		This means that if a tenth of page n is displayed at the top 
		and the rest of the view shows page n+1, this method returns n,
		and not n+1, because the first pixel of the view shows page n.
		"""
		
		if self.__type_of_view == self.VIEW_CONTINUOUS: # continuous
			adj = self.get_vadjustment()
			current_pos = adj.value			
			return self.get_page_at_position(current_pos)
		else: # single page
			return self.__current_page
			
			
	def go_to_page(self, page, relative = False):
		"""
		Method that moves the view to a given page. If relative is 
		False, and page is negative, go to (n - page) where n is the 
		total number of pages.
		@param page: the number of the page to go to
		@param relative: True if parameter "page" is relative to the current page number, False if parameter "page" is the absolute page number
		"""
		
		if self.__document == None:
			return

		if relative:
			current_page = self.get_current_page()
			new_page = current_page + page
		else:
			if page < 0:
				page = self.__document.get_n_pages() + page
			new_page = page
			
		if new_page < 0:
			new_page = 0
		elif new_page >= self.__document.get_n_pages():
			new_page = self.__document.get_n_pages() - 1
			
		if self.__type_of_view == self.VIEW_CONTINUOUS: # continous
			adj = self.get_vadjustment()
			value = max(adj.lower, min(adj.upper - adj.page_size, self.__page_position[new_page]))
			adj.set_value(value)
		else: # single page
			self.__current_page = new_page
			self.__update_scrolled_window(self.EVENT_CHANGE_PAGE)


	def go_to_page_and_position(self, page, y):
		# TODO: Add an argument for choosing where to put 
		# the destination: at the top, middle, or bottom of the view.
		if page < 0 or page > self.__document.get_n_pages():
			return False
			
		if self.__type_of_view == self.VIEW_CONTINUOUS:
			page_index = page
		else:
			page_index = 0
		
		#~ free_left_space = self.get_free_horiz_space(page_index)
		free_top_space = self.get_free_vert_space()
		#~ x_in_page = (x - free_left_space) / self.__scale
		scroll_pos = y * self.__scale + free_top_space + (self.__page_position[page_index] + 2)
		
		vadj = self.get_vadjustment()
		scroll_pos = max(vadj.lower, min(scroll_pos, vadj.upper - vadj.page_size))
		if self.__type_of_view == self.VIEW_CONTINUOUS:
			vadj.set_value(scroll_pos)
		else:
			if page != self.__current_page:
				self.__current_page = page
				self.__update_scrolled_window(self.EVENT_CHANGE_PAGE)
			vadj.set_value(scroll_pos)
		
		return True
		
				
	def toggle_continuous(self):
		"""
		Method that toggles continuous/single page type of view.
		"""
		
		current_page = self.get_current_page()
		if self.__type_of_view == self.VIEW_CONTINUOUS: # was continuous
			self.__type_of_view = self.VIEW_SINGLE_PAGE # set to single page
			self._preferences.set("PdfPreviewTypeOfView", self.__type_of_view)
			last_pos = self.__last_vertical_scroll_position - self.__page_position[current_page]
			self.__current_page = current_page
			self.__update_scrolled_window(self.EVENT_TOGGLE_CONTINUOUS)
			self.__last_vertical_scroll_position = last_pos
		else: # was single page
			self.__type_of_view = self.VIEW_CONTINUOUS # set to continuous
			self._preferences.set("PdfPreviewTypeOfView", self.__type_of_view)
			last_pos = self.__last_vertical_scroll_position
			self.__update_scrolled_window(self.EVENT_TOGGLE_CONTINUOUS)
			self.__last_vertical_scroll_position = last_pos + self.__page_position[current_page]


	def __sync_edit(self, x, y):
		"""
		Called on Ctrl+Click at some point in the output, to sync with 
		the corresponding source through synctex. (x,y) is the position 
		in the scrolled window.
		"""
		
		page, page_x, page_y = self.get_page_and_position_from_pointer(x, y)
			
		import subprocess
		import sys

		cmd = ["synctex", "edit", "-o", "%d:%d:%d:%s" % (page + 1, page_x, page_y, self.__compiled_file_path)]
		try:
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		except OSError:
			self._log.warning("Synctex not found. Please install the synctex package from your TeX distribution.")
			return

		found_a_place = False
		for l in iter(p.stdout.readline, ''):
			tag, sep, value = l.strip("\n").partition(":")
			if tag == "SyncTeX ERROR":
				self._log.warning("%s: %s" % (tag, value))
				self._log.warning("Use the '\synctex=1' command in your preamble.")
				return
			elif tag == "Output":
				# We only keep the first result.
				if found_a_place == True:
					break
				else:
					found_a_place = True
				output = value
			elif tag == "Input":
				input = value
			elif tag == "Line":
				line = int(value)
			elif tag == "Column":
				column = int(value)
			elif tag == "Offset":
				offset = int(value)
			elif tag == "Context":
				context = value
			sys.stdout.flush() 
		p.wait()
		
		if not found_a_place:
			return

		self.__latex_previews.sync_edit(input, output, line, column, offset, context)
				
	
	def sync_view(self, source_file, line, column, output_file):
		import subprocess
		import sys

		found_a_place = False
		
		cmd = ["synctex", "view", "-i", "%d:%d:%s" % (line, column, source_file), "-o", output_file]
		try:
			p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		except OSError:
			self._log.warning("Synctex not found. Please install the synctex package from your TeX distribution.")
			return
			
		for l in iter(p.stdout.readline, ''):
			tag, sep, value = l.strip("\n").partition(":")
			if tag == "SyncTeX ERROR":
				self._log.warning("%s: %s" % (tag, value))
				self._log.warning("Use the '\synctex=1' command in your preamble.")
				return
			elif tag == "Output":
				# We only keep the first result.
				if found_a_place == True:
					break
				else:
					found_a_place = True
			elif tag == "Page":
				page = int(value)
			elif tag == "x":
				x = float(value)
			elif tag == "y":
				y = float(value)
			elif tag == "h":
				h = float(value)
			elif tag == "v":
				v = float(value)
			elif tag == "W":
				W = float(value)
			elif tag == "H":
				H = float(value)
			# For synchronization by offset, use the tags:
			# before, offset, middle, after
			# Run "synctex view" for more information.

			sys.stdout.flush()
		p.wait()

		if not found_a_place:
			return
		
		self._log.debug("Sync view. Found values: page:%d, x:%f, y:%f, h:%f, v:%f, W:%f, H:%f." % (page, x, y, h, v, W, H))
		
		# TODO: implement a method to make sure the box with top-left 
		# and bottom-right corners (h, v - H) and (h + W, v) is visible.
		# Currently, we only scroll to put the vertical position v - H 
		# of page "page", at the middle of the pdf preview.
		if self.__type_of_view == self.VIEW_CONTINUOUS:
			index = page - 1
		else:
			index = 0
		view_height = self.get_vadjustment().page_size
		self.go_to_page_and_position(page - 1, v - H/2 - (view_height/self.scale)/2)
		self.__sync_rectangle.show(page - 1, h, v - H, W, H, self.__drawing_areas[index], self.scale)

		
	def __connect_mouse_events(self):
		"""
		Connects mouse events. Called by 
		__create_preview_panel().
		"""
		
		scrolled_window = self.get_scrolled_window()

		self.__mouse_handlers = [ scrolled_window.connect("scroll-event", self.__on_scroll),
					scrolled_window.connect("button-press-event", self.__on_button_press),
					scrolled_window.connect("button-release-event", self.__on_button_release),
					scrolled_window.connect("motion-notify-event", self.__on_motion) ]
		
		
	def __disconnect_mouse_events(self):
		"""
		Disconnects mouse events. Called by 
		__create_default_panel().
		"""

		scrolled_window = self.get_scrolled_window()
		
		for handler in self.__mouse_handlers:
			scrolled_window.disconnect(handler)
			handler = None
		self.__mouse_handlers = []

		
	def __connect_keyboard_events(self):
		"""
		Connects keyboard events. Called by 
		__create_preview_panel().
		"""
		
		widget = self.get_panel()

		self.__keyboard_handlers = [ widget.connect("key-press-event", self.__on_key_press) ]
		
		
	def __disconnect_keyboard_events(self):
		"""
		Disconnects keyboard events. Called by 
		__create_default_panel().
		"""

		widget = self.get_panel()
		
		for handler in self.__keyboard_handlers:
			widget.disconnect(handler)
			handler = None
		self.__keyboard_handlers = []

	
	def __free_scrolled_window_handlers(self):
		"""
		Method that frees all signal handlers related to the preview 
		panel.
		"""
		
		
		
	def destroy(self):
		"""
		Method that destroys every children of the panel.
		"""
		
		GObject.source_remove(self.__check_changes_id)

		# scrolled window adjustments
		scrolled_window = self.get_scrolled_window()
		
		vadj = scrolled_window.get_vadjustment()
		vadj.disconnect(self.__vadj_changed_id)
		vadj.disconnect(self.__vadj_value_id)
		self.__vadj_changed_id = None
		self.__vadj_value_id = None
		
		hadj = scrolled_window.get_hadjustment()
		hadj.disconnect(self.__hadj_changed_id)
		hadj.disconnect(self.__hadj_value_id)
		self.__hadj_changed_id = None
		self.__hadj_value_id = None
		
		# mouse
		self.__disconnect_mouse_events()

		# drag managers
		self.__preview_drag.destroy()
		self.__glass_drag.destroy()
		
		# keyboard
		self.__disconnect_keyboard_events()
		
		# magnifying glass
		if not self.__magnifying_glass is None:
			self.__magnifying_glass.destroy()
			self.__magnifying_glass = None
		
		# pages
		pages = self.get_scrolled_window().get_children()[0].get_children()[0].get_children()[0]
		for i in range(len(self.__drawing_areas)):
			self.__delete_last_page(pages)
		self.__expose_id.clear()
		self.__drawing_areas.clear()

		# the scrolled window
		for i in self.__panel.get_children():
			self.__panel.remove(i)


	def __del__(self):
		self._log.debug("Preview panel properly destroyed (__del__ called)")
		


class MagnifyingGlass:
	"""
	Class that manages a magnifying glass for the PDF preview.
	"""
	
	USE_PIXBUF = False
	
	def __init__(self, preview_scale, document):
		"""
		Initializes the magnifying glass.
		"""
		
		self._preferences = Preferences()
		
		self.__width = int(self._preferences.get("PDFPreviewMagnifierWidth", 400))
		self.__height = int(self._preferences.get("PDFPreviewMagnifierHeight", 233))
		
		self.__scale = float(self._preferences.get("PDFPreviewMagnifierScale", 4.0))
		self.set_preview_scale(preview_scale)
		
		self.__is_shown = False
		
		self.__page = 0
		self.__page_center_x = 0
		self.__page_center_y = 0
		
		self.__document = document
		self.__page_width, self.__page_height = self.__document.get_page_size(self.__page)
		
		self.__window = Gtk.Window(Gtk.WindowType.POPUP)
		self.__window.set_size_request(self.__width, self.__height)
		self.__window.set_gravity(Gdk.GRAVITY_CENTER)
		self.__window.set_position(Gtk.WindowPosition.MOUSE)
		
		self.__drawing_area = Gtk.DrawingArea()
		self.__drawing_area.set_size_request(int(self.__width), int(self.__height))
		self.__drawing_area.show()
		
		if self.USE_PIXBUF:
			self.__pixbuf = None
			self.__expose_id = self.__drawing_area.connect("expose-event", self.__on_expose_with_pixbuf)
		else:
			self.__expose_id = self.__drawing_area.connect("expose-event", self.__on_expose)
		
		self.__window.add(self.__drawing_area)
		

	def show(self):
		self.__window.show()
		self.__is_shown = True


	def hide(self):
		self.__window.hide()
		self.__is_shown = False
	
	
	def set_scale(self, scale):
		self.__scale = scale
		self._preferences.set("PDFPreviewMagnifierScale", float(scale))
		
		
	def set_preview_scale(self, preview_scale):
		self.__preview_scale = preview_scale
		self.__total_scale = self.__scale * self.__preview_scale
		if self.USE_PIXBUF:
			self.__pixbuf = None


	def is_shown(self):
		return self.__is_shown
		
		
	def move_center_to(self, x, y):
		self.__window.move(x - self.__width / 2, y - self.__height / 2)
		
		
	def set_page_and_position(self, page, x, y):
		"""
		Sets the page number and the position (at scale 1) in the page 
		of the center of the region to be drawn in the magnifying glass.
		"""

		if page != self.__page:
			self.__page = page
			self.__page_width, self.__page_height = self.__document.get_page_size(page)
			
			if self.USE_PIXBUF:
				self.__update_pixbuf()
			
		self.__page_center_x = x
		self.__page_center_y = y	
	
	
	def __update_pixbuf(self):
		scale = self.__total_scale
		width = int(self.__page_width * scale)
		height = int(self.__page_height * scale)
		
		self.__pixbuf = GdkPixbuf.Pixbuf(GdkPixbuf.Colorspace.RGB, False, 8, width, height)
		self.__pixbuf.fill(0xffffffff)

		# Strange: render_to_pixbuf doesn't take into account the width 
		# and height given as 4th and 5th arguments here...
		# And it is VERY slow...
		self.__document.render_page_to_pixbuf(self.__page, 0, 0, width, height, scale, 0, self.__pixbuf)


	def __on_expose(self, drawing_area, event):
		cr = drawing_area.window.cairo_create()

		scale = self.__total_scale
		cr.scale(scale, scale)
		
		translate_x = (self.__page_center_x - (self.__width / scale) / 2)
		translate_y = (self.__page_center_y - (self.__height / scale) / 2)
		cr.translate(- translate_x, - translate_y)

		cr.set_source_rgb(1, 1, 1)
		cr.rectangle(0, 0, self.__page_width, self.__page_height)
		cr.fill()

		self.__document.render_page(cr, self.__page)


	def __on_expose_with_pixbuf(self, drawing_area, event):
		scale = self.__scale * self.__preview_scale
		
		translate_x = (self.__page_center_x * scale - self.__width / 2.0)
		translate_y = (self.__page_center_y * scale - self.__height / 2.0)

		cr = drawing_area.window.cairo_create()
		if self.__pixbuf is None:
			self.__update_pixbuf()
		cr.set_source_pixbuf(self.__pixbuf, -translate_x, -translate_y)
		cr.paint()


	def refresh(self):
		self.__drawing_area.queue_draw()
		
		
	def destroy(self):
		self.__drawing_area.disconnect(self.__expose_id)



class DocumentPropertiesDialog:
	"""
	This class manages the document properties dialog.
	"""
	
	def __init__(self, document):
		"""
		Initializes the dialog.
		"""
		
		self.__document = document
		
		# Hacky way to get the gedit main window...
		self.__parent_window = Gtk.window_list_toplevels()[0]

		self.__properties = ["title", "path", "subject", "author",
							 "keywords", "producer", "creator", 
							 "creation-date", "mod-date", "format", 
							 "n-pages", "linearized", "permissions",
							 "page-layout", "page-mode", 
							 "viewer-preferences", "paper-size"]
		self.__labels = {"title": "Title:",
						 "path": "Path:",
						 "subject": "Subject:",
						 "author": "Author:",
						 "keywords": "Keywords:",
						 "producer": "Producer:",
						 "creator": "Creator:",
						 "creation-date": "Creation date:",
						 "mod-date": "Modification date:",
						 "format": "Format:",
						 "n-pages": "Number of pages:",
						 "linearized": "Optimized:",
						 "page-layout": "Page layout:",
						 "page-mode": "Page mode:",
						 "viewer-preferences": "Viewer preferences:",
						 "permissions": "Permissions:",
						 "paper-size": "Paper size:"}
		self.__tooltips = {"title": "The title of the document",
						   "path": "The file path of the document",
						   "subject": "Subjects the document touches",
						   "author": "The author of the document",
						   "keywords": "Keywords",
						   "producer": "The software that converted the document",
						   "creator": "The software that created the document",
						   "creation-date": "The date and time the document was created",
						   "mod-date": "The date and time the document was modified",
						   "format": "The PDF version of the document",
						   "n-pages": "Number of pages",
						   "linearized": "Is the document optimized for web viewing?",
						   "page-layout": "Initial Page Layout",
						   "page-mode": "Page Mode",
						   "viewer-preferences": "Viewer preferences",
						   "permissions": "Permissions",
						   "paper-size": "Paper size of the first page of the document"}

		self.__property_values = {}
		self.__dialog = None
		
		self.__build_dialog()

		self.show()
		
	
	def __on_response(self, widget, response):
		"""
		Monitors the response events sent by the dialog.
		"""
		
		if response == Gtk.ResponseType.CLOSE or response == Gtk.ResponseType.DELETE_EVENT:
			self.destroy()
		
		
	def __build_dialog(self):
		"""
		Builds the dialog.
		"""
		
		self.__dialog = Gtk.Dialog("PDF document properties",
                     self.__parent_window,
                     Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                     (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
		
		self.__response_id = self.__dialog.connect("response", self.__on_response)
		
		table = Gtk.Table(len(self.__properties), 2)
		
		(maj, min, rev) = Gtk.ver
		if not (maj >= 2 and min >= 12):
			tooltips = Gtk.Tooltips()
		
		i = 0
		for property in self.__properties:
			label = Gtk.Label()
			label.set_markup("<b>%s</b>" % self.__labels[property])
			label.set_alignment(0, 1)
			if not (maj >= 2 and min >= 12):
				tooltips.set_tip(label, self.__tooltips[property])
			else:
				label.set_tooltip_text(self.__tooltips[property])
			table.attach(label, 0, 1, i, i + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL, 8, 3)

			value = Gtk.Label()
			value.set_selectable(True)
			value.set_width_chars(45)
			value.set_ellipsize(Pango.EllipsizeMode.END)
			value.set_alignment(0, 1)
			table.attach(value, 1, 2, i, i + 1, Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND, Gtk.AttachOptions.FILL, 8, 3)
			self.__property_values[property] = value
			i += 1
		
		self.__dialog.vbox.add(table)
		

	def __format_value(self, property, value):
		"""
		Formats value according to property type.
		"""
		
		if property in ["creation-date", "mod-date"]:
			import datetime
			date = datetime.datetime.fromtimestamp(value)
			return date.ctime()
		elif property == "n-pages":
			return str(value)
		elif property == "permissions":
			perm = self.__document.permissions_to_text_list(value)
			return "Allowed to %s" % ", ".join(perm)
		elif property == "page-layout":
			return self.__document.page_layout_to_text(value)
		elif property == "page-mode":
			return self.__document.page_mode_to_text(value)
		elif property == "viewer-preferences":
			pref = self.__document.viewer_preferences_to_text_list(value)
			return ", ".join(pref)
		elif property == "paper-size":
			width, height = value
			return "%d x %d mm" % (width / 72 * 25.4, height / 72 * 25.4)
		else:
			return str(value)
		
		
	def update(self):
		"""
		Updates the fields.
		"""
		
		for property in self.__properties:
			if property == "path":
				value = self.__document.get_document_path()
			elif property == "n-pages":
				value = self.__document.get_n_pages()
			elif property == "paper-size":
				value = self.__document.get_page_size(0)
			else:
				value = self.__document.get_property(property)
			
			text = self.__format_value(property, value)
			if text == "":
				text = "<i>%s</i>" % "None"
				self.__property_values[property].set_markup(text)
			else:
				self.__property_values[property].set_text(text)		
		
		
	def show(self):
		"""
		Shows the dialog (actually creates it).
		"""
		
		self.update()
		self.__dialog.show_all()
		
		
	def hide(self):
		"""
		Hides the dialog (actually destroys it).
		"""
		
		self.__dialog.hide()
		
		
	def destroy(self):
		"""
		Destroys the dialog (removes all handlers, references, etc.).
		"""
		
		self.hide()
		self.__dialog.disconnect(self.__response_id)
		self.__dialog = None
		
