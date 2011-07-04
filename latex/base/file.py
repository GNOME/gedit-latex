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
import os.path
from glob import glob

import re
import urllib
import urlparse

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

    __log = getLogger("File")

    _DEFAULT_SCHEME = "file://"

    def __init__(self, uri):
        """
        @param uri: any URI, URL or local filename
        """
        if uri is None:
            raise ValueError("URI must not be None")

        self._uri = urlparse.urlparse(uri)
        if len(self._uri.scheme) == 0:
            # prepend default scheme if missing
            self._uri = urlparse.urlparse("%s%s" % (self._DEFAULT_SCHEME, uri))

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
        return urllib.url2pathname(self._uri.path)

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
        # TODO: urllib.quote doesn't support utf-8
        return fixurl(self._uri.geturl())

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

        except Exception, e:
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
        except Exception, e:
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

    def __cmp__(self, other):
        try:
            return self.basename.__cmp__(other.basename)
        except AttributeError:        # no File object passed or None
            # returning NotImplemented is bad because we have to
            # compare None with File
            return False


class Folder(File):

    # FIXME: a Folder is NOT a subclass of a File, both are a subclass of some AbstractFileSystemObject,
    # this is just a quick hack
    #
    # FIXME: but basically a Folder is a File so this class should not be needed

    __log = getLogger("Folder")

    @property
    def files(self):
        """
        Return File objects for all files in this Folder
        """
        try:
            filenames = glob("%s/*" % (self.path))
            files = [File(filename) for filename in filenames]
            return files

        except Exception, e:
            # as seen in Bug #2002630 the glob() call compiles a regex and so we must be prepared
            # for an exception from that because the shortname may contain regex characters

            # TODO: a more robust solution would be an escape() method for re

            self.__log.debug("files: %s" % e)

            return []

def fixurl(url):
    r"""From http://stackoverflow.com/questions/804336/best-way-to-convert-a-unicode-url-to-ascii-utf-8-percent-escaped-in-python/805166#805166 .
    Was named canonurl(). Comments added to the original are prefixed with ##.

    Return the canonical, ASCII-encoded form of a UTF-8 encoded URL, or ''
    if the URL looks invalid.

    >>> canonurl('    ')
    ''
    >>> canonurl('www.google.com')
    'http://www.google.com/'
    >>> canonurl('bad-utf8.com/path\xff/file')
    ''
    >>> canonurl('svn://blah.com/path/file')
    'svn://blah.com/path/file'
    >>> canonurl('1234://badscheme.com')
    ''
    >>> canonurl('bad$scheme://google.com')
    ''
    >>> canonurl('site.badtopleveldomain')
    ''
    >>> canonurl('site.com:badport')
    ''
    >>> canonurl('http://123.24.8.240/blah')
    'http://123.24.8.240/blah'
    >>> canonurl('http://123.24.8.240:1234/blah?q#f')
    'http://123.24.8.240:1234/blah?q#f'
    >>> canonurl('\xe2\x9e\xa1.ws')  # tinyarro.ws
    'http://xn--hgi.ws/'
    >>> canonurl('  http://www.google.com:80/path/file;params?query#fragment  ')
    'http://www.google.com:80/path/file;params?query#fragment'
    >>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5')
    'http://xn--hgi.ws/%E2%99%A5'
    >>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5/pa%2Fth')
    'http://xn--hgi.ws/%E2%99%A5/pa/th'
    >>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5/pa%2Fth;par%2Fams?que%2Fry=a&b=c')
    'http://xn--hgi.ws/%E2%99%A5/pa/th;par/ams?que/ry=a&b=c'
    >>> canonurl('http://\xe2\x9e\xa1.ws/\xe2\x99\xa5?\xe2\x99\xa5#\xe2\x99\xa5')
    'http://xn--hgi.ws/%E2%99%A5?%E2%99%A5#%E2%99%A5'
    >>> canonurl('http://\xe2\x9e\xa1.ws/%e2%99%a5?%E2%99%A5#%E2%99%A5')
    'http://xn--hgi.ws/%E2%99%A5?%E2%99%A5#%E2%99%A5'
    >>> canonurl('http://badutf8pcokay.com/%FF?%FE#%FF')
    'http://badutf8pcokay.com/%FF?%FE#%FF'
    >>> len(canonurl('google.com/' + 'a' * 16384))
    4096
    """
    # strip spaces at the ends and ensure it's prefixed with 'scheme://'
    url = url.strip()
    if not url:
        return ''
    if not urlparse.urlsplit(url).scheme:
        ## We usually deal with local files here
        url = 'file://' + url
        ## url = 'http://' + url

    # turn it into Unicode
    try:
        url = unicode(url, 'utf-8')
    except Exception, exc:   # UnicodeDecodeError, exc:
        ## It often happens that the url is already "python unicode" encoded
        if not str(exc) == "decoding Unicode is not supported":
            return ''  # bad UTF-8 chars in URL
        ## If the exception is indeed "decoding Unicode is not supported"
        ## this generally means that url is already unicode encoded,
        ## so we can just continue (see http://www.red-mercury.com/blog/eclectic-tech/python-mystery-of-the-day/ )

    # parse the URL into its components
    parsed = urlparse.urlsplit(url)
    scheme, netloc, path, query, fragment = parsed

    # ensure scheme is a letter followed by letters, digits, and '+-.' chars
    if not re.match(r'[a-z][-+.a-z0-9]*$', scheme, flags=re.I):
        return ''
    scheme = str(scheme)

    ## We mostly deal with local files here, and the following check
    ## would exclude all local files, so we drop it.
    # ensure domain and port are valid, eg: sub.domain.<1-to-6-TLD-chars>[:port]
    #~ match = re.match(r'(.+\.[a-z0-9]{1,6})(:\d{1,5})?$', netloc, flags=re.I)
    #~ if not match:
        #~ print "return 4"
        #~ return ''
    #~ domain, port = match.groups()
    #~ netloc = domain + (port if port else '')
    netloc = netloc.encode('idna')

    # ensure path is valid and convert Unicode chars to %-encoded
    if not path:
        path = '/'  # eg: 'http://google.com' -> 'http://google.com/'
    path = urllib.quote(urllib.unquote(path.encode('utf-8')), safe='/;')

    # ensure query is valid
    query = urllib.quote(urllib.unquote(query.encode('utf-8')), safe='=&?/')

    # ensure fragment is valid
    fragment = urllib.quote(urllib.unquote(fragment.encode('utf-8')))

    # piece it all back together, truncating it to a maximum of 4KB
    url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
    return url[:4096]

# ex:ts=4:et:
