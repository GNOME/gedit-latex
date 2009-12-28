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
	Class that manages all tab's preview panels.
	"""
	
	def __init__(self, window):
		"""
		Initializes the PDF preview.
		"""
		
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
		Enables/disables the preview window for the active tab.
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
		Method that creates the actual split view.
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
		Method that ends the preview.
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
		Method that saves the width of the preview each time it is 
		modified.
		"""
		total_width = pane.get_property("max-position")
		position = pane.get_position()
		self.__preview_width = total_width - position
		self._preferences.set("PdfPreviewWidth", self.__preview_width)



class PreviewDocument:
	"""
	Class that abstracts document methods for a future pdf and ps support.
	Currently does nothing.
	"""

	def __init__(self, document_path):
		"""
		Initializes the ps or pdf document with name document_path.
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
		self.__pages = {}


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
			return self.get_page(index).render(rc)
		else:
			return None



class PreviewPanel:
	"""
	This class contains a view of the .pdf file. A gtk.Vbox is created
	that contains all visible elements, accessible through get_panel().
	If the file is not found or an error is triggered during the 
	preview generation a default display is shown.
	"""

	def __init__(self, parent_pdf_path):
		"""
		Creates a PreviewPanel given a pdf file path
		@param parent_pdf_path: the path to the pdf file
		"""
		
		# Get the preferred scale for the pdf preview
		self._preferences = Preferences()
		self.__scale = float(self._preferences.get("PdfPreviewScale", 1.0))
		
		# Get the preferred type of view (continuous of single page)
		if int(self._preferences.get("PdfPreviewTypeOfView", 0)) == 0:
			self.__type_of_view = 0 # continuous
		else:
			self.__type_of_view = 1 # single page
		
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
		self.__parent_pdf_path = parent_pdf_path
		self.__document = None

		# the panel that will contain all visible elements
		self.__panel = gtk.VBox(False, 0)

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

		self.__button_press_id = None
		self.__motion_id = None
		self.__button_release_id = None
		
		self.__in_drag = False
		self.__drag_id = None
		self.__drag_last_x = 0
		self.__drag_last_y = 0

		# Only used in "single page" type of view
		self.__current_page = 0
		# See self.__on_scroll()
		self.__scroll_up_count = 0
		self.__scroll_down_count = 0
		
		self.__magnifying_glass = None
		self.__glass_id = None
		self.__glass_last_x = 0
		self.__glass_last_y = 0
		self.__glass_last_root_x = 0
		self.__glass_last_root_y = 0	
		#~ self.__glass_delayed_hide_mouse_id = None
		
		
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

		self.__vadj_changed_id = vadj.connect('changed', self.__on_vert_adj_changed)
		self.__vadj_value_id = vadj.connect("notify::value", self.__on_vert_adj_value_changed)

		self.__hadj_changed_id = hadj.connect('changed', self.__on_horiz_adj_changed)
		self.__hadj_value_id = hadj.connect("notify::value", self.__on_horiz_adj_value_changed)

		# See __on_horiz_adj_changed()
		self.__horiz_rescroll_count = 0

		# Cursors. Used in self.__set_cursor().
		self.__cursor_standard = None
		self.__cursor_hand = gtk.gdk.Cursor(gtk.gdk.HAND1)
		pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
		color = gtk.gdk.Color()
		self.__cursor_invisible = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)


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
		@return: True so that the method will be called again by gobject.timeout_add
		"""
		
		try:
			file_time = os.path.getmtime(self.__parent_pdf_path)
			if self.__last_update_time < file_time:
				self.__initialize()
				self.__panel.show_all()
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
		than the value is changed (I think). Uses the value stored in 
		self.__last_horizontal_scroll_position (by 
		self.__on_horiz_adj_value_changed(), self.zoom_in/out()) 
		to scroll to the previous position after a zoom in/out.
		"""
		
		# Wait until page_size settles: the first time a "changed" 
		# event is triggered, the vertical scroll bar is not yet 
		# present, giving the wrong size to page_size. Waiting for a 
		# few events bypasses this.
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
		than the value is changed (I think). Uses the value stored in 
		self.__last_vertical_scroll_position (by 
		self.__on_vert_adj_value_changed(), self.zoom_in/out(), or
		self.toggle_continuous()) to scroll to the previous 
		position after a zoom in/out or after toggling 
		continuous/single page type of view.
		"""

		if self.__last_vertical_scroll_position < (adj.upper - adj.page_size):
			adj.set_value(self.__last_vertical_scroll_position)
			

	def __create_default_panel(self, scrolled_window):
		"""
		Creates a default document view.
		@param scrolled_window: the window to add the default view page
		"""
		if not self.__document is None:
			self.__document = None
		
		page = gtk.VBox(False, 2)
		dwg = gtk.DrawingArea()
		dwg.set_size_request(int((self.__page_width[0] + 2 * self.__shadow_thickness) * self.__scale), int((self.__page_height[0] + 2 * self.__shadow_thickness) * self.__scale))
		self.__page_position[0] = 0
		self.__mean_page_size = int((self.__page_height[0] + 2 * self.__shadow_thickness) * self.__scale)
		# we need to redraw the new exposed portion of the document
		self.__drawing_areas[0] = dwg
		self.__expose_id[0] = dwg.connect("expose-event", self.__on_expose_default)
		# keep the page in the middle of the scrolled window
		align = gtk.Alignment(0.5, 0.5, 0, 0)
		page.pack_start(align, True, False, 1)
		align.add(dwg)
		
		scrolled_window.add_with_viewport(page)


	def __create_preview_panel(self, scrolled_window):
		"""
		Method that creates a view of all document pages.
		@param scrolled_window: the window to add the document pages
		"""
		
		# create the document using poppler library
		self.__document = PreviewDocument(self.__parent_pdf_path)
		self.__last_update_time = os.path.getmtime(self.__parent_pdf_path)

		# create all document pages, or only one if in "single page" type of view
		pages = gtk.VBox(False, 2) # here we ask for a padding equal to 2
		if self.__type_of_view == 0: # continuous
			for i in range(self.__document.get_n_pages()):
				dwg = gtk.DrawingArea()
				(self.__page_width[i], self.__page_height[i]) = self.__document.get_page_size(i)
				dwg.set_size_request(int((self.__page_width[i] + 2 * self.__shadow_thickness) * self.__scale), int((self.__page_height[i] + 2 * self.__shadow_thickness) * self.__scale))

				# Save each page's position in the scrolled_window for 
				# the popup menu "Next/Previous page".
				# Actually it is the page position minus the padding, 
				# so that self.__page_position[i] is exactly between 
				# the end of page i-1 (2 pixels higher) and the 
				# beginning page i (2 pixels lower).
				if i == 0:
					self.__page_position[i] = 0
				else:
					# don't forget to take the padding into account (+ 4)
					self.__page_position[i] = self.__page_position[i-1] + int((self.__page_height[i-1] + 2 * self.__shadow_thickness) * self.__scale) + 4

				# we need to redraw the new exposed portion of the document
				self.__drawing_areas[i] = dwg
				self.__expose_id[i] = dwg.connect("expose-event", self.__on_expose, i)
				# keep the page in the middle of the scrolled window
				align = gtk.Alignment(0.5, 0.5, 0, 0)
				pages.pack_start(align, False, False, 1)
				align.add(dwg)
			
			# The mean size taken by a page in the scrolled window
			n = self.__document.get_n_pages()
			self.__mean_page_size = (self.__page_position[n-1] + int((self.__page_height[n-1] + 2 * self.__shadow_thickness) * self.__scale) + 4)/n
			
		else: # single page
			dwg = gtk.DrawingArea()
			(self.__page_width[0], self.__page_height[0]) = self.__document.get_page_size(self.__current_page)
			dwg.set_size_request(int((self.__page_width[0] + 2 * self.__shadow_thickness) * self.__scale), int((self.__page_height[0] + 2 * self.__shadow_thickness) * self.__scale))

			self.__page_position[0] = 0

			# we need to redraw the new exposed portion of the document
			self.__drawing_areas[0] = dwg
			self.__expose_id[0] = dwg.connect("expose-event", self.__on_expose, 0)
			# keep the page in the middle of the scrolled window
			align = gtk.Alignment(0.5, 0.5, 0, 0)
			pages.pack_start(align, True, False, 1)
			align.add(dwg)
			
			self.__mean_page_size = int((self.__page_height[0] + 2 * self.__shadow_thickness) * self.__scale + 4)
			
			# this one is triggered by mouse wheel move
			self.__scroll_id = scrolled_window.connect("scroll-event", self.__on_scroll)
			# this one is triggered by self.scroll_up/down()
			self.__scroll_child_id = scrolled_window.connect("scroll-child", self.__on_scroll_child)
		
		self.__magnifying_glass = MagnifyingGlass(self.__scale, self.__document)
		
		self.__button_press_id = scrolled_window.connect("button-press-event", self.__on_button_press)
		self.__button_release_id = scrolled_window.connect("button-release-event", self.__on_button_release)
		self.__motion_id = scrolled_window.connect("motion-notify-event", self.__on_motion)

		# pack the VBox in an EventBox to be able to receive 
		# events like "button-release-event" and "motion-notify-event"
		event_box = gtk.EventBox()
		event_box.add(pages)
		scrolled_window.add_with_viewport(event_box)
		
		
	def get_panel(self):
		"""
		Method that returns the current panel available for display.
		@return: the current panel available for display
		"""
		
		return self.__panel


	def get_scrolled_window(self):
		"""
		Method that returns the scrolled window containing the preview.
		@return: the scrolled window containing the preview
		"""
		
		return self.__panel.get_children()[0]
		
	
	def get_vadjustment(self):
		"""
		Method that returns the vertical adjustment of the scrolled 
		window containing the preview.
		"""
		
		scrolled_window = self.get_scrolled_window()
		return scrolled_window.get_vadjustment()
		
		
	def get_hadjustment(self):
		"""
		Method that returns the horizontal adjustment of the scrolled 
		window containing the preview.
		"""
		
		scrolled_window = self.get_scrolled_window()
		return scrolled_window.get_hadjustment()
		
		
	def get_width(self):
		"""
		Method that returns the document's width.
		@return: the document's width
		"""
		
		return self.__page_width[0]


	def __on_expose(self, widget, event, i):
		"""
		Redraws a portion of the document area that is exposed.
		@param widget: 
		@param event: 
		@param i: 
		"""
		
		# When in "single page" type of view, the dimensions are stored 
		# at index 0 of variables like self.__page_height,
		# while i is the index of the page to be rendered.
		# When in "continuous" type of view, i serves for both indices.
		if self.__type_of_view == 0: # continuous
			page_to_render = i
		else: # single page
			page_to_render = self.__current_page
		
		cr = self.__initialize_cairo_page(widget, event, i)
		self.__document.render_page(cr, page_to_render)
		self.__create_page_border(cr, i)


	def __on_expose_default(self, widget, event):
		"""
		Method that redraws a portion of the default document area 
		that is exposed.
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
		
		if event.button == 1:
			page, x_in_page, y_in_page = self.get_page_and_position_from_pointer(event.x, event.y)
			self.__magnifying_glass.set_page_and_position(page, x_in_page, y_in_page)
			self.__magnifying_glass.show()
			self.__set_cursor(True)
			#~ self.__glass_delayed_hide_mouse_id = gobject.timeout_add(500, self.__delayed_hide_mouse)
			return True
			
		elif event.button == 2:
			scrolled_window = self.get_scrolled_window()
			hscroll = scrolled_window.get_hadjustment().value
			vscroll = scrolled_window.get_vadjustment().value
			
			self.__drag_initial_x = event.x - hscroll
			self.__drag_initial_y = event.y - vscroll
			self.__drag_last_x = event.x - hscroll
			self.__drag_last_y = event.y - vscroll
			self.__drag_initial_hscroll = hscroll
			self.__drag_initial_vscroll = vscroll
			
			self.__in_drag = True
			
			self.__set_cursor(True, True)
			
			return True

		elif event.button == 3:
			popup_menu = gtk.Menu()

			menu_zoom_in = gtk.ImageMenuItem(gtk.STOCK_ZOOM_IN)
			popup_menu.add(menu_zoom_in)
			menu_zoom_in.connect_object("event", self.__on_popup_clicked, "zoom_in", event.time)

			menu_zoom_out = gtk.ImageMenuItem(gtk.STOCK_ZOOM_OUT)
			popup_menu.add(menu_zoom_out)
			menu_zoom_out.connect_object("event", self.__on_popup_clicked, "zoom_out", event.time)
			
			menu_previous_page = gtk.ImageMenuItem(gtk.STOCK_GO_UP)
			popup_menu.add(menu_previous_page)
			menu_previous_page.connect_object("event", self.__on_popup_clicked, "previous_page", event.time)
			
			menu_next_page = gtk.ImageMenuItem(gtk.STOCK_GO_DOWN)
			popup_menu.add(menu_next_page)
			menu_next_page.connect_object("event", self.__on_popup_clicked, "next_page", event.time)
			
			menu_continuous = gtk.CheckMenuItem("Continuous")
			popup_menu.add(menu_continuous)
			menu_continuous.connect_object("event", self.__on_popup_clicked, "continuous", event.time)

			if self.__type_of_view == 0:
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
		
		if self.__in_drag == True:
			scrolled_window = self.get_scrolled_window()

			hadj = scrolled_window.get_hadjustment()
			vadj = scrolled_window.get_vadjustment()
			self.__drag_last_x = event.x - hadj.value
			self.__drag_last_y = event.y - vadj.value
			
			# Schedule the actual move for a time where the computer 
			# has nothing better to do. The function __follow_mouse_drag
			# always returns False, so that it is only executed once, 
			# even if it has been queued many times. This results in the 
			# view really following the mouse, and not lagging behind 
			# trying to execute every single mouse move.
			self.__drag_id = gobject.idle_add(self.__follow_mouse_drag)
			
		elif self.__magnifying_glass.is_shown():
			root_window = widget.get_screen().get_root_window()
			root_x, root_y, mods = root_window.get_pointer()

			self.__glass_last_root_x = root_x
			self.__glass_last_root_y = root_y
			self.__glass_last_x = event.x
			self.__glass_last_y = event.y
			
			self.__glass_id = gobject.idle_add(self.__follow_mouse_glass)
			
			self.__set_cursor(True)
			#~ if not self.__glass_delayed_hide_mouse_id is None:
				#~ gobject.source_remove(self.__glass_delayed_hide_mouse_id)
			#~ self.__glass_delayed_hide_mouse_id = gobject.timeout_add(500, self.__delayed_hide_mouse)

		return False


	def __follow_mouse_drag(self):
		"""
		Executed in idle time (see self.__on_motion). Drags the view 
		when the middle mouse button is down.
		@return: False whatever happens so that it is only executed once even if it has been queued many times.
		"""
		
		if self.__in_drag == True:
			hadj = self.get_hadjustment()
			vadj = self.get_vadjustment()
			new_hscroll = self.__drag_initial_hscroll - (self.__drag_last_x - self.__drag_initial_x)
			new_vscroll = self.__drag_initial_vscroll - (self.__drag_last_y - self.__drag_initial_y)
			
			if new_hscroll < 0:
				new_hscroll = 0
			elif new_hscroll > hadj.upper - hadj.page_size:
				new_hscroll = hadj.upper - hadj.page_size
				
			if new_vscroll < 0:
				new_vscroll = 0
			elif new_vscroll > vadj.upper - vadj.page_size:
				new_vscroll = vadj.upper - vadj.page_size
				
			self.__last_horizontal_scroll_position = new_hscroll
			self.__last_vertical_scroll_position = new_vscroll
			hadj.set_value(new_hscroll)
			vadj.set_value(new_vscroll)
		return False
		
		
	def __follow_mouse_glass(self):
		"""
		Executed in idle time (see self.__on_motion). Moves the 
		magnifying glass when the left mouse button is down.
		@return: False whatever happens so that it is only executed once even if it has been queued many times.
		"""
		
		if self.__magnifying_glass.is_shown() == True:
			page, x_in_page, y_in_page = self.get_page_and_position_from_pointer(self.__glass_last_x, self.__glass_last_y)
			self.__magnifying_glass.set_page_and_position(page, x_in_page, y_in_page) #page_to_render, x_in_page, y_in_page)
			self.__magnifying_glass.move_center_to(int(self.__glass_last_root_x), int(self.__glass_last_root_y))
			self.__magnifying_glass.refresh()
		return False


	def __on_button_release(self, widget, event):
		"""
		Called when a mouse button is released after having been
		clicked in the scrolled window. Ends the drag or the magnifying 
		glass.
		"""
		
		if self.__in_drag == True:
			self.__in_drag = False
			# It may happen that we start the drag and then don't move, 
			# which results in self.__drag_id not being defined by 
			# self.__on_motion()
			if not self.__drag_id is None:
				gobject.source_remove(self.__drag_id)
				self.__drag_id = None
			self.__set_cursor(True)
			
		elif self.__magnifying_glass.is_shown():
			if not self.__glass_id is None:
				gobject.source_remove(self.__glass_id)
				self.__glass_id = None
			#~ if not self.__glass_delayed_hide_mouse_id is None:
				#~ gobject.source_remove(self.__glass_delayed_hide_mouse_id)
				#~ self.__glass_delayed_hide_mouse_id = None
			self.__set_cursor(True)
			self.__magnifying_glass.hide()
			
		return False


	def __set_cursor(self, visible, in_drag = False):
		"""
		Sets the cursor visible or invisible according to the variable 
		"visible" being True or False, and if visible, sets the cursor 
		to a hand if in_drag is True.
		"""
				
		if visible:
			if in_drag:
				cursor = self.__cursor_hand
			else:
				cursor = self.__cursor_standard
		else:
			cursor = self.__cursor_invisible
		
		#~ if self.__magnifying_glass.is_shown():
			#~ self.__magnifying_glass.set_cursor(cursor)
		self.get_scrolled_window().window.set_cursor(cursor)

	
	def __delayed_hide_mouse(self):
		"""
		Hides the mouse. Scheduled for half a second after the last 
		mouse move when the magnifying glass if shown (the reason is 
		that otherwise the mouse pointer is always in the middle of the 
		magnifying glass, which is a bit annoying).
		What is more annoying is that this doesn't work! I can't change 
		the cursor while the button is pressed, only before or after it
		has been released... I think it is related to the fact that 
		when the button is pressed, another window has the focus, and 
		it is the cursor of that window which should be changed.
		@return: False, to be executed only once.
		"""
		
		self.__set_cursor(False)
		
		return False
		
		
	def __on_popup_clicked(self, widget, event, time):
		"""
		Called when a popup menu item is clicked on.
		"""
		
		# the test on the time is there only to circumvent a strange behaviour: 
		# when right clicking and releasing directly the button, the first 
		# menu item is "activated" (i.e. clicked) AND the menu stays open...
		#TODO: Find out why this doesn't happen in other programs, and fix this properly.
		if event.type == gtk.gdk.BUTTON_RELEASE and event.time - time > 200:
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
		return False


	def __on_scroll_child(self, scrolled_window, scroll_type, horizontal):
		"""
		Monitors the scroll events, to go to next/previous page when 
		in single page type of view and the user scrolls further 
		as he already reached the end of the view.
		Two mouse wheel "clicks" are necessary to go to next/previous 
		page.
		This one is triggered by self.scroll_up/down().
		"""
		
		direction = None
		if horizontal == False:
			if scroll_type == gtk.SCROLL_STEP_BACKWARD:
				direction = gtk.gdk.SCROLL_UP
			elif scroll_type == gtk.SCROLL_STEP_FORWARD:
				direction = gtk.gdk.SCROLL_DOWN
		if not direction is None:
			vadj = scrolled_window.get_vadjustment()
			self.__decide_page_change(vadj, direction)
			
	
	def __on_scroll(self, scrolled_window, event):
		"""
		Monitors the scroll events, to go to next/previous page when 
		in single page type of view and the user scrolls further 
		as he already reached the end of the view.
		Two mouse wheel "clicks" are necessary to go to next/previous 
		page.
		This one is triggered by mouse wheel move.
		"""
		
		vadj = scrolled_window.get_vadjustment()
		self.__decide_page_change(vadj, event.direction)


	def __decide_page_change(self, vadj, direction):
		"""
		According to vadj.value, direction, and 
		self.__scroll_up/down_count, decide wether to change page 
		or not. 
		See self.__on_scroll() and self.__on_scroll_child() for more 
		information.
		"""
		
		if vadj.value == vadj.lower and direction == gtk.gdk.SCROLL_UP and self.__current_page != 0:
			self.__scroll_up_count += 1
			if self.__scroll_up_count == 2:
				self.go_to_page(-1, True)
				self.__scroll_up_count = 0
				self.__last_vertical_scroll_position = vadj.upper - vadj.page_size
				vadj.value = vadj.upper - vadj.page_size
		elif vadj.value == vadj.upper - vadj.page_size and direction == gtk.gdk.SCROLL_DOWN and self.__current_page != self.__document.get_n_pages() - 1:
			self.__scroll_down_count += 1
			if self.__scroll_down_count == 2:
				self.go_to_page(1, True)
				self.__scroll_down_count = 0
				self.__last_vertical_scroll_position = vadj.lower
				vadj.value = vadj.lower
		else:
			self.__scroll_up_count = 0
			self.__scroll_down_count = 0


	def __initialize_cairo_page(self, widget, event, i):
		"""
		Initializes cairo to draw in the given widget, and draws the 
		background and the shadow of page "i".
		"""
		
		cr = widget.window.cairo_create()
		
		# do not draw too much for nothing
		region = gtk.gdk.region_rectangle(event.area)
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

		
	def zoom_in(self):
		"""
		Method that zooms in the pdf preview.
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

			scrolled_window = self.get_scrolled_window()
			hadj = scrolled_window.get_hadjustment()
			last_upper = hadj.upper
			last_lower = hadj.lower
			
			self.__initialize()
			
			# If there was no horizontal scroll bar before zooming in, center the document
			if last_upper - last_lower == last_size:
				self.__last_horizontal_scroll_position = None
			else:
				# Keep the center of the view centered after zooming
				self.__last_horizontal_scroll_position = (last_pos + last_size / 2) * (self.__scale / (self.__scale - 0.25)) - last_size / 2
				self.__last_horizontal_scroll_page_size = last_size
			self.__panel.show_all()


	def zoom_out(self):
		"""
		Method that zooms out the pdf preview.
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
		Method that scrolls up the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-child", gtk.SCROLL_STEP_BACKWARD, False)


	def scroll_down(self):
		"""
		Method that scrolls down the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-child", gtk.SCROLL_STEP_FORWARD, False)


	def scroll_left(self):
		"""
		Method that scrolls down the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-child", gtk.SCROLL_STEP_BACKWARD, True)


	def scroll_right(self):
		"""
		Method that scrolls down the pdf preview a few lines.
		It is triggered by an accelerator to allow moving in the preview without the mouse.
		"""

		scrolled_window = self.get_scrolled_window()
		scrolled_window.emit("scroll-child", gtk.SCROLL_STEP_FORWARD, True)


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
		if self.__type_of_view == 0: # continuous
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

		if self.__type_of_view == 0: # continuous
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
			
		while not (page == 0 or self.__page_position[page] <= position and (page == (n - 1) or self.__page_position[page+1] >= position)):
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
		
		if self.__type_of_view == 0: # continuous
			scrolled_window = self.get_scrolled_window()
			adj = scrolled_window.get_vadjustment()
			current_pos = adj.value
			
			return self.get_page_at_position(current_pos)
		else: # single page
			return self.__current_page
			
			
	def go_to_page(self, page, relative = False):
		"""
		Method that moves the view to a given page.
		@param page: the number of the page to go to
		@param relative: True if parameter "page" is relative to the current page number, False if parameter "page" is the absolute page number
		"""
		
		if relative:
			current_page = self.get_current_page()
			new_page = current_page + page
		else:
			new_page = page
			
		if new_page < 0:
			new_page = 0
		elif new_page >= self.__document.get_n_pages():
			new_page = self.__document.get_n_pages() - 1
			
		if self.__type_of_view == 0: #continous
			scrolled_window = self.get_scrolled_window()
			adj = scrolled_window.get_vadjustment()
			adj.set_value(self.__page_position[new_page])
		else: # single page
			self.__current_page = new_page
			self.__initialize()
			self.__panel.show_all()


	def toggle_continuous(self):
		"""
		Method that toggles continuous/single page type of view.
		"""
		
		current_page = self.get_current_page()
		if self.__type_of_view == 0: # was continuous
			self.__type_of_view = 1 # set to single page
			self._preferences.set("PdfPreviewTypeOfView", self.__type_of_view)
			last_pos = self.__last_vertical_scroll_position - self.__page_position[current_page]
			self.__current_page = current_page
			self.__initialize()
			self.__last_vertical_scroll_position = last_pos
		else: # was single page
			self.__type_of_view = 0 # set to continuous
			self._preferences.set("PdfPreviewTypeOfView", self.__type_of_view)
			last_pos = self.__last_vertical_scroll_position
			self.__initialize()
			self.__last_vertical_scroll_position = last_pos + self.__page_position[current_page]
		self.__panel.show_all()


	def __free_handlers(self):
		"""
		Method that frees all signal handlers related to the preview 
		panel.
		"""
		
		panel_children = self.__panel.get_children()
		if len(panel_children) != 0:
			scrolled_window = panel_children[0]
			
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
			
			# These are not defined in default view, so we have to check
			if not self.__button_press_id is None:
				scrolled_window.disconnect(self.__button_press_id)
				scrolled_window.disconnect(self.__button_release_id)
				scrolled_window.disconnect(self.__motion_id)
				self.__button_press_id = None
				self.__button_release_id = None
				self.__motion_id = None
			
			if not self.__magnifying_glass is None:
				self.__magnifying_glass.destroy()
				self.__magnifying_glass = None
		
		for i in self.__drawing_areas:
			self.__drawing_areas[i].disconnect(self.__expose_id[i])
		self.__expose_id.clear()
		self.__drawing_areas.clear()
		
		
	def destroy(self):
		"""
		Method that destroys every children of the panel.
		"""
		
		self.__free_handlers()
		for i in self.__panel.get_children():
			self.__panel.remove(i)
		gobject.source_remove(self.__check_changes_id)



class MagnifyingGlass:
	"""
	Class that manages a magnifying glass for the PDF preview.
	"""
	
	def __init__(self, preview_scale, document):
		"""
		Initializes the magnifying glass.
		"""
		
		self.__width = 400
		self.__height = 233
		
		self.__scale = 4
		
		self.__is_shown = False
		
		self.__page = 0
		self.__page_center_x = 0
		self.__page_center_y = 0
		
		self.__preview_scale = preview_scale
		
		self.__document = document
		self.__page_width, self.__page_height = self.__document.get_page_size(self.__page)
		
		self.__window = gtk.Window(gtk.WINDOW_POPUP)
		self.__window.set_size_request(self.__width, self.__height)
		self.__window.set_gravity(gtk.gdk.GRAVITY_CENTER)
		self.__window.set_position(gtk.WIN_POS_MOUSE)
		
		self.__drawing_area = gtk.DrawingArea()
		self.__drawing_area.set_size_request(int(self.__width), int(self.__height))
		self.__drawing_area.show()
		
		self.__expose_id = self.__drawing_area.connect("expose-event", self.__on_expose)
		
		self.__window.add(self.__drawing_area)
		

	def show(self):
		self.__window.show()
		self.__is_shown = True


	def hide(self):
		self.__window.hide()
		self.__is_shown = False
	
	
	def set_cursor(self, cursor):
		self.__window.window.set_cursor(cursor)

	
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

		self.__page_center_x = x
		self.__page_center_y = y	
	
	
	def __on_expose(self, drawing_area, event):
		cr = drawing_area.window.cairo_create()
				
		scale = self.__scale * self.__preview_scale
		cr.scale(scale, scale)
		
		translate_x = (self.__page_center_x - (self.__width / scale) / 2)
		translate_y = (self.__page_center_y - (self.__height / scale) / 2)
		cr.translate(- translate_x, - translate_y)

		cr.set_source_rgb(1, 1, 1)
		cr.rectangle(0, 0, self.__page_width, self.__page_height)
		cr.fill()
		
		self.__document.render_page(cr, self.__page)


	def refresh(self):
		self.__drawing_area.queue_draw()
		
		
	def destroy(self):
		self.__drawing_area.disconnect(self.__expose_id)
