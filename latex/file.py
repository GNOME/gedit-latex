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

from os import remove
from glob import glob

import logging
import os.path

import re
import urllib.request, urllib.parse, urllib.error

class File(object):
    """
    This is an object-oriented wrapper for all the os.* stuff. A File object
    represents the reference to a file.
    """

    # TODO: use Gio.File as underlying implementation

    @staticmethod
    def create_from_relative_path(relative_path, working_directory):
        """
        Create a File from a path relative to some working directory.

        File.create_from_relative_path('../sub/file.txt', '/home/michael/base') == File('/home/michael/sub/file.txt')

        @param relative_path: a relative path, e.g. '../../dir/myfile.txt'
        @param working_directory: an absolute directory to be used as the starting point for the relative path
        """
        absolute_path = os.path.abspath(os.path.join(working_directory, relative_path))
        return File(absolute_path)

    @staticmethod
    def is_absolute(path):
        return os.path.isabs(path)

    __log = logging.getLogger("File")

    _DEFAULT_SCHEME = "file://"

    def __init__(self, uri):
        """
        @param uri: any URI, URL or local filename
        """
        if uri is None:
            raise ValueError("URI must not be None")

        self._uri = urllib.parse.urlparse(uri)
        if len(self._uri.scheme) == 0:
            # prepend default scheme if missing
            self._uri = urllib.parse.urlparse("%s%s" % (self._DEFAULT_SCHEME, uri))

    def create(self, content=None):
        """
        Create a the File in the file system
        """
        f = open(self.path, "w")
        if content is not None:
            f.write(content)
        f.close()

    @property
    def path(self):
        """
        Returns '/home/user/image.jpg' for 'file:///home/user/image.jpg'
        """
        return urllib.request.url2pathname(self._uri.path)

    @property
    def extension(self):
        """
        Returns '.jpg' for 'file:///home/user/image.jpg'
        """
        return os.path.splitext(self.path)[1]

    @property
    def shortname(self):
        """
        Returns '/home/user/image' for 'file:///home/user/image.jpg'
        """
        return os.path.splitext(self.path)[0]

    @property
    def basename(self):
        """
        Returns 'image.jpg' for 'file:///home/user/image.jpg'
        """
        return os.path.basename(self.path)

    @property
    def shortbasename(self):
        """
        Returns 'image' for 'file:///home/user/image.jpg'
        """
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def dirname(self):
        """
        Returns '/home/user' for 'file:///home/user/image.jpg'
        """
        return os.path.dirname(self.path)

    @property
    def uri(self):
        return self._uri.geturl()

    @property
    def exists(self):
        return os.path.exists(self.path)

    @property
    def mtime(self):
        if self.exists:
            return os.path.getmtime(self.path)
        else:
            raise IOError("File not found")

    def find_neighbors(self, extension):
        """
        Find other files in the directory of this one having
        a certain extension

        @param extension: a file extension pattern like '.tex' or '.*'
        """

        # TODO: glob is quite expensive, find a simpler way for this

        try:
            filenames = glob("%s/*%s" % (self.dirname, extension))
            neighbors = [File(filename) for filename in filenames]
            return neighbors

        except Exception as e:
            # as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
            # for an exception from that because the shortname may contain regex characters

            # TODO: a more robust solution would be an escape() method for re

            self.__log.debug("find_neighbors: %s" % e)

            return []

    @property
    def siblings(self):
        """
        Find other files in the directory of this one having the same
        basename. This means for a file '/dir/a.doc' this method returns
        [ '/dir/a.tmp', '/dir/a.sh' ]
        """
        siblings = []
        try:
            filenames = glob("%s.*" % self.shortname)
            siblings = [File(filename) for filename in filenames]
        except Exception as e:
            # as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
            # for an exception from that because the shortname may contain regex characters

            # TODO: a more robust solution would be an escape() method for re

            self.__log.debug("find_siblings: %s" % e)
        return siblings

    def relativize(self, base, allow_up_level=False):
        """
        Relativize the path of this File against a base directory. That means that e.g.
        File("/home/user/doc.tex").relativize("/home") == "user/doc.tex"

        If up-level references are NOT allowed but necessary (e.g. base='/a/b/c', path='/a/b/d')
        then the absolute path is returned.

        @param base: the base directory to relativize against
        @param allow_up_level: allow up-level references (../../) or not
        """
        if allow_up_level:
            return os.path.relpath(self.path, base)
        else:
            # TODO: why do we need this?

            # relative path must be 'below' base path
            if len(base) >= len(self.path):
                return self.path
            if self.path[:len(base)] == base:
                # bases match, return relative part
                return self.path[len(base) + 1:]
            return self.path

    def relativize_shortname(self, base):
        """
        Relativize the path of this File and return only the shortname of the resulting
        relative path. That means that e.g.
        File("/home/user/doc.tex").relativize_shortname("/home") == "user/doc"

        This is just a convenience method.

        @param base: the base directory to relativize against
        """
        relative_path = self.relativize(base)
        return os.path.splitext(relative_path)[0]

    def delete(self):
        """
        Delete the File from the file system

        @raise OSError:
        """
        if self.exists:
            remove(self.path)
        else:
            raise IOError("File not found")

    def __eq__(self, other):
        """
        Override == operator
        """
        try:
            return self.uri == other.uri
        except AttributeError:        # no File object passed or None
            # returning NotImplemented is bad because we have to
            # compare None with File
            return False

    def __ne__(self, other):
        """
        Override != operator
        """
        return not self.__eq__(other)

    def __str__(self):
        return self.uri

    def __key__(self, file):
        try:
            return file.basename
        except AttributeError:        # no File object passed or None
            # returning NotImplemented is bad because we have to
            # compare None with File
            return None

    def __lt__(self, other):
        return self.__key__(self) < self.__key__(other)

    def __eq__(self, other):
        return self.__key__(self) == self.__key__(other)

    def __hash__(self):
        return hash(self.__key__(self))


class Folder(File):

    # FIXME: a Folder is NOT a subclass of a File, both are a subclass of some AbstractFileSystemObject,
    # this is just a quick hack
    #
    # FIXME: but basically a Folder is a File so this class should not be needed

    __log = logging.getLogger("Folder")

    @property
    def files(self):
        """
        Return File objects for all files in this Folder
        """
        try:
            filenames = glob("%s/*" % (self.path))
            files = [File(filename) for filename in filenames]
            return files

        except Exception as e:
            # as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
            # for an exception from that because the shortname may contain regex characters

            # TODO: a more robust solution would be an escape() method for re

            self.__log.debug("files: %s" % e)

            return []

# ex:ts=4:et:
