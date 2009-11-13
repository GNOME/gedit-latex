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

'''
Created on May 31, 2009

@author: Dan Mihai Ile (mihai007)
'''

import gedit
import gtk
import poppler
import os
import gobject
import cairo

class LatexPreview:
    """
    Class that manages all tab's preview panels
    """

    def __init__(self, window):
        self.__gedit_window = window

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

            # The trick of this whole thing is that you have to wait a second for the
            # Paned object to figure out how much room it can take up.  So, we're just
            # going to set a timer that'll check every 10 milliseconds until it
            # decides it can trust the width that the Paned object returns.
            gobject.timeout_add(10, self.adjust_width)

            # Add the two scrolled windows to our Paned object.
            self.split_views[current_tab].add(left_window)
            self.split_views[current_tab].add(preview_panel.get_panel())

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
        self.preview_panels.pop(current_tab)

    def adjust_width(self):
        """
        This function eventually sets the divider of the splitview
        It waits until the gui object returns a reasonable width.
        """
        
        # 0 means successfuly set the width, 1 means nothing done 
        result = 0
            
        current_tab = self.__gedit_window.get_active_tab()

        width = self.split_views[current_tab].get_property("max-position")

        if (width < 50):
            result = 1
        else:
            # give all space to the editor - the preview window width
            self.split_views[current_tab].set_position(int(width - 620))
        return result


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
        
        # by default the document width and height is an A4 document
        (self.__doc_width, self.__doc_height) = (595, 842)
        # TODO preview message should be externalised and translatable
        self.__no_preview_message = "Preview not available..."
        self.__parent_pdf_path = parent_pdf_path
        # the panel that will contain all visible elements
        self.__panel = gtk.VBox(False, 0)
        # keep track of scroll changes in the preview document
        self.__last_vertical_scroll_position = 0
        
        # TODO: very nasty hack to detect changes in pdf file
        # this is a 1000ms loop, there should be an event generated
        # by the plugin to notify that pdf file was updated
        gobject.timeout_add(1000, self.__check_changes)
        
        # create the visible elements on the panel
        self.__initialize()

    def __initialize(self):
        """
        Creates all visible elements on the panel, cleaning it
        from previous existing elements first
        """
        
        # clean the panel before addin anything to it
        for i in self.__panel.get_children():
            self.__panel.remove(i)
        # a scrolled window that will contain all .pdf pages
        scrolled_window = gtk.ScrolledWindow()
        
        vadj = scrolled_window.get_vadjustment()
        
        # TODO: remove listeners when closing preview for document or a reload occurs
        vadj.connect('changed', lambda a, s=scrolled_window: self.__rescroll(a,s))
        vadj.connect("notify::value", self.__doVAdjustment)

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

    def __doVAdjustment(self, adj, scroll):
        self.__last_vertical_scroll_position = adj.get_value()

    def __rescroll(self, adj, scroll):
        if self.__last_vertical_scroll_position < (adj.upper - adj.page_size):
            adj.set_value(self.__last_vertical_scroll_position)
            scroll.set_vadjustment(adj)

    def __create_default_panel(self, scrolled_window):
        """
        Creates a default document view
        @param scrolled_window: the window to add the default view page
        """
        
        page = gtk.VBox(False, 2)
        dwg = gtk.DrawingArea()
        dwg.set_size_request(int(self.__doc_width), int(self.__doc_height))
        # we need to redraw the new exposed portion of the document
        dwg.connect("expose-event", self.on_expose_default)
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
        self.__document = poppler.document_new_from_file("file://%s" % self.__parent_pdf_path, None)
        self.__last_update_time = os.path.getmtime(self.__parent_pdf_path)
        (self.__doc_width, self.__doc_height) = self.__document.get_page(0).get_size()

        # create all document pages
        pages = gtk.VBox(False, 2)
        for i in range(self.__document.get_n_pages()):
            dwg = gtk.DrawingArea()
            dwg.set_size_request(int(self.__doc_width), int(self.__doc_height))
            # we need to redraw the new exposed portion of the document
            dwg.connect("expose-event", self.on_expose, i)
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
        self.__document.get_page(i).render(cr)
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
        cr.set_source_rgb(1, 1, 1)
        cr.rectangle(0, 0, self.__doc_width, self.__doc_height)
        cr.fill()
        return cr

    def __create_page_border(self, cr):
        """
        method that draws a border around the document page
        """
        
        cr.set_source_rgb(0, 0, 0)
        cr.move_to(1, 1)
        cr.line_to(self.__doc_width - 0.5, 1)
        cr.line_to(self.__doc_width - 0.5, self.__doc_height )
        cr.line_to(0, self.__doc_height )
        cr.line_to(0, 1)
        cr.stroke()
