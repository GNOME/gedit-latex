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
bibtex.parser

BibTeX parser and object model
"""

#
##
## async parser feature
##
#if __name__ == "__main__":
#    #
#    # The script has been started in a shell process
#    #
#    # Parse the file passed as first argument and write the model
#    # as a pickled object to STDOUT
#    #
#    import sys
#
#    # TODO: fetch issues and pass them together with the model in a special
#    # transfer object
#
#    plugin_path = sys.argv[1]
#    filename = sys.argv[2]
#
#    sys.path.append(plugin_path)
#    sys.path.append("/home/michael/.gnome2/gedit/plugins")
#
#    from issues import MockIssueHandler
#    from base.file import File
#
#    model = BibTeXParser().parse_async(open(filename).read(), filename)
#else:
#    #
#    # normal package code...
#    #

from xml.sax.saxutils import escape

from ..issues import Issue
from ..preferences import Preferences

class Token(object):
    """
    A BibTeX token
    """

    AT, TEXT, COMMA, EQUALS, QUOTE, HASH, CURLY_OPEN, CURLY_CLOSE, ROUND_OPEN, ROUND_CLOSE = list(range(10))

    def __init__(self, type, offset, value):
        self.type = type
        self.offset = offset
        self.value = value

    def __str__(self):
        return "<Token type='%s' value='%s' @%s>" % (self.type, self.value, self.offset)


from ..util import StringReader
from ..util import open_info


class BibTeXLexer(object):
    """
    BibTeX lexer. We only separate text from special tokens here and
    apply escaping.
    """

    _TERMINALS_TOKENS = {"@" : Token.AT, "," : Token.COMMA, "=" : Token.EQUALS,
                         "{" : Token.CURLY_OPEN, "}" : Token.CURLY_CLOSE, "\"" : Token.QUOTE,
                         "#" : Token.HASH, "(" : Token.ROUND_OPEN, ")" : Token.ROUND_CLOSE}

    _TERMINALS = set(_TERMINALS_TOKENS.keys())

    def __init__(self, string):
        self._reader = StringReader(string)

    def __iter__(self):
        return self

    def __next__(self):
        """
        Return the next token
        """

        escaping = False
        textBuilder = None
        textStart = None

        while True:
            c = self._reader.read()

            if not escaping and c in self._TERMINALS:
                if textBuilder is not None:
                    self._reader.unread(c)
                    text = "".join(textBuilder)
                    textBuilder = None
                    return Token(Token.TEXT, textStart, text)

                return Token(self._TERMINALS_TOKENS[c], self._reader.offset - 1, c)

            else:
                if textBuilder is None:
                    textStart = self._reader.offset
                    textBuilder = [c]
                else:
                    textBuilder.append(c)

                if c == "\\":
                    escaping = True
                else:
                    escaping = False


class BibTeXParser(object):
    """
    A fast and safe BibTeX parser that generates a handy model on the fly.

    Instead of raising exceptions this parser uses an IIssueHandler.
    """

    _OUTSIDE, _TYPE, _AFTER_TYPE, _AFTER_STRING_TYPE, _KEY, _STRING_KEY, _AFTER_KEY, _AFTER_STRING_KEY, \
            _STRING_VALUE, _QUOTED_STRING_VALUE, _FIELD_NAME, _AFTER_FIELD_NAME, _FIELD_VALUE, _EMBRACED_FIELD_VALUE, \
            _QUOTED_FIELD_VALUE = list(range(15))

    def __init__(self, quiet=False):
        self._quiet = quiet
        self._max_size_info_shown = False

        self._state = None
        self._type = None
        self._constant = None
        self._entry = None
        self._file = None
        self._closingDelimiter = None
        self._document = None
        self._field = None
        self._value = None
        self._stack = None

    #
    # callables for each state of the parser
    #

    def _on_outside(self, token, file, issue_handler):
        if token.type == Token.AT:
            self._state = self._TYPE

    def _on_type(self, token, file, issue_handler):
        if token.type == Token.TEXT:
            self._type = token.value.strip()

            if self._type.lower() == "string" :
                self._constant = Constant()
                self._state = self._AFTER_STRING_TYPE
            elif self._type.lower() in ["preamble", "comment"]:        # simply skip PREAMBLE and COMMENT entries
                self._state = self._OUTSIDE
            else:
                self._entry = Entry()
                self._entry.type = self._type
                self._entry.start = token.offset - 2
                self._state = self._AFTER_TYPE
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> in entry type" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._entry = None
            self._state = self._OUTSIDE

    def _on_after_type(self, token, file, issue_handler):
        if token.type == Token.CURLY_OPEN:
            self._closingDelimiter = Token.CURLY_CLOSE
            self._state = self._KEY
        elif token.type == Token.ROUND_OPEN:
            self._closingDelimiter = Token.ROUND_CLOSE
            self._state = self._KEY
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> after entry type" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._entry = None
            self._state = self._OUTSIDE

    def _on_after_string_type(self, token, file, issue_handler):
        if token.type == Token.CURLY_OPEN:
            self._closingDelimiter = Token.CURLY_CLOSE
            self._state = self._STRING_KEY
        elif token.type == Token.ROUND_OPEN:
            self._closingDelimiter = Token.ROUND_CLOSE
            self._state = self._STRING_KEY
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> after string type" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._constant = None
            self._state = self._OUTSIDE

    def _on_key(self, token, file, issue_handler):
        if token.type == Token.TEXT:
            self._entry.key = token.value.strip()
            self._state = self._AFTER_KEY
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> in entry key" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._entry = None
            self._state = self._OUTSIDE

    def _on_string_key(self, token, file, issue_handler):
        if token.type == Token.TEXT:
            self._constant.name = token.value.strip()
            self._state = self._AFTER_STRING_KEY
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> in string key" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._constant = None
            self._state = self._OUTSIDE

    def _on_after_key(self, token, file, issue_handler):
        if token.type == Token.COMMA:
            self._state = self._FIELD_NAME
        elif token.type == self._closingDelimiter:
            self._entry.end = token.offset + 1
            self._document.entries.append(self._entry)
            self._state = self._OUTSIDE
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> after entry key" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._entry = None
            self._state = self._OUTSIDE

    def _on_after_string_key(self, token, file, issue_handler):
        if token.type == Token.EQUALS:
            self._state = self._STRING_VALUE
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> after string key" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._constant = None
            self._state = self._OUTSIDE

    def _on_string_value(self, token, file, issue_handler):
        if token.type == Token.QUOTE:
            self._state = self._QUOTED_STRING_VALUE

    def _on_quoted_string_value(self, token, file, issue_handler):
        if token.type == Token.TEXT:
            self._constant.value = token.value
            self._document.constants.append(self._constant)
            self._state = self._OUTSIDE

    def _on_field_name(self, token, file, issue_handler):
        if token.type == Token.TEXT:

            if token.value.isspace():
                return

            self._field = Field()
            self._field.name = token.value.strip()
            self._state = self._AFTER_FIELD_NAME
        elif token.type == self._closingDelimiter:
            self._entry.end = token.offset + 1
            self._document.entries.append(self._entry)
            self._state = self._OUTSIDE
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> in field name" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._entry = None
            self._state = self._OUTSIDE

    def _on_after_field_name(self, token, file, issue_handler):
        if token.type == Token.EQUALS:
            self._state = self._FIELD_VALUE
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> after field name" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._entry = None
            self._state = self._OUTSIDE

    def _on_field_value(self, token, file, issue_handler):
        # TODO: we may not recognize something like "author = ," as an error

        if token.value.isspace():
            return

        if token.type == Token.TEXT:
            self._value = token.value.strip()
            if self._value.isdigit():
                self._field.value.append(NumberValue(self._value))
            else:
                self._field.value.append(ConstantReferenceValue(self._value))
        elif token.type == Token.CURLY_OPEN:
            self._value = ""
            self._stack = [Token.CURLY_OPEN]
            self._state = self._EMBRACED_FIELD_VALUE
        elif token.type == Token.QUOTE:
            self._value = ""
            #stack = [Token.QUOTE]
            self._state = self._QUOTED_FIELD_VALUE
        elif token.type == Token.COMMA:
            self._entry.fields.append(self._field)
            self._state = self._FIELD_NAME
        elif token.type == self._closingDelimiter:
            self._entry.fields.append(self._field)
            self._entry.end = token.offset + 1
            self._document.entries.append(self._entry)
            self._state = self._OUTSIDE
        elif token.type == Token.HASH:
            pass
        else:
            issue_handler.issue(Issue("Unexpected token <b>%s</b> in field value" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
            self._entry = None
            self._state = self._OUTSIDE

    def _on_embraced_field_value(self, token, file, issue_handler):
        if token.type == Token.CURLY_OPEN:
            self._stack.append(Token.CURLY_OPEN)
            self._value += token.value
        elif token.type == Token.CURLY_CLOSE:
            try:
                while self._stack[-1] != Token.CURLY_OPEN:
                    self._stack.pop()
                self._stack.pop()

                if len(self._stack) == 0:
                    self._field.value.append(StringValue(self._value))
                    self._state = self._FIELD_VALUE
                else:
                    self._value += token.value

            except IndexError:
                issue_handler.issue(Issue("Unexpected token <b>%s</b> in field value" % escape(token.value),
                                    token.offset, token.offset + 1, file, Issue.SEVERITY_ERROR))
                self._entry = None
                self._state = self._OUTSIDE
        else:
            self._value += token.value

    def _on_quoted_field_value(self, token, file, issue_handler):
        if token.type == Token.QUOTE:
            self._field.value.append(StringValue(self._value))
            self._state = self._FIELD_VALUE
        else:
            self._value += token.value

    def parse(self, string, file, issue_handler):
        """
        Parse a BibTeX content
        @param string: the content to be parsed
        @param file: the File object containing the BibTeX
        @param issue_handler: an object implementing IIssueHandler
        """
        self._document = Document()

        # respect maximum BibTeX file size
        max_size_kb = int(Preferences().get("maximum-bibtex-size"))
        length = len(string)

        if length > max_size_kb * 1024:
            if not self._quiet and not self._max_size_info_shown:
                open_info("BibTeX file will not be parsed", "The maximum size of BibTeX files to parse is set to %s KB." % max_size_kb)
                self._max_size_info_shown = True
            return self._document

        # parse
        self._state = self._OUTSIDE

        #
        # use this hash table instead of endless if...elif statements
        #
        callables = {
                self._OUTSIDE : self._on_outside,
                self._TYPE : self._on_type,
                self._AFTER_TYPE : self._on_after_type,
                self._AFTER_STRING_TYPE : self._on_after_string_type,
                self._KEY : self._on_key,
                self._STRING_KEY : self._on_string_key,
                self._AFTER_KEY : self._on_after_key,
                self._AFTER_STRING_KEY : self._on_after_string_key,
                self._STRING_VALUE : self._on_string_value,
                self._QUOTED_STRING_VALUE : self._on_quoted_string_value,
                self._FIELD_NAME : self._on_field_name,
                self._AFTER_FIELD_NAME : self._on_after_field_name,
                self._FIELD_VALUE : self._on_field_value,
                self._EMBRACED_FIELD_VALUE : self._on_embraced_field_value,
                self._QUOTED_FIELD_VALUE : self._on_quoted_field_value
        }

        for token in BibTeXLexer(string):
            callables[self._state].__call__(token, file, issue_handler)

        return self._document

#
# BibTeX object model
#

class Value(object):
    def __init__(self, text):
        self.text = text

    MAX_MARKUP_LENGTH = 50

    @property
    def markup(self):
        text = self.text

        # remove braces
        if text.startswith("{{") and text.endswith("}}"):
            text = text[2:-2]
        elif text.startswith("{") and text.endswith("}"):
            text = text[1:-1]
        elif text.startswith("\\url{") and text.endswith("}"):
            text = text[5:-1]

        # truncate
        if len(text) > self.MAX_MARKUP_LENGTH:
            text = text[:self.MAX_MARKUP_LENGTH] + "..."

        # remove newlines
        text = text.replace("\n", "")

        # escape problematic characters
        text = escape(text)

        return text

    def __str__(self):
        return "<Value text='%s'>" % self.text


class NumberValue(Value):
    def __str__(self):
        return "<NumberValue text='%s'>" % self.text


class StringValue(Value):
    def __str__(self):
        return "<StringValue text='%s'>" % self.text


class ConstantReferenceValue(Value):
    @property
    def markup(self):
        return "<i>%s</i>" % escape(self.text)

    def __str__(self):
        return "<ReferenceValue text='%s'>" % self.text


class Field(object):
    def __init__(self):
        self.name = None
        self.value = []

    @property
    def valueMarkup(self):
        return " ".join([v.markup for v in self.value])

    @property
    def valueString(self):
        return " ".join([v.text for v in self.value])

    def __str__(self):
        return "<Field name='%s' value='%s' />" % (self.name, self.valueString)


class Entry(object):
    def __init__(self):
        self.type = None
        self.key = None
        self.start = None
        self.end = None
        self.fields = []

    def findField(self, name):
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError

    def __str__(self):
        s = "<Entry type='%s' key='%s'>\n" % (self.type, self.key)
        for field in self.fields:
            s += "\t" + str(field) + "\n"
        s += "</Entry>"
        return s


class Constant(object):
    """
    A BibTeX string constant
    """
    def __init__(self):
        self.name = None
        self.value = None


class Document(object):
    def __init__(self):
        self.entries = []
        self.constants = []

    def __str__(self):
        s = "<Document>\n"
        for entry in self.entries:
            s += str(entry) + "\n"
        s += "</Document>"
        return s


#    #
#    # async parser feature
#    #
#
#    # TODO: put the __main__ part in another file
#
#    import pickle
#    import os
#
#    from ..tools.util import Process
#    from ..base.resources import PLUGIN_PATH
#
#    # TODO: time pickle.loads() and pickle.dump()
#    # TODO: support Process.abort()
#
#    class AsyncParserRunner(Process):
#
#        __log = getLogger("AsyncParserRunner")
#
#        def parse(self, file):
#            self.__pickled_object = None
#
#            source_path = PLUGIN_PATH + "/src"
#            self.__log.debug("chdir: %s" % source_path)
#            os.chdir(source_path)
#
#            self.execute("python %s/bibtex/parser.py %s %s" % (source_path, source_path, file.path))
#
#        def _on_stdout(self, text):
#            # Process._on_stdout
#            self.__pickled_object = text
#
#        def _on_stderr(self, text):
#            # Process._on_stderr
#            self.__log.debug("_on_stderr: %s" % text)
#
#        def _on_abort(self):
#            # Process._on_abort
#            pass
#
#        def _on_exit(self, condition):
#            # Process._on_exit
#            self.__log.debug("_on_exit")
#
#            model = None
#
#            if condition:
#                self.__log.error("failed")
#            else:
#                model = pickle.loads(self.__pickled_object)
#
#            self._on_parser_finished(model)
#
#        def _on_parser_finished(self, model):
#            """
#            To be overridden by the subclass
#            """






# ex:ts=4:et:
