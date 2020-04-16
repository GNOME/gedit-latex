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

import re
import time
import logging
import uuid

from gi.repository import Gtk, Gdk

from .completion import CompletionDistributor
from .snippetmanager import SnippetManager
from .file import File

LOG = logging.getLogger(__name__)

class Editor(object):
    """
    The base class for editors. This manages
     - the subclass life-cycle
     - the marker framework
     - change monitoring
     - drag'n'drop support
    """

    class Marker(object):
        """
        Markers refer to and highlight a range of text in the TextBuffer decorated by
        an Editor. They are used for highlighting issues.

        Each Marker instance stores two Gtk.TextMark objects refering to the start and
        end of the text range.
        """
        def __init__(self, left_mark, right_mark, id, type):
            """
            @param left_mark: a Gtk.TextMark
            @param right_mark: a Gtk.TextMark
            @param id: a unique string
            @param type: a marker type string
            """
            self.left_mark = left_mark
            self.right_mark = right_mark
            self.type = type
            self.id = id

    class MarkerTypeRecord(object):
        """
        This used for managing Marker types
        """
        def __init__(self, tag, anonymous):
            """
            @param tag: a Gtk.TextTag
            """
            self.tag = tag
            self.anonymous = anonymous
            self.markers = []

    __PATTERN_INDENT = re.compile("[ \t]+")

    # A list of file extensions
    #
    # If one or more files with one of these extensions is dragged and dropped on the editor,
    # the Editor.drag_drop_received method is called. An empty list disables the dnd support.
    dnd_extensions = []

    def __init__(self, tab_decorator, file):
        self._tab_decorator = tab_decorator
        self._file = file
        self._text_buffer = tab_decorator.tab.get_document()
        self._text_view = tab_decorator.tab.get_view()

        # hook completion handlers of the subclassing Editor
        completion_handlers = self.completion_handlers
        if len(completion_handlers):
            self._completion_distributor = CompletionDistributor(self, completion_handlers)
        else:
            self._completion_distributor = None

        #
        # init marker framework
        #

        # needed for cleanup
        self._tags = []
        self._marker_types = {}    # {marker type -> MarkerTypeRecord object}
        self._markers = {}        # { marker id -> marker object }

        self._window_context = self._tab_decorator._window_decorator._window_context
        self._window_context.create_editor_views(self, file)

        self._offset = None        # used by move_cursor

        self.__view_signal_handlers = [
                self._text_view.connect("button-press-event", self.__on_button_pressed),
                self._text_view.connect("key-release-event", self.__on_key_released),
                self._text_view.connect("button-release-event", self.__on_button_released)]

        self.__buffer_change_timestamp = time.time()
        self.__buffer_signal_handlers = [
                self._text_buffer.connect("changed", self.__on_buffer_changed)]

        # dnd support
        if len(self.dnd_extensions) > 0:
            self.__view_signal_handlers.append(
                    self._text_view.connect("drag-data-received", self.__on_drag_data_received))

        # start life-cycle for subclass
        self.init(file, self._window_context)

    def __on_buffer_changed(self, text_buffer):
        """
        Store the timestamp of the last buffer change
        """
        self.__buffer_change_timestamp = time.time()

    def __on_drag_data_received(self, widget, context, x, y, data, info, timestamp):
        """
        The drag destination received the data from the drag operation

        @param widget: the widget that received the signal
        @param context: the Gdk.DragContext
        @param x: the X position of the drop
        @param y: the Y position of the drop
        @param data: a Gtk.SelectionData object
        @param info: an integer ID for the drag
        @param timestamp: the time of the drag event
        """
        LOG.debug("drag-data-received")

        files = []
        match = False

        for uri in data.get_uris():
            file = File(uri)
            files.append(file)
            if file.extension.lower() in self.dnd_extensions:
                match = True

        if match:
            self.drag_drop_received(files)

    def __on_key_released(self, *args):
        """
        This helps to call 'move_cursor'
        """
        offset = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert()).get_offset()
        if offset != self._offset:
            self._offset = offset
            self.on_cursor_moved(offset)

    def __on_button_released(self, *args):
        """
        This helps to call 'move_cursor'
        """
        offset = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert()).get_offset()
        if offset != self._offset:
            self._offset = offset
            self.on_cursor_moved(offset)

    def __on_button_pressed(self, text_view, event):
        """
        Mouse button has been pressed on the TextView
        """
        if event.button == 3:    # right button
            x, y = text_view.get_pointer()
            x, y = text_view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, x, y)
            it = text_view.get_iter_at_location(x, y)

            LOG.debug("Right button pressed at offset %s" % it.get_offset())

            #
            # find Marker at this position
            #
            while True:
                for mark in it.get_marks():
                    name = mark.get_name()

                    LOG.debug("Found TextMark '%s' at offset %s" % (name, it.get_offset()))

                    if name:
                        if name in list(self._markers.keys()):
                            marker = self._markers[name]
                            return self.on_marker_activated(marker, event)
                        else:
                            LOG.warning("No marker found for TextMark '%s'" % name)
                    else:
                        # FIXME: this is not safe - use another symbol for right boundaries!
                        LOG.debug("Unnamed TextMark found, outside of any Markers")
                        return

                # move left by one char and continue
                if not it.backward_char():
                    # start of buffer reached
                    return

        elif event.button == 1 and event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            x, y = text_view.get_pointer()
            x, y = text_view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, x, y)
            it = text_view.get_iter_at_location(x, y)
            # notify subclass
            self._ctrl_left_clicked(it)

    def _ctrl_left_clicked(self, it):
        """
        Left-clicked on the editor with Ctrl modifier key pressed
        @param it: the Gtk.TextIter at the clicked position
        """

    @property
    def file(self):
        return self._file

    @property
    def tab_decorator(self):
        return self._tab_decorator

    def delete_at_cursor(self, offset):
        """
        Delete characters relative to the cursor position:

        offset < 0        delete characters from offset to cursor
        offset > 0        delete characters from cursor to offset
        """
        start = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
        end = self._text_buffer.get_iter_at_offset(start.get_offset() + offset)
        self._text_buffer.delete(start, end)

    # methods/properties to be used/overridden by the subclass

    @property
    def extensions(self):
        """
        Return a list of extensions for which this Editor is to be activated
        """
        raise NotImplementedError

    def drag_drop_received(self, files):
        """
        To be overridden

        @param files: a list of File objects dropped on the Editor
        """
        pass

    @property
    def initial_timestamp(self):
        """
        Return an initial reference timestamp (this just has to be smaller than
        every value returned by current_timestamp)
        """
        return 0

    @property
    def current_timestamp(self):
        """
        Return the current timestamp for buffer change recognition
        """
        return time.time()

    def content_changed(self, reference_timestamp):
        """
        Return True if the content of this Editor has changed since a given
        reference timestamp (this must be a timestamp as returned by current_timestamp)
        """
        return self.__buffer_change_timestamp > reference_timestamp

    @property
    def charset(self):
        """
        Return the character set used by this Editor
        """
        return self._text_buffer.get_file().get_encoding().get_charset()

    @property
    def content(self):
        """
        Return the string contained in the TextBuffer
        """
        return self._text_buffer.get_text(self._text_buffer.get_start_iter(),
                                    self._text_buffer.get_end_iter(), False)

    @property
    def content_at_left_of_cursor(self):
        """
        Only return the content at left of the cursor
        """
        end_iter = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
        return self._text_buffer.get_text(self._text_buffer.get_start_iter(),
                                    end_iter, False)

    def insert(self, source):
        """
        This may be overridden to catch special types like LaTeXSource
        """
        LOG.debug("insert(%s)" % source)

        SnippetManager().insert_at_cursor(self, str(source))

        # grab the focus again (necessary e.g. after symbol insert)
        self._text_view.grab_focus()

    def insert_at_offset(self, offset, string, scroll=False):
        """
        Insert a string at a certain offset

        @param offset: a positive int
        @param string: a str
        @param scroll: if True the view is scrolled to the insert position
        """
        iter = self._text_buffer.get_iter_at_offset(offset)
        self._text_buffer.insert(iter, str(string))

        if scroll:
            self._text_view.scroll_to_iter(iter, .25, False, 0.5, 0.5)

        # grab the focus again (necessary e.g. after symbol insert)
        self._text_view.grab_focus()

    def append(self, string):
        """
        Append some source (only makes sense with simple string) and scroll to it

        @param string: a str
        """
        self._text_buffer.insert(self._text_buffer.get_end_iter(), str(string))
        self._text_view.scroll_to_iter(self._text_buffer.get_end_iter(), .25, False, 0.5, 0.5)

        # grab the focus again (necessary e.g. after symbol insert)
        self._text_view.grab_focus()

    @property
    def indentation(self):
        """
        Return the indentation string of the line at the cursor
        """
        i_start = self._text_buffer.get_iter_at_mark(self._text_buffer.get_insert())
        i_start.set_line_offset(0)

        i_end = i_start.copy()
        i_end.forward_to_line_end()
        string = self._text_buffer.get_text(i_start, i_end, False)

        match = self.__PATTERN_INDENT.match(string)
        if match:
            return match.group()
        else:
            return ""

    def select(self, start_offset, end_offset):
        """
        Select a range of text and scroll the view to the right position
        """
        # select
        it_start = self._text_buffer.get_iter_at_offset(start_offset)
        it_end = self._text_buffer.get_iter_at_offset(end_offset)
        self._text_buffer.select_range(it_start, it_end)
        # scroll
        self._text_view.scroll_to_iter(it_end, .25, False, 0.5, 0.5)

    def select_lines(self, start_line, end_line=None):
        """
        Select a range of lines in the text

        @param start_line: the first line to select (counting from 0)
        @param end_line: the last line to select (if None only the first line is selected)
        """
        it_start = self._text_buffer.get_iter_at_line(start_line)
        if end_line:
            it_end = self._text_buffer.get_iter_at_line(end_line)
        else:
            it_end = it_start.copy()
        it_end.forward_to_line_end()
        # select
        self._text_buffer.select_range(it_start, it_end)
        # scroll
        self._text_view.scroll_to_iter(it_end, .25, False, 0.5, 0.5)

    #
    # markers are used for highlighting (anonymous)
    #

    def register_marker_type(self, marker_type, background_color, anonymous=True):
        """
        @param marker_type: a string
        @param background_color: a hex color
        @param anonymous: markers of an anonymous type may not be activated and do not get a unique ID
        """
        assert not marker_type in list(self._marker_types.keys())

        # create Gtk.TextTag
        tag = self._text_buffer.create_tag(marker_type, background=background_color)

        self._tags.append(tag)

        # create a MarkerTypeRecord for this type
        self._marker_types[marker_type] = self.MarkerTypeRecord(tag, anonymous)

    def create_marker(self, marker_type, start_offset, end_offset):
        """
        Mark a section of the text

        @param marker_type: type string
        @return: a Marker object if the type is not anonymous or None otherwise
        """

        # check offsets
        if start_offset < 0:
            LOG.error("create_marker(): start offset out of range (%s < 0)" % start_offset)
            return

        buffer_end_offset = self._text_buffer.get_end_iter().get_offset()

        if end_offset > buffer_end_offset:
            LOG.error("create_marker(): end offset out of range (%s > %s)" % (end_offset, buffer_end_offset))

        type_record = self._marker_types[marker_type]

        # hightlight
        left = self._text_buffer.get_iter_at_offset(start_offset)
        right = self._text_buffer.get_iter_at_offset(end_offset)
        self._text_buffer.apply_tag_by_name(marker_type, left, right)

        if type_record.anonymous:
            # create TextMarks
            left_mark = self._text_buffer.create_mark(None, left, True)
            right_mark = self._text_buffer.create_mark(None, right, False)

            # create Marker object
            marker = self.Marker(left_mark, right_mark, None, marker_type)

            # store Marker
            type_record.markers.append(marker)

            return None
        else:
            # create unique marker id
            id = str(uuid.uuid1())

            # create Marker object and put into map
            left_mark = self._text_buffer.create_mark(id, left, True)
            right_mark = self._text_buffer.create_mark(None, right, False)
            marker = self.Marker(left_mark, right_mark, id, marker_type)

            # store Marker
            self._markers[id] = marker
            type_record.markers.append(marker)

            return marker

    def remove_marker(self, marker):
        """
        @param marker: the Marker object to remove
        """
        # create TextIters from TextMarks
        left_iter = self._text_buffer.get_iter_at_mark(marker.left_mark)
        right_iter = self._text_buffer.get_iter_at_mark(marker.right_mark)

        # remove TextTag
        type_record = self._marker_types[marker.type]
        self._text_buffer.remove_tag(type_record.tag, left_iter, right_iter)

        # remove TextMarks
        self._text_buffer.delete_mark(marker.left_mark)
        self._text_buffer.delete_mark(marker.right_mark)

        # remove Marker from MarkerTypeRecord
        i = type_record.markers.index(marker)
        del type_record.markers[i]

        # remove from id map
        del self._markers[marker.id]

    def remove_markers(self, marker_type):
        """
        Remove all markers of a certain type
        """
        type_record = self._marker_types[marker_type]

        for marker in type_record.markers:
            assert not marker.left_mark.get_deleted()
            assert not marker.right_mark.get_deleted()

            # create TextIters from TextMarks
            left_iter = self._text_buffer.get_iter_at_mark(marker.left_mark)
            right_iter = self._text_buffer.get_iter_at_mark(marker.right_mark)

            # remove TextTag
            self._text_buffer.remove_tag(type_record.tag, left_iter, right_iter)

            # remove TextMarks
            self._text_buffer.delete_mark(marker.left_mark)
            self._text_buffer.delete_mark(marker.right_mark)

            if not type_record.anonymous:
                # remove Marker from id map
                del self._markers[marker.id]

        # remove markers from MarkerTypeRecord
        type_record.markers = []

    def replace_marker_content(self, marker, content):
        # get TextIters
        left = self._text_buffer.get_iter_at_mark(marker.left_mark)
        right = self._text_buffer.get_iter_at_mark(marker.right_mark)

        # replace
        self._text_buffer.delete(left, right)
        left = self._text_buffer.get_iter_at_mark(marker.left_mark)
        self._text_buffer.insert(left, content)

        # remove Marker
        self.remove_marker(marker)

    def on_marker_activated(self, marker, event):
        """
        A marker has been activated

        To be overridden

        @param id: id of the activated marker
        @param event: the GdkEvent of the mouse click (for raising context menus)
        """

    @property
    def completion_handlers(self):
        """
        To be overridden

        @return: a list of objects implementing CompletionHandler
        """
        return []

    def init(self, file, context):
        """
        @param file: File object
        @param context: WindowContext object
        """

    def on_save(self):
        """
        The file has been saved to its original location
        """

    def on_cursor_moved(self, offset):
        """
        The cursor has moved
        """

    def destroy(self):
        """
        The edited file has been closed or saved as another file
        """

        # disconnect signal handlers
        for handler in self.__view_signal_handlers:
            self._text_view.disconnect(handler)

        for handler in self.__buffer_signal_handlers:
            self._text_buffer.disconnect(handler)

        # delete the tags that were created for markers
        table = self._text_buffer.get_tag_table()
        for tag in self._tags:
            table.remove(tag)

        # destroy the views associated to this editor
        for i in self._window_context.editor_views[self]:
            self._window_context.editor_views[self][i].destroy()
        del self._window_context.editor_views[self]

        # unreference the tab decorator
        del self._tab_decorator

        # destroy the completion distributor
        if self._completion_distributor != None:
            self._completion_distributor.destroy()
        del self._completion_distributor

        # unreference the window context
        del self._window_context

# ex:ts=4:et:
