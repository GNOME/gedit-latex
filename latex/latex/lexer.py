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
latex.lexer
"""

class StringListener(object):
    """
    Recognizes a string in a stream of characters
    """
    def __init__(self, string, any_position=True):
        """
        @param string: the character sequence to be recognized
        @param any_position: if True the sequence may occur at any position in
                the stream, if False it must occur at the start
        """
        self._string = string
        self._last = len(string)
        self._pos = 0
        self._any_position = any_position

        self._active = True

    def put(self, char):
        """
        Returns True if the string is recognized
        """
        if not self._active:
            return False

        if char == self._string[self._pos]:
            self._pos += 1

            if self._pos == self._last:
                return True
        else:
            if self._any_position:
                self._pos = 0
            else:
                self._active = False

        return False


from ..util import StringReader


class Token(object):
    """
    A Token returned by the Lexer
    """

    COMMAND, TEXT, COMMENT, VERBATIM, BEGIN_CURLY, END_CURLY, BEGIN_SQUARE, END_SQUARE = list(range(8))

    def __init__(self, type, offset=None, value=None):
        self.type = type
        self.offset = offset
        self.value = value

    @property
    def xml(self):
        if self.type == self.COMMAND:
            return "<t:command>%s</t:command>" % self.value
        elif self.type == self.TEXT:
            return "<t:text>%s</t:text>" % self.value
        elif self.type == self.VERBATIM:
            return "<t:verbatim>%s</t:verbatim>" % self.value
        elif self.type == self.COMMENT:
            return "<t:comment>%s</t:comment>" % self.value
        else:
            return "<t:terminal />"


class Lexer(object):
    """
    LaTeX lexer
    """

    # TODO: redesign and optimize this from a DFA

    # states of the lexer
    _DEFAULT, _BACKSLASH, _COMMAND, _TEXT, _COMMENT, _PRE_VERB, _VERB, _VERBATIM = list(range(8))

    _SPECIAL = set(["&", "$", "{", "}", "[", "]", "%", "#", "_", "\\"])

    _TERMINALS = set(["{", "}", "[", "]"])
    _TERMINALS_MAP = {"{" : Token.BEGIN_CURLY, "}" : Token.END_CURLY,
                      "[" : Token.BEGIN_SQUARE, "]" : Token.END_SQUARE}

    _VERBATIM_ENVIRONS = set(["verbatim", "verbatim*", "lstlisting", "lstlisting*"])


    # additional states for recognizing "\begin{verbatim}"
    _VERBATIM_DEFAULT, _VERBATIM_BEGIN, _VERBATIM_BEGIN_CURLY, _VERBATIM_BEGIN_CURLY_ENVIRON = list(range(4))


    def __init__(self, string, skipWs=True, skipComment=False):
        self._reader = StringReader(string)

        self._skipWs = skipWs
        self._skipComment = skipComment

        self._state = self._DEFAULT
        self._verbatimState = self._VERBATIM_DEFAULT

        self._eof = False
        self._tokenStack = []    # used to return a sequence of tokens after a verbatim ended

    def __iter__(self):
        return self

    def __next__(self):
        if self._eof:
            raise StopIteration

        # first empty the token stack
        if len(self._tokenStack):
            return self._tokenStack.pop()

        while True:
            try:
                char = self._reader.read()

                if self._state == self._DEFAULT:
                    if char == "\\":
                        self._state = self._BACKSLASH
                        self._verbatimState = self._VERBATIM_DEFAULT
                        self._startOffset = self._reader.offset - 1

                    elif char == "%":
                        self._state = self._COMMENT
                        self._verbatimState = self._VERBATIM_DEFAULT
                        self._startOffset = self._reader.offset - 1
                        if not self._skipComment:
                            self._text = []

                    elif char in self._TERMINALS:
                        if self._verbatimState == self._VERBATIM_BEGIN and char == "{":
                            self._verbatimState = self._VERBATIM_BEGIN_CURLY

                        elif self._verbatimState == self._VERBATIM_BEGIN_CURLY_ENVIRON and char == "}":
                            # we have "\begin{verbatim}"
                            self._verbatimState = self._VERBATIM_DEFAULT
                            self._state = self._VERBATIM
                            self._text = []
                            self._startOffset = self._reader.offset
                            self._verbatimSequenceListener = StringListener("\\end{%s}" % self._verbatimEnviron)

                        else:
                            self._verbatimState = self._VERBATIM_DEFAULT

                        return Token(self._TERMINALS_MAP[char], self._reader.offset - 1)

                    else:
                        self._state = self._TEXT
                        self._startOffset = self._reader.offset - 1
                        self._text = [char]

                elif self._state == self._BACKSLASH:
                    if char in self._SPECIAL or char.isspace():
                        # this is a one-character-command, also whitespace is allowed
                        self._state = self._DEFAULT
                        return Token(Token.COMMAND, self._startOffset, char)

                    else:
                        self._state = self._COMMAND

                        self._verbListener = StringListener("verb", any_position=False)
                        self._verbListener.put(char)

                        self._text = [char]

                elif self._state == self._COMMENT:
                    if char == "\n":
                        self._state = self._DEFAULT
                        if not self._skipComment:
                            return Token(Token.COMMENT, self._startOffset, "".join(self._text))

                    else:
                        if not self._skipComment:
                            self._text.append(char)

                elif self._state == self._COMMAND:
                    if char in self._SPECIAL or char.isspace():

                        name = "".join(self._text)

                        # this is mostly false because \verb is mostly followed by something like |
                        if name == "verb":
                            self._state = self._VERB
                            self._verbDelimiter = char
                            self._startOffset = self._reader.offset - 1
                            self._text = [char]

                        elif name == "url":     # we handle "\url" just like "\verb"
                            self._state = self._VERB
                            self._verbDelimiter = "}"
                            self._startOffset = self._reader.offset - 1
                            self._text = []

                        else:
                            self._state = self._DEFAULT
                            self._reader.unread(char)

                            if name == "begin":
                                self._verbatimState = self._VERBATIM_BEGIN

                            return Token(Token.COMMAND, self._startOffset, name)

                    else:
                        if self._verbListener.put(char):
                            # we have "\verb"
                            self._state = self._PRE_VERB
                        else:
                            self._text.append(char)

                elif self._state == self._PRE_VERB:
                    self._state = self._VERB
                    self._verbDelimiter = char
                    self._startOffset = self._reader.offset - 1
                    self._text = []

                elif self._state == self._TEXT:
                    if char in self._SPECIAL:
                        self._state = self._DEFAULT
                        self._reader.unread(char)

                        text = "".join(self._text)

                        if self._skipWs and text.isspace():
                            continue
                        else:

                            if self._verbatimState == self._VERBATIM_BEGIN_CURLY:
                                # we have "\begin{" until now, handle verbatim environment

                                if text in self._VERBATIM_ENVIRONS:
                                    self._verbatimEnviron = text
                                    self._verbatimState = self._VERBATIM_BEGIN_CURLY_ENVIRON

                                else:
                                    self._verbatimState = self._VERBATIM_DEFAULT

                            return Token(Token.TEXT, self._startOffset, text)

                    else:
                        self._text.append(char)

                elif self._state == self._VERB:
                    if char == self._verbDelimiter:        # FIXME: \overbrace
                        self._state = self._DEFAULT

                        return Token(Token.VERBATIM, self._startOffset, "".join(self._text) + char)

                    else:
                        self._text.append(char)

                elif self._state == self._VERBATIM:
                    if self._verbatimSequenceListener.put(char):
                        self._state = self._DEFAULT

                        # TODO: calculate offsets
                        self._tokenStack = [ Token(Token.END_CURLY, 0),
                                             Token(Token.TEXT, 0, self._verbatimEnviron),
                                             Token(Token.BEGIN_CURLY, 0),
                                             Token(Token.COMMAND, 0, "end") ]

                        text = "".join(self._text)
                        text = text[5:]        # cut off "\end{"
                        return Token(Token.VERBATIM, self._startOffset, text)
                    else:
                        self._text.append(char)

                elif self._state == self._VERB:
                    # this char is the verb delimiter
                    # TODO: implement verbatim detection
                    pass

            except StopIteration:
                self._eof = True

                # evaluate final state
                if self._state == self._BACKSLASH:
                    return Token(Token.COMMAND, self._startOffset, "")

                elif self._state == self._COMMAND:
                    return Token(Token.COMMAND, self._startOffset, "".join(self._text))

                elif self._state == self._TEXT:
                    text = "".join(self._text)
                    if not (self._skipWs and text.isspace()):
                        return Token(Token.TEXT, self._startOffset, text)

                elif self._state == self._VERB:

                    # TODO: the document is malformed in this case, so the lexer should be
                    # able to produce issues, too
                    #
                    # TODO: return a VERBATIM token

                    return Token(Token.TEXT, self._startOffset, "".join(self._text))

                raise StopIteration
# ex:ts=4:et:
