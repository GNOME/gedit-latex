# -*- coding: utf-8 -*-

#  Copyright (C) 2011 - Ignacio Casal Quinteiro
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.

from .singleton import Singleton
import logging

LOG = logging.getLogger(__name__)


class SnippetManager(Singleton):
    def __init_once__(self):
        pass

    def insert(self, editor, iter, text):
        view = editor.tab_decorator.tab.get_view()
        window = view.get_toplevel()
        bus = window.get_message_bus()

        if bus.is_registered('/plugins/snippets', 'parse-and-activate'):
            bus.send('/plugins/snippets', 'parse-and-activate',
                     snippet=text, iter=iter, view=view)
            LOG.info("Inserted using snippets plugin")
        else:
            buf = view.get_buffer()

            buf.begin_user_action()
            buf.insert(iter, text)
            buf.end_user_action()
            LOG.info("Inserted without snippets plugin")

    def insert_at_cursor(self, editor, text):
        buf = editor.tab_decorator.tab.get_document()
        insert = buf.get_insert()
        iter = buf.get_iter_at_mark(insert)
        self.insert(editor, iter, text)

# vi:ex:ts=4:et:
