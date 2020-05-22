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
latex.preview
"""

from ..file import File
from ..tools import Tool, Job, ToolRunner
from ..tools.postprocess import RubberPostProcessor, GenericPostProcessor
from ..issues import MockStructuredIssueHandler
from .environment import Environment

from gi.repository import GdkPixbuf

class ImageToolGenerator(object):
    """
    This generates Tools for rendering images from LaTeX source
    """

    FORMAT_PNG, FORMAT_JPEG, FORMAT_GIF = 1, 2, 3

    PNG_MODE_MONOCHROME, PNG_MODE_GRAYSCALE, PNG_MODE_RGB, PNG_MODE_RGBA = 1, 2, 3, 4

    def __init__(self):
        self._names = {self.FORMAT_PNG : "PNG Image", self.FORMAT_JPEG : "JPEG Image", self.FORMAT_GIF : "GIF Image"}
        self._png_modes = {self.PNG_MODE_MONOCHROME : "mono", self.PNG_MODE_GRAYSCALE : "gray", self.PNG_MODE_RGB : "16m",
                        self.PNG_MODE_RGBA : "alpha"}

        # default settings
        self.format = self.FORMAT_PNG
        self.png_mode = self.PNG_MODE_RGBA
        self.render_box = True
        self.resolution = int(round(Environment().screen_dpi))
        self.antialias_factor = 4
        self.open = False

    def generate(self):
        """
        @return: a Tool object
        """
        tool = Tool(label=self._names[self.format], jobs=[], description="", accelerator="", extensions=[])

        # use rubber to render a DVI
        tool.jobs.append(Job("rubber --force --short --inplace \"$filename\"", True, RubberPostProcessor))

        if self.render_box:
            # DVI -> PS

            # -D num    resolution in DPI
            # -q        quiet mode
            # -E        generate an EPSF file with a tight bounding box
            tool.jobs.append(Job("dvips -D %s -q -E -o \"$shortname.eps\" \"$shortname.dvi\"" % self.resolution, True, GenericPostProcessor))

            # EPS -> PNG|JPG|GIF
            if self.format == self.FORMAT_PNG:
                command = "$plugin_path/util/eps2png.pl -png%s -resolution=%s -antialias=%s \"$shortname.eps\"" % (self._png_modes[self.png_mode],
                                                                                self.resolution, self.antialias_factor)
            elif self.format == self.FORMAT_JPEG:
                command = "$plugin_path/util/eps2png.pl -jpeg -resolution=%s -antialias=%s \"$shortname.eps\"" % (self.resolution, self.antialias_factor)
            elif self.format == self.FORMAT_GIF:
                command = "$plugin_path/util/eps2png.pl -gif -resolution=%s -antialias=%s \"$shortname.eps\"" % (self.resolution, self.antialias_factor)

            tool.jobs.append(Job(command, True, GenericPostProcessor))
        else:
            # dvips
            tool.jobs.append(Job("dvips -D %s -q -o \"$shortname.ps\" \"$shortname.dvi\"" % self.resolution, True, GenericPostProcessor))

            if self.format == self.FORMAT_PNG:
                tool.jobs.append(Job("gs -q -dNOPAUSE -r%s -dTextAlphaBits=%s -dGraphicsAlphaBits=%s -sDEVICE=png%s -sOutputFile=$shortname.png $shortname.ps quit.ps"
                                    % (self.resolution, self.antialias_factor, self.antialias_factor, self._png_modes[self.png_mode]), True, GenericPostProcessor))
            elif self.format == self.FORMAT_JPEG:
                tool.jobs.append(Job("gs -q -dNOPAUSE -r%s -dTextAlphaBits=%s -dGraphicsAlphaBits=%s -sDEVICE=jpeg -sOutputFile=$shortname.jpg $shortname.ps quit.ps"
                                    % (self.resolution, self.antialias_factor, self.antialias_factor), True, GenericPostProcessor))
            elif self.format == self.FORMAT_GIF:
                tool.jobs.append(Job("gs -q -dNOPAUSE -r%s -dTextAlphaBits=%s -dGraphicsAlphaBits=%s -sDEVICE=ppm -sOutputFile=$shortname.ppm $shortname.ps quit.ps"
                                    % (self.resolution, self.antialias_factor, self.antialias_factor), True, GenericPostProcessor))
                # ppmtogif
                tool.jobs.append(Job("ppmtogif $shortname.ppm > $shortname.gif", True, GenericPostProcessor))

        if self.open:
            extension = {self.FORMAT_PNG : "png", self.FORMAT_JPEG: "jpg", self.FORMAT_GIF : "gif"}[self.format]
            tool.jobs.append(Job("gio open \"$shortname.%s\"" % extension, True, GenericPostProcessor))

        return tool


from tempfile import NamedTemporaryFile

class PreviewRenderer(ToolRunner):
    def render(self, source):
        """
        Render a preview image from LaTeX source

        @param source: some LaTeX source without \begin{document}
        """
        # create temp file with source
        self._temp_file = NamedTemporaryFile(mode="w", suffix=".tex")
        self._temp_file.write("\\documentclass{article}\\pagestyle{empty}\\begin{document}%s\\end{document}" % source)
        self._temp_file.flush()

        # generate Tool
        tool = ImageToolGenerator().generate()
        self._file = File(self._temp_file.name)
        issue_handler = MockStructuredIssueHandler()

        # run the Tool
        self.run(self._file, tool, issue_handler)

    def _on_tool_succeeded(self):
        # see ToolRunner._on_tool_succeeded
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(self._file.shortname + ".png")
        self.__cleanup()
        self._on_render_succeeded(pixbuf)

    def _on_tool_failed(self):
        # see ToolRunner._on_tool_failed
        self.__cleanup()
        self._on_render_failed()

    def __cleanup(self):
        """
        Remove the files created during the render process
        """
        # delete the temp file
        self._temp_file.close()

        # delete all files created during the build process
        for file in self._file.siblings:
            try:
                file.delete()
                self._log.debug("Removed %s" % file)
            except OSError:
                self._log.error("Failed to remove '%s'" % file)

    def _on_render_succeeded(self, pixbuf):
        """
        The rendering process has finished successfully

        @param pixbuf: a GdkPixbuf.Pixbuf containing the result image
        """

    def _on_render_failed(self):
        """
        The rendering process has failed
        """



# ex:ts=4:et:
