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
PDF live preview

@author: Dan Mihai Ile (mihai007)
         Yannick Voglaire (yannickv)
"""

import gedit
import gtk
import os
import gobject
import cairo

from ..preferences import Preferences


class LatexPreview:
	"""
	Class that manages all tab's preview panels
	"""
	
	def __init__(self, window):
		self.__gedit_window = window
		
		self._preferences = Preferences()
		
		# keep track of all gedit tabs that have preview enabled
		self.split_views = {}
		self.preview_panels = {}

		# I hardly even know how this works, but it gets our encoding.
		try: self.encoding = gedit.encoding_get_current()
		except: self.encoding = gedit.gedit_encoding_get_current()

	def toggle_preview(self, parent_pdf_path):
		"""
		enable/disable the preview window for the active tab
		@param parent_pdf_path: the path to the pdf file
		"""

		# use the current tab to create the preview in it
		current_tab = self.__gedit_window.get_active_tab()

		# If we already have a preview for this tab, remove it
		if (current_tab in self.split_views):
			self.end_preview()
		# Otherwise, start the preview
		else:
			self.split_view(parent_pdf_path)

	def split_view(self, parent_pdf_path):
		"""
		This function creates the actual split view.
		@param parent_pdf_path: the path to the pdf file
		"""
		
		# Get the preferred width for the pdf preview (default: A4 width (scale 1) + scrollbar)
		self.__preview_width = int(self._preferences.get("PdfPreviewWidth", 620))
		
		# Get the tab / document
		current_tab = self.__gedit_window.get_active_tab()
		self.split_views[current_tab] = gtk.HPaned()

		old_view = None

		# Here we just kind of loop through the child object of the tab
		# and get rid of all of the existing GUI objects.
		for each in current_tab.get_children():

			# The child of the child has the View object for the active document.
			for any in each.get_children():
				old_view = any
				each.remove(any)

			# Create a scrolled window for the left / top side.
			left_window = gtk.ScrolledWindow()
			left_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
			left_window.add(old_view)

			preview_panel = PreviewPanel(parent_pdf_path)
			self.preview_panels[current_tab] = preview_panel
			
			vbox2 = gtk.VBox()
			vbox2.pack_start(self.split_views[current_tab])

			each.add_with_viewport(vbox2)

			# Add the two scrolled windows to our Paned object.
			# Ask that when the window is resized, the preview keep the same size
			self.split_views[current_tab].pack1(left_window, True, True)
			self.split_views[current_tab].pack2(preview_panel.get_panel(), False, True)

			# Request the preferred width for the preview
			self.split_views[current_tab].get_child2().set_size_request(self.__preview_width, -1)

			# Monitor the handle position to keep the document centered
			self.__pane_position_id = self.split_views[current_tab].connect("notify::position", self.__pane_moved)

		current_tab.show_all()

	def end_preview(self):
		"""
		Method that ends the preview
		"""
		
		current_tab = self.__gedit_window.get_active_tab()
		original_view = self.split_views[current_tab].get_child1().get_children()[0]

		for each in current_tab.get_children():

			for any in each.get_children():
				each.remove(any)

			original_view.reparent(each)

		current_tab.show_all()

		self.split_views.pop(current_tab)
		self.preview_panels[current_tab].destroy()
		self.preview_panels.pop(current_tab)

	def __pane_moved(self, pane, paramspec):
		"""
		Method that saves the width of the preview each time it is modified
		"""
		total_width = pane.get_property("max-position")
		position = pane.get_position()
		self.__preview_width = total_width - position
		self._preferences.set("PdfPreviewWidth", self.__preview_width)


class PreviewDocument:
	"""
	This class abstracts document methods for a future pdf and ps support.
	Currently does nothing.
	"""

	def __init__(self, document_path):
		"""
		Initialize the ps or pdf document with name document_path
		"""

		# TODO: Handle errors
		# TODO: Support postscript documents

		self.__document_path = document_path
		if self.__document_path.endswith(".pdf"):
			self.__document_type = "pdf"
			import poppler
			self.__document = poppler.document_new_from_file("file://%s" % self.__document_path, None)
		elif self.__document_path.endswith(".ps"):
			self.__document_type = "ps"
			self.__document = None
		else:
			self.__document_type = None
			self.__document = None

	def get_n_pages(self):
		if not self.__document_type is None:
			return self.__document.get_n_pages()
		else:
			return None

	def get_page(self, index):
		if not self.__document_type is None:
			return self.__document.get_page(index)
		else:
			return None

	def get_size_from_page(self, page):
		if not self.__document_type is None:
			return page.get_size()
		else:
			return None

	def free_page(self, page):
		# Was necessary with libspectre: spectre_page_free(page)
		pass

	def get_page_size(self, index):
		page = self.get_page(index)
		if page is None:
			return None
		size = self.get_size_from_page(page)
		self.free_page(page)
		return size

	def render_page(self, rc, index):
		if not self.__document_type is None:
			return self.__document.get_page(index).render(rc)
		else:
			return None


class PreviewPanel:
	"""
	This class contains a view of the .pdf file. A gtk.Vbox is created
	and contains all visible elements, accessible through get_panel().
	If file is not found or an error found during the preview generation
	a default display is shown.
	"""

	def __init__(self, parent_pdf_path):
		"""
		Creates a PreviewPanel given a pdf file path
		@param parent_pdf_path: the path to the pdf file
		"""
		
		# Get the preferred scale for the pdf preview
		self._preferences = Preferences()
		self.__scale = float(self._preferences.get("PdfPreviewScale", 1.0))
		
		# by default the document width and height is an A4 document
		(self.__doc_width, self.__doc_height) = (595, 842)
		
		# Thickness of the shadow under each page
		# The real shadow has thickness self.__scale times this
		self.__shadow_thickness = 3.0
		
		# TODO preview message should be externalised and translatable
		self.__no_preview_message = "Preview not available..."
		self.__parent_pdf_path = parent_pdf_path
		self.__document = None
		# the panel that will contain all visible elements
		self.__panel = gtk.VBox(False, 0)
		# keep track of vertical scroll changes in the preview document
		self.__last_vertical_scroll_position = 0
		# same for the horizontal changes, starting centered
		self.__last_horizontal_scroll_percentage = 0.5
		self.__last_horizontal_scroll_position = None
		self.__last_horizontal_scroll_page_size = None
		
		self.__last_update_time = 0
		
		self.__drawing_areas = {}
		self.__vadj_changed_id = None
		self.__hadj_changed_id = None
		self.__vadj_value_id = None
		self.__hadj_value_id = None
		self.__expose_id = {}
		
		# TODO: very nasty hack to detect changes in pdf file
		# this is a 1000ms loop, there should be an event generated
		# by the plugin to notify that pdf file was updated
		self.__check_changes_id = gobject.timeout_add(1000, self.__check_changes)
		
		# create the visible elements on the panel
		self.__initialize()

	def __initialize(self):
		"""
		Creates all visible elements on the panel, cleaning it
		from previous existing elements first
		"""
		self.__free_handlers()
		
		# clean the panel before addin anything to it
		for i in self.__panel.get_children():
			self.__panel.remove(i)
		# a scrolled window that will contain all .pdf pages
		scrolled_window = gtk.ScrolledWindow()
		
		vadj = scrolled_window.get_vadjustment()
		
		hadj = scrolled_window.get_hadjustment()

		self.__vadj_changed_id = vadj.connect('changed', lambda a, s=scrolled_window: self.__vert_rescroll(a,s))
		self.__vadj_value_id = vadj.connect("notify::value", self.__do_vert_adjustment)

		self.__hadj_changed_id = hadj.connect('changed', lambda a, s=scrolled_window: self.__horiz_rescroll(a,s))
		self.__hadj_value_id = hadj.connect("notify::value", self.__do_horiz_adjustment)

		# See __horiz_rescroll()
		self.__horiz_rescroll_count = 0

		scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.__panel.pack_start(scrolled_window, True, True, 0)
		try: # try to create a preview for the document, if unable
			self.__create_preview_panel(scrolled_window)
		except: # then show a default document view
			self.__create_default_panel(scrolled_window)
			
	def __check_changes(self):
		"""
		Check the pdf file for the last modification time and call for
		preview redraw it file has a more recent modification timestamp
		@return: 1 so that the method will be called again by gobject.timeout_add
		"""
		
		file_time = os.path.getmtime(self.__parent_pdf_path)
		if self.__last_update_time < file_time:
			self.__initialize()
			self.__panel.show_all()
		return 1

	def __do_horiz_adjustment(self, adj, scroll):
		if adj.page_size > 50:
			self.__last_horizontal_scroll_position = adj.value
			self.__last_horizontal_scroll_page_size = adj.page_size
		else:
			self.__last_horizontal_scroll_position = None

	def __horiz_rescroll(self, adj, scroll):
		# Wait until page_size settles: the first time a "changed" event is triggered,
		# the vertical scroll bar is not yet present, giving the wrong size to page_size.
		# Waiting a few events bypasses this.
		if self.__horiz_rescroll_count < 2:
			self.__horiz_rescroll_count += 1
			return
		
		if self.__last_horizontal_scroll_position == None:
			total = adj.upper - adj.lower - adj.page_size - 2 * self.__shadow_thickness * self.__scale
			adj.value = adj.lower + total / 2
		else:
			new_value = self.__last_horizontal_scroll_position - (adj.page_size - self.__last_horizontal_scroll_page_size) / 2
			if new_value < adj.lower:
				adj.value = adj.lower
			elif new_value > adj.upper - adj.page_size:
				adj.value = adj.upper - adj.page_size
			else:
				adj.value = new_value
		scroll.set_hadjustment(adj)

	def __do_vert_adjustment(self, adj, scroll):
		self.__last_vertical_scroll_position = adj.value

	def __vert_rescroll(self, adj, scroll):
		if self.__last_vertical_scroll_position < (adj.upper - adj.page_size):
			adj.set_value(self.__last_vertical_scroll_position)
			scroll.set_vadjustment(adj)

	def __create_default_panel(self, scrolled_window):
		"""
		Creates a default document view
		@param scrolled_window: the window to add the default view page
		"""
		if not self.__document is None:
			self.__document = None
		
		page = gtk.VBox(False, 2)
		dwg = gtk.DrawingArea()
		dwg.set_size_request(int((self.__doc_width + 2 * self.__shadow_thickness) * self.__scale), int((self.__doc_height + 2 * self.__shadow_thickness) * self.__scale))
		# we need to redraw the new exposed portion of the document
		self.__drawing_areas[0] = dwg
		self.__expose_id[0] = dwg.connect("expose-event", self.on_expose_default)
		# keep the page in the middle of the scrolled window
		align = gtk.Alignment(0.5, 0.5, 0, 0)
		page.pack_start(align, False, False, 1)
		align.add(dwg)
		scrolled_window.add_with_viewport(page)

	def __create_preview_panel(self, scrolled_window):
		"""
		method that creates a view of all document pages
		@param scrolled_window: the window to add the document pages
		"""
		
		# create the document using poppler library
		self.__document = PreviewDocument(self.__parent_pdf_path)
		self.__last_update_time = os.path.getmtime(self.__parent_pdf_path)
		(self.__doc_width, self.__doc_height) = self.__document.get_page_size(0)

		# create all document pages
		pages = gtk.VBox(False, 2)
		for i in range(self.__document.get_n_pages()):
			dwg = gtk.DrawingArea()
			dwg.set_size_request(int((self.__doc_width + 2 * self.__shadow_thickness) * self.__scale), int((self.__doc_height + 2 * self.__shadow_thickness) * self.__scale))
			# we need to redraw the new exposed portion of the document
			self.__drawing_areas[i] = dwg
			self.__expose_id[i] = dwg.connect("expose-event", self.on_expose, i)
			# keep the page in the middle of the scrolled window
			align = gtk.Alignment(0.5, 0.5, 0, 0)
			pages.pack_start(align, False, False, 1)
			align.add(dwg)

		scrolled_window.add_with_viewport(pages)

	def get_panel(self):
		"""
		method that returns the current panel available for display
		@return: the current panel available for display
		"""
		
		return self.__panel

	def get_width(self):
		"""
		method that returns the document's width
		@return: the document's width
		"""
		
		return self.__doc_width

	def on_expose(self, widget, event, i):
		"""
		Redraws a portion of the document area that is exposed
		@param widget: 
		@param event: 
		@param i: 
		"""
		
		cr = self.__initialize_cairo_page(widget)
		self.__document.render_page(cr, i)
		self.__create_page_border(cr)

	def on_expose_default(self, widget, event):
		"""
		method that redraws a portion of the default document area that is exposed
		"""
		
		cr = self.__initialize_cairo_page(widget)
		self.__create_page_border(cr)
		# draw the default message in the center of the page
		cr.set_source_rgb(0.5, 0.5, 0.5)
		cr.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
		cr.set_font_size(32)
		x_bearing, y_bearing, width, height = cr.text_extents(self.__no_preview_message)[:4]
		cr.move_to((self.__doc_width / 2) - width / 2 - x_bearing, (self.__doc_height / 2) - height / 2 - y_bearing)
		cr.show_text(self.__no_preview_message)

	def __initialize_cairo_page(self, widget):
		"""
		just initilize cairo to draw in the given widget
		"""
		
		cr = widget.window.cairo_create()
		
		# set the zoom factor for the whole drawing
		cr.scale(self.__scale, self.__scale)

		# shadow (must be under the rest of the drawing)
		st = self.__shadow_thickness
		cr.set_line_width(st)
		cr.set_source_rgb(0.4, 0.4, 0.4)
		cr.move_to(self.__doc_width + 0.5 + st / 2, st)
		cr.line_to(self.__doc_width + 0.5 + st / 2, self.__doc_height + st / 2)
		cr.line_to(st, self.__doc_height + st / 2)
		cr.stroke()

		# prevent the background from showing outside the border because of the antialiasing
		cr.set_antialias(cairo.ANTIALIAS_NONE)

		# background
		cr.set_source_rgb(1, 1, 1)
		cr.rectangle(0, 0, self.__doc_width, self.__doc_height)
		cr.fill()
		
		cr.set_antialias(cairo.ANTIALIAS_DEFAULT)
		
		return cr

	def __create_page_border(self, cr):
		"""
		method that draws a border around the document page
		"""
		# prevent the borders from thickening because of the antialiasing
		cr.set_antialias(cairo.ANTIALIAS_NONE)

		# border (strangely, the white background is 1 pixel wider 
		# than self.__doc_width * self.__scale, so we draw the right border 
		# one pixel further to the right)
		cr.set_line_width(1 / self.__scale)
		
		cr.set_source_rgb(0, 0, 0)
		cr.rectangle(0, 0, self.__doc_width + 1 / self.__scale, self.__doc_height)
		cr.stroke()
		
		cr.set_antialias(cairo.ANTIALIAS_DEFAULT)
		
	def zoom_in(self):
		"""
		This function zooms in the pdf preview.
		"""

		if self.__scale < 16:
			self.__scale += 0.25
			self._preferences.set("PdfPreviewScale", self.__scale)

			# Keep the vertical scrollbar at the same position in the document
			# up to the error due to the space between the pages, which is not scaled
			self.__last_vertical_scroll_position *= self.__scale / (self.__scale - 0.25)

			# Save the horizontal scroll position before initializing
			# and restore it after, to prevent the document from being centered
			# if it was not before
			last_pos = self.__last_horizontal_scroll_position
			last_size = self.__last_horizontal_scroll_page_size

			scrolled_window = self.__panel.get_children()[0]
			hadj = scrolled_window.get_hadjustment()
			last_upper = hadj.upper
			last_lower = hadj.lower
			
			self.__initialize()
			
			# If there is was horizontal scroll bar before zooming in, center the document
			if last_upper - last_lower == last_size:
				self.__last_horizontal_scroll_position = None
			else:
				# Keep the center of the view centered after zooming
				self.__last_horizontal_scroll_position = (last_pos + last_size / 2) * (self.__scale / (self.__scale - 0.25)) - last_size / 2
				self.__last_horizontal_scroll_page_size = last_size
			self.__panel.show_all()


	def zoom_out(self):
		"""
		This function zooms out the pdf preview.
		"""

		if self.__scale > 0.25:
			self.__scale -= 0.25
			self._preferences.set("PdfPreviewScale", self.__scale)

			# Keep the vertical scrollbar at the same position in the document
			# up to the error due to the space between the pages, which is not scaled
			self.__last_vertical_scroll_position *= self.__scale / (self.__scale + 0.25)

			# Save the horizontal scroll position before initializing
			# and restore it after, to prevent the document from being centered
			# if it was not before
			last_pos = self.__last_horizontal_scroll_position
			last_size = self.__last_horizontal_scroll_page_size
			
			self.__initialize()
			
			# Keep the center of the view centered after zooming
			self.__last_horizontal_scroll_position = (last_pos + last_size / 2) * (self.__scale / (self.__scale + 0.25)) - last_size / 2
			self.__last_horizontal_scroll_page_size = last_size
			
			self.__panel.show_all()


	def scroll_up(self):
		"""
		This function scrolls up the pdf preview a few lines
		It is triggered by an accelerator to allow moving in the preview without the mouse
		"""

		#TODO: Use some kind of double buffering to prevent flickering
		scrolled_window = self.__panel.get_children()[0]
		vadj = scrolled_window.get_vadjustment()
		vadj.set_value(vadj.value - 30 * self.__scale)


	def scroll_down(self):
		"""
		This function scrolls down the pdf preview a few lines
		It is triggered by an accelerator to allow moving in the preview without the mouse
		"""

		scrolled_window = self.__panel.get_children()[0]
		vadj = scrolled_window.get_vadjustment()
		vadj.set_value(vadj.value + 30 * self.__scale)


	def scroll_left(self):
		"""
		This function scrolls down the pdf preview a few lines
		It is triggered by an accelerator to allow moving in the preview without the mouse
		"""

		scrolled_window = self.__panel.get_children()[0]
		hadj = scrolled_window.get_hadjustment()
		hadj.set_value(hadj.value - 10 * self.__scale)


	def scroll_right(self):
		"""
		This function scrolls down the pdf preview a few lines
		It is triggered by an accelerator to allow moving in the preview without the mouse
		"""

		scrolled_window = self.__panel.get_children()[0]
		hadj = scrolled_window.get_hadjustment()
		hadj.set_value(hadj.value + 10 * self.__scale)


	def __free_handlers(self):
		panel_children = self.__panel.get_children()
		if len(panel_children) != 0:
			vadj = panel_children[0].get_vadjustment()
			vadj.disconnect(self.__vadj_changed_id)
			vadj.disconnect(self.__vadj_value_id)
			del self.__vadj_changed_id
			del self.__vadj_value_id
			
			hadj = panel_children[0].get_hadjustment()
			hadj.disconnect(self.__hadj_changed_id)
			hadj.disconnect(self.__hadj_value_id)
			del self.__hadj_changed_id
			del self.__hadj_value_id
		
		for i in self.__drawing_areas:
			self.__drawing_areas[i].disconnect(self.__expose_id[i])
		self.__expose_id.clear()
		self.__drawing_areas.clear()
			
			
	def destroy(self):
		self.__free_handlers()
		for i in self.__panel.get_children():
			self.__panel.remove(i)
		gobject.source_remove(self.__check_changes_id)
