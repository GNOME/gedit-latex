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
latex.dialogs
"""

import logging
import tempfile
import os.path
import string

from gi.repository import Gtk, GdkPixbuf

from ..preferences import Preferences
from ..util import GladeInterface
from ..resources import Resources
from ..file import File, Folder

from .preview import PreviewRenderer, ImageToolGenerator
from .environment import Environment
from .listing import LanguagesParser

from . import LaTeXSource

class ComboBoxProxy:
    """
    This proxies a ComboBox widget:

    p = ComboBoxProxy(self.find_widget("myCombo"), "SomeSetting")
    p.add_option("thing_1", "First Thing")
    p.add_option("thing_2", "Second Thing")
    p.restore("thing_1")
    ...
    """
    def __init__(self, widget, key):
        self._widget = widget
        self._key = key
        self._preferences = Preferences()

        self._store = Gtk.ListStore(str, str)            # value, label
        self._widget.set_model(self._store)
        cell = Gtk.CellRendererText()
        self._widget.pack_start(cell, True)
        self._widget.add_attribute(cell, "markup", 1)

        self._options = []

    def restore(self, default):
        if default != None:
            restored_value = default
        else:
            restored_value = self._preferences.get(self._key)
        restored_index = 0
        i = 0
        for value, label in self._options:
            if value == restored_value:
                restored_index = i
                break
            i += 1
        self._widget.set_active(restored_index)

        self._widget.connect("changed", self._on_changed)

    def _on_changed(self, combobox):
        self._preferences.set(self._key, self.value)

    def add_option(self, value, label, show_value=True):
        """
        Add an option to the widget

        @param value: a unique value
        @param label: a label text that may contain markup
        """
        self._options.append((value, label))

        if show_value:
            if not value is None and len(value) > 0:
                label_markup = "%s <span color='%s'>%s</span>" % (value, self._preferences.get("light-foreground-color"), _(label))
            else:
                label_markup = "<span color='%s'>%s</span>" % (self._preferences.get("light-foreground-color"), _(label))
        else:
            label_markup = _(label)

        self._store.append([value, label_markup])

    @property
    def value(self):
        index = self._widget.get_active()
        return self._options[index][0]

class ChooseMasterDialog(GladeInterface):
    """
    Dialog for choosing a master file to a LaTeX fragment file
    """

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("choose_master_dialog.ui")

    def run(self, folder):
        """
        Runs the dialog and returns the selected filename

        @param folder: a folder to initially place the file chooser
        """
        dialog = self.find_widget("dialogSelectMaster")
        file_chooser_button = self.find_widget("filechooserbutton")
        file_chooser_button.set_current_folder(folder)

        if dialog.run() == 1:
            filename = file_chooser_button.get_filename()
        else:
            filename = None
        dialog.hide()

        return filename

class NewDocumentDialog(GladeInterface):
    """
    Dialog for creating the body of a new LaTeX document
    """

    _log = logging.getLogger("NewDocumentWizard")

    _PAPER_SIZES = (
        ("a4paper", "A4"),
        ("a5paper", "A5"),
        ("b5paper", "B5"),
        ("executivepaper", "US-Executive"),
        ("legalbl_paper", "US-Legal"),
        ("letterpaper", "US-Letter") )

    _DEFAULT_FONT_FAMILIES =  (
        ("\\rmdefault", "<span font_family=\"serif\">Roman</span>"),
        ("\\sfdefault", "<span font_family=\"sans\">Sans Serif</span>"),
        ("\\ttdefault", "<span font_family=\"monospace\">Typerwriter</span>") )

    _LOCALE_MAPPINGS = {
        "af"    : "afrikaans",
        "af_ZA" : "afrikaans",
        "sq"    : "albanian",
        "sq_AL" : "albanian",
        "eu"    : "basque",
        "eu_ES" : "basque",
        "id"    : "bahasai",
        "id_ID" : "bahasai",
        "ms"    : "bahasam",
        "ms_MY" : "bahasam",
        "br"    : "breton",
        "bg"    : "bulgarian",
        "bg_BG" : "bulgarian",
        "ca"    : "catalan",
        "ca_ES" : "catalan",
        "hr"    : "croatian",
        "hr_HR" : "croatian",
        "cz"    : "czech",
        "da"    : "danish",
        "da_DK" : "danish",
        "nl"    : "dutch",
        "nl_BE" : "dutch",
        "nl_NL" : "dutch",
        "eo"    : "esperanto",
        "et"    : "estonian",
        "et_EE" : "estonian",
        "en"    : "USenglish",
        "en_AU" : "australian",
        "en_CA" : "canadian",
        "en_GB" : "UKenglish",
        "en_US" : "USenglish",
        "en_ZA" : "UKenglish",
        "fi"    : "finnish",
        "fi_FI"    : "finnish",
        "fr"    : "frenchb",
        "fr_FR" : "frenchb",
        "fr_CA" : "canadien",
        "gl"    : "galician",
        "gl_ES" : "galician",
        "el"    : "greek",
        "el_GR" : "greek",
        "he"    : "hebrew",
        "he_IL" : "hebrew",
        "hu"    : "magyar",
        "hu_HU" : "magyar",
        "is"    : "icelandic",
        "is_IS" : "icelandic",
        "it"    : "italian",
        "it_CH" : "italian",
        "it_IT" : "italian",
        "ga"    : "irish",
        "la"    : "latin",
        "dsb"    : "lsorbian",
        "de_DE" : "ngermanb",
        "de_AT" : "naustrian",
        "de_CH" : "ngermanb",
        "nb"    : "norsk",
        "no"    : "norsk",
        "no_NO" : "norsk",
        "no_NY" : "norsk",
        "nn"    : "nynorsk",
        "nn_NO" : "nynorsk",
        "pl"    : "polish",
        "pl_PL" : "polish",
        "pt"    : "portuguese",
        "pt_BR" : "brazilian",
        "pt_PT" : "portuguese",
        "ro"    : "romanian",
        "ro_RO" : "romanian",
        "ru"    : "russianb",
        "ru_RU" : "russianb",
        "gd"    : "scottish",
        "se"    : "samin",
        "se_NO" : "samin",
        "sr"    : "serbian",
        "sr_YU" : "serbian",
        "sl"    : "slovene",
        "sl_SL" : "slovene",
        "sl_SI"    : "slovene",
        "sk"    : "slovak",
        "sk_SK" : "slovak",
        "es"    : "spanish",
        "es_AR" : "spanish",
        "es_CL" : "spanish",
        "es_CO" : "spanish",
        "es_DO" : "spanish",
        "es_EC" : "spanish",
        "es_ES" : "spanish",
        "es_GT" : "spanish",
        "es_HN" : "spanish",
        "es_LA" : "spanish",
        "es_MX" : "spanish",
        "es_NI" : "spanish",
        "es_PA" : "spanish",
        "es_PE" : "spanish",
        "es_PR" : "spanish",
        "es_SV" : "spanish",
        "es_UY" : "spanish",
        "es_VE" : "spanish",
        "es_UY" : "spanish",
        "sv"    : "swedish",
        "sv_SE" : "swedish",
        "sv_SV" : "swedish",
        "tr"    : "turkish",
        "tr_TR"    : "turkish",
        "uk"    : "ukraineb",
        "uk_UA" : "ukraineb",
        "hsb"    : "usorbian",
        "cy"    : "welsh",
        "cy_GB" : "welsh"
    }

    dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("new_document_template_dialog.ui")

    def get_dialog(self):
        """
        Build and return the dialog
        """
        if self.dialog == None:
            preferences = Preferences()
            environment = Environment()

            self.dialog = self.find_widget("dialogNewDocument")

            #
            # file
            #
            self._entry_name = self.find_widget("entryName")
            self._button_dir = self.find_widget("buttonDirectory")
            self._button_dir.set_action(Gtk.FileChooserAction.SELECT_FOLDER)

            #
            # templates
            #
            self._proxy_template = ComboBoxProxy(self.find_widget("comboTemplate"), "RecentTemplate")

            folder = Folder(preferences.TEMPLATE_DIR)

            templates = folder.files
            default_template_path = Resources().get_data_file("templates")
            folder = Folder(default_template_path)
            templates.extend(folder.files)
            templates.sort()
            for template in templates:
                self._proxy_template.add_option(template.path, template.shortbasename, show_value=False)
            self._proxy_template.restore(os.path.join(default_template_path,"Default.template"))

            #
            # metadata
            #
            self._entry_title = self.find_widget("entryTitle")
            self._entry_author = self.find_widget("entryAuthor")
            self._entry_author.set_text(environment.username)
            self._radio_date_custom = self.find_widget("radioCustom")
            self._entry_date = self.find_widget("entryDate")

            #
            # document classes
            #
            self._proxy_document_class = ComboBoxProxy(self.find_widget("comboClass"), "RecentDocumentClass")
            document_classes = environment.document_classes
            document_classes.sort(key=lambda x: x.name.lower())
            for c in document_classes:
                self._proxy_document_class.add_option(c.name, _(c.label))
            self._proxy_document_class.restore("article")

            #
            # paper
            #
            self._proxy_paper_size = ComboBoxProxy(self.find_widget("comboPaperSize"), "RecentPaperSize")
            self._proxy_paper_size.add_option("", _("Default"))
            for size, label in self._PAPER_SIZES:
                self._proxy_paper_size.add_option(size, label)
            self._proxy_paper_size.restore("")


            self._check_landscape = self.find_widget("checkLandscape")
            self._check_landscape.set_active(False)

            #
            # font size
            #
            self._radio_font_user = self.find_widget("radioFontUser")
            self._spin_font_size = self.find_widget("spinFontSize")
            self._labelFontSize = self.find_widget("labelFontSize")

            #
            # font family
            #
            self._proxy_font_family = ComboBoxProxy(self.find_widget("comboFontFamily"), "RecentDefaultFontFamily")
            for command, label in self._DEFAULT_FONT_FAMILIES:
                self._proxy_font_family.add_option(command, _(label), False)
            self._proxy_font_family.restore("\\rmdefault")


            #
            # input encodings
            #
            self._proxy_encoding = ComboBoxProxy(self.find_widget("comboEncoding"), "RecentInputEncoding")
            input_encodings = environment.input_encodings
            input_encodings.sort(key=lambda x: x.name.lower())
            for e in input_encodings:
                self._proxy_encoding.add_option(e.name, e.label)
            self._proxy_encoding.restore("utf8")

            #
            # babel packages
            #
            self._proxy_babel = ComboBoxProxy(self.find_widget("comboBabel"), "RecentBabelPackage")
            language_definitions = environment.language_definitions
            language_definitions.sort(key=lambda x: x.name.lower())
            for l in language_definitions:
                self._proxy_babel.add_option(l.name, _(l.label))

            try:
                self._proxy_babel.restore(self._LOCALE_MAPPINGS[environment.language_code])
            except Exception as e:
                self._log.error("Failed to guess babel package: %s" % e)
                self._proxy_babel.restore("english")

            #
            # connect signals
            #
            self.connect_signals({ "on_radioCustom_toggled" : self._on_custom_date_toggled,
                                   "on_radioFontUser_toggled" : self._on_user_font_toggled })

        return self.dialog

    def _on_custom_date_toggled(self, toggle_button):
        self._entry_date.set_sensitive(toggle_button.get_active())

    def _on_user_font_toggled(self, toggle_button):
        self._spin_font_size.set_sensitive(toggle_button.get_active())
        self._labelFontSize.set_sensitive(toggle_button.get_active())

    @property
    def source(self):
        """
        Compose and return the source resulting from the dialog
        """
        # document class options
        documentOptions = []

        if self._radio_font_user.get_active():
            documentOptions.append("%spt" % self._spin_font_size.get_value_as_int())

#        paperSize = self._store_paper_size[self._combo_paper_size.get_active()][0]
#        if len(paperSize) > 0:
#            documentOptions.append(paperSize)
        paperSize = self._proxy_paper_size.value
        if paperSize != "":
            documentOptions.append(paperSize)

        if self._check_landscape.get_active():
            documentOptions.append("landscape")

        if len(documentOptions) > 0:
            documentOptions = "[" + ",".join(documentOptions) + "]"
        else:
            documentOptions = ""


#        documentClass = self._store_class[self._combo_class.get_active()][0]
        documentClass = self._proxy_document_class.value

        title = self._entry_title.get_text()
        author = self._entry_author.get_text()
#        babelPackage = self._store_babel[self._combo_babel.get_active()][0]
#        inputEncoding = self._store_encoding[self._combo_encoding.get_active()][0]
        babelPackage = self._proxy_babel.value
        inputEncoding = self._proxy_encoding.value

        if self._radio_date_custom.get_active():
            date = self._entry_date.get_text()
        else:
            date = "\\today"

        if self.find_widget("checkPDFMeta").get_active():
            ifpdf = "\n\\usepackage{ifpdf}\n\\usepackage{hyperref}"

            # pdfinfo is discouraged because it
            #  - doesn't support special characters like umlauts
            #  - is not supported by XeTeX
            # see http://sourceforge.net/tracker/index.php?func=detail&aid=2809478&group_id=204144&atid=988431

#            pdfinfo = """
#\\ifpdf
#    \\pdfinfo {
#        /Author (%s)
#        /Title (%s)
#        /Subject (SUBJECT)
#        /Keywords (KEYWORDS)
#        /CreationDate (D:%s)
#    }
#\\fi""" % (author, title, time.strftime('%Y%m%d%H%M%S'))

            pdfinfo = """
\\ifpdf
\\hypersetup{
    pdfauthor={%s},
    pdftitle={%s},
}
\\fi""" % (author, title)
        else:
            ifpdf = ""
            pdfinfo = ""

        if self._proxy_font_family.value == "\\rmdefault":
            default_font_family = ""    # \rmdefault is the default value of \familydefault
        else:
            default_font_family = "\n\\renewcommand{\\familydefault}{%s}" % self._proxy_font_family.value

        template_string = open(self._proxy_template.value).read()
        template = string.Template(template_string)
        s = template.safe_substitute({
                    "DocumentOptions" : documentOptions,
                    "DocumentClass" : documentClass,
                    "InputEncoding" : inputEncoding,
                    "BabelPackage" : babelPackage,
                    "AdditionalPackages" : default_font_family + ifpdf,
                    "Title" : title,
                    "Author" : author,
                    "Date" : date,
                    "AdditionalPreamble" : pdfinfo})

#        s = """\\documentclass%s{%s}
#\\usepackage[%s]{inputenc}
#\\usepackage[%s]{babel}%s%s
#\\title{%s}
#\\author{%s}
#\\date{%s}%s
#\\begin{document}
#
#\\end{document}""" % (documentOptions, documentClass, inputEncoding, babelPackage, default_font_family, ifpdf, title, author, date, pdfinfo)

        return s

    @property
    def file(self):
        """
        Return the File object
        """
        return File("%s/%s.tex" % (self._button_dir.get_filename(), self._entry_name.get_text()))

    def run(self):
        """
        Runs the dialog
        """
        dialog = self.get_dialog()
        r = dialog.run()
        dialog.hide()
        return r


class UseBibliographyDialog(GladeInterface, PreviewRenderer):
    """
    Dialog for inserting a reference to a bibliography
    """

    _log = logging.getLogger("UseBibliographyWizard")


    # sample bibtex content used for rendering the preview
    _BIBTEX = """@book{ dijkstra76,
    title={{A Discipline of Programming}},
    author={Edsger W. Dijkstra},
    year=1976 }
@article{ dijkstra68,
    title={{Go to statement considered harmful}},
    author={Edsger W. Dijkstra},
    year=1968 }"""

    dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("use_bibliography_dialog.ui")

    def run_dialog(self, edited_file):
        """
        Run the dialog

        @param edited_file: the File edited the active Editor
        @return: the source resulting from the dialog
        """
        source = None
        dialog = self._get_dialog()

        self._file_chooser_button.set_current_folder(edited_file.dirname)

        if dialog.run() == 1:        # TODO: use gtk constant
            base_dir = edited_file.dirname

            file = File(self._file_chooser_button.get_filename())
            source = "\\bibliography{%s}\n\\bibliographystyle{%s}" % (file.relativize_shortname(base_dir),
                                                                    self._storeStyle[self._comboStyle.get_active()][0])

        dialog.hide()

        return source

    def _get_dialog(self):
        if not self.dialog:

            self.dialog = self.find_widget("dialogUseBibliography")

            # bib file

            self._file_chooser_button = self.find_widget("filechooserbutton")

            # styles

            self._storeStyle = Gtk.ListStore(str)

            styles = Environment().bibtex_styles
            for style in styles:
                self._storeStyle.append([style.name])

            self._comboStyle = self.find_widget("comboboxStyle")
            self._comboStyle.set_model(self._storeStyle)

            try:
                recent = styles.index(Preferences().get("recent-bibtex-style"))
            except ValueError:
                recent = 0
            self._comboStyle.set_active(recent)

            self._imagePreview = self.find_widget("previewimage")
            self._imagePreview.show()

            self.connect_signals({ "on_buttonRefresh_clicked" : self._on_refresh_clicked })

        return self.dialog

    def _on_refresh_clicked(self, widget):
        """
        The button for refreshing the preview has been clicked
        """
        index = self._comboStyle.get_active()
        if index < 0:
            self._log.error("No style selected")
            return

        style = self._storeStyle[index][0]

        self._imagePreview.set_from_stock(Gtk.STOCK_EXECUTE, Gtk.IconSize.BUTTON)

        # create temporary bibtex file
        self._tempFile = tempfile.NamedTemporaryFile(mode="w", suffix=".bib")
        self._tempFile.write(self._BIBTEX)
        self._tempFile.flush()

        filename = self._tempFile.name
        self._filenameBase = os.path.splitext(os.path.basename(filename))[0]

        # build preview image
        self.render("Book \\cite{dijkstra76} Article \\cite{dijkstra68} \\bibliography{%s}\\bibliographystyle{%s}" % (self._filenameBase,
                                                                                                                    style))
    def _on_render_succeeded(self, pixbuf):
        # PreviewRenderer._on_render_succeeded
        self._imagePreview.set_from_pixbuf(pixbuf)
        # remove the temp bib file
        self._tempFile.close()

    def _on_render_failed(self):
        # PreviewRenderer._on_render_failed

        # set a default icon as preview
        self._imagePreview.set_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON)
        # remove the temp bib file
        self._tempFile.close()


class InsertGraphicsDialog(GladeInterface):

    _PREVIEW_WIDTH, _PREVIEW_HEIGHT = 128, 128
    _dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("insert_graphics_dialog.ui")

    def run(self, edited_file):
        """
        @param edited_file: the File currently edited
        """
        dialog = self.__get_dialog()

        source = None

        if dialog.run() == 1:
            #filename = self._fileChooser.get_filename()

            file = File(self._fileChooser.get_filename())
            relative_filename = file.relativize(edited_file.dirname)

            # for eps and pdf the extension should be omitted
            # (see http://www.tex.ac.uk/cgi-bin/texfaq2html?label=graph-pspdf)
            ext = os.path.splitext(relative_filename)[1]
            if ext == ".pdf" or ext == ".eps":
                relative_filename = os.path.splitext(relative_filename)[0]

            width = "%.2f" % round(self.find_widget("spinbuttonWidth").get_value() / 100.0, 2)
            caption = self.find_widget("entryCaption").get_text()
            label = self.find_widget("entryLabel").get_text()
            floating = self.find_widget("checkbuttonFloat").get_active()
            spread = self.find_widget("checkbuttonSpread").get_active()
            relativeTo = self._comboRelative.get_active()
            rotate = self.find_widget("spinRotate").get_value()
            flip = self.find_widget("checkFlip").get_active()

            source = ""
            packages = ["graphicx"]

            if relativeTo == 0:        # relative to image size
                options = "scale=%s" % width
            else:        # relative to text width
                options = "width=%s\\textwidth" % width

            if rotate != 0:
                options += ", angle=%s" % rotate

            includegraphics = "\\includegraphics[%s]{%s}" % (options, relative_filename)

            if flip:
                includegraphics = "\\reflectbox{%s}" % includegraphics

            if floating:
                if spread:
                    ast = "*"
                else:
                    ast = ""
                source += "\\begin{figure%s}[ht]\n\t\\centering\n\t%s" % (ast, includegraphics)
                if len(caption):
                    source += "\n\t\\caption{%s}" % caption
                if len(label) and label != "fig:":
                    source += "\n\t\\label{%s}" % label
                source += "\n\\end{figure%s}" % ast
            else:
                source += "\\begin{center}\n\t%s" % includegraphics
                if len(caption):
                    source += "\n\t\\captionof{figure}{%s}" % caption
                    packages.append("caption")
                if len(label) and label != "fig:":
                    source += "\n\t\\label{%s}" % label
                source += "\n\\end{center}"

#            viewAdapter.insertText(source)
#            viewAdapter.ensurePackages(packages)

            source = LaTeXSource(source, packages)

        dialog.hide()

        return source

    def __get_dialog(self):
        if not self._dialog:

            # setup the dialog

            self._dialog = self.find_widget("dialogInsertGraphics")

            previewImage = Gtk.Image()
            self._fileChooser = self.find_widget("FileChooser")
            self._fileChooser.set_preview_widget(previewImage)
            self._fileChooser.connect("update-preview", self.__update_preview, previewImage)

            #self._fileChooser.get_property("dialog").connect("response", self._fileChooserResponse)    # FIXME: not readable
            #self._fileChooser.connect("file-activated", self._fileActivated)                            # FIXME: doesn't work

            self._okayButton = self.find_widget("buttonOkay")

            self._comboRelative = self.find_widget("comboRelative")
            self._comboRelative.set_active(0)

        return self._dialog

    def __update_preview(self, fileChooser, previewImage):
        """
        Update the FileChooser's preview image
        """
        filename = fileChooser.get_preview_filename()

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, self._PREVIEW_WIDTH, self._PREVIEW_HEIGHT)
            previewImage.set_from_pixbuf(pixbuf)
            fileChooser.set_preview_widget_active(True)
        except:
            fileChooser.set_preview_widget_active(False)


class InsertTableDialog(GladeInterface):
    """
    This is used to include tables and matrices
    """

    _dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("insert_table_dialog.ui")

    def run(self):
        dialog = self.__get_dialog()

        source = None

        if dialog.run() == 1:
            floating = self.find_widget("checkbuttonFloat").get_active()
            rows = int(self.find_widget("spinbuttonRows").get_value())
            cols = int(self.find_widget("spinbuttonColumns").get_value())
            caption = self.find_widget("entryCaption").get_text()
            label = self.find_widget("entryLabel").get_text()

            s = ""

            if self.find_widget("radiobuttonTable").get_active():
                # table

                layout = "l" * cols

                if floating:
                    s += "\\begin{table}[ht]\n\t\\centering\n\t\\begin{tabular}{%s}%s\n\t\\end{tabular}" % (layout,
                                                                                        self.__build_table_body(rows, cols, "\t\t"))

                    if len(caption):
                        s += "\n\t\\caption{%s}" % caption

                    if len(label) and label != "tab:":
                        s += "\n\t\\label{%s}" % label

                    s += "\n\\end{table}"

                else:
                    s += "\\begin{center}\n\t\\begin{tabular}{%s}%s\n\t\\end{tabular}" % (layout,
                                                                                        self.__build_table_body(rows, cols, "\t\t"))

                    if len(caption):
                        s += "\n\t\\captionof{table}{%s}" % caption

                    if len(label):
                        s += "\n\t\\label{%s}" % label

                    s += "\n\\end{center}"
                packages = []
            else:
                environ = self._storeDelims[self._comboDelims.get_active()][2]
                s = "\\begin{%s}%s\n\\end{%s}" % (environ, self.__build_table_body(rows, cols, "\t\t"), environ)
                packages = ["amsmath"]

            source = LaTeXSource(s, packages)

        dialog.hide()

        return source

    def __get_dialog(self):
        if not self._dialog:
            self._dialog = self.find_widget("dialogInsertTable")

            # delimiters
            self._storeDelims = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)      # icon, label, environment

            self._storeDelims.append([None, "None", "matrix"])

            delimiters = [("parantheses", "Parantheses", "pmatrix"),
                        ("brackets", "Brackets", "bmatrix"),
                        ("braces", "Braces", "Bmatrix"),
                        ("vbars", "Vertical Bars", "vmatrix"),
                        ("dvbars", "Double Vertical Bars", "Vmatrix")]

            for d in delimiters:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(Resources().get_icon("%s.png" % d[0]))
                self._storeDelims.append([pixbuf, d[1], d[2]])

            self._comboDelims = self.find_widget("comboDelims")
            self._comboDelims.set_model(self._storeDelims)

            cellPixbuf = Gtk.CellRendererPixbuf()
            self._comboDelims.pack_start(cellPixbuf, False)
            self._comboDelims.add_attribute(cellPixbuf, 'pixbuf', 0)

            cellText = Gtk.CellRendererText()
            self._comboDelims.pack_start(cellText, False)
            self._comboDelims.add_attribute(cellText, 'text', 1)

            self._comboDelims.set_active(0)

            self.connect_signals({ "on_radioMatrix_toggled" : self.__matrix_toggled })

        return self._dialog

    def __matrix_toggled(self, toggleButton):
        self._comboDelims.set_sensitive(toggleButton.get_active())

    def __build_table_body(self, rows, cols, indent):
        """
        This builds the body of a table template according to the number of rows and
        columns.
        """

        # FIXME: create unique placeholders for each cell for multi-placeholder feature

        s = ""
        for i in range(rows):
            colList = []
            for j in range(cols):
                colList.append("${%s%s}" % (i + 1, j + 1))
            s += "\n" + indent + " & ".join(colList) + " \\\\\\\\"
        return s


class InsertListingDialog(GladeInterface):
    """
    """

    _dialog = None

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("insert_listing_dialog.ui")

    def run(self, edited_file):
        """
        @param edited_file: the File currently edited
        """
        dialog = self.__get_dialog()

        source = None

        if dialog.run() == 1:

            lstset = ""
            options = ""
            extra = r',basicstyle=\small\ttfamily,breaklines=true,showtabs=false,showspaces=false,breakatwhitespace=true'

            language = self._storeLanguages[self._comboLanguage.get_active()][0]
            try:
                dialect = self._storeDialects[self._comboDialect.get_active()][0]
            except IndexError:
                dialect = ""

            if self._dialectsEnabled and len(dialect):
                # we need the lstset command
                lstset = "\\lstset{language=[%s]%s%s}\n" % (dialect, language, extra)
            else:
                options = "[language=%s%s]" % (language, extra)


            if self._checkFile.get_active():
                file = File(self._fileChooserButton.get_filename())
                relative_filename = file.relativize(edited_file.dirname)

                source = "%s\\lstinputlisting%s{%s}" % (lstset, options, relative_filename)

            else:
                source = "%s\\begin{lstlisting}%s\n\t$0\n\\end{lstlisting}" % (lstset, options)

            source = LaTeXSource(source, ["listings"])

        dialog.hide()

        return source

    def __get_dialog(self):
        if not self._dialog:
            self._dialog = self.find_widget("dialogListing")

            self._fileChooserButton = self.find_widget("fileChooserButton")

            #
            # languages
            #
            self._languages = []
            parser = LanguagesParser()
            parser.parse(self._languages, Resources().get_data_file("listings.xml"))

            recentLanguage = Preferences().get("recent-listing-language")

            self._storeLanguages = Gtk.ListStore(str)
            recentLanguageIndex = 0
            i = 0
            for l in self._languages:
                self._storeLanguages.append([l.name])
                if l.name == recentLanguage:
                    recentLanguageIndex = i
                i += 1

            self._comboLanguage = self.find_widget("comboLanguage")
            self._comboLanguage.set_model(self._storeLanguages)
            cell = Gtk.CellRendererText()
            self._comboLanguage.pack_start(cell, True)
            self._comboLanguage.add_attribute(cell, "text", 0)

            #
            # dialects
            #
            self._labelDialect = self.find_widget("labelDialect")

            self._storeDialects = Gtk.ListStore(str)

            self._comboDialect = self.find_widget("comboDialect")
            self._comboDialect.set_model(self._storeDialects)
            cell = Gtk.CellRendererText()
            self._comboDialect.pack_start(cell, True)
            self._comboDialect.add_attribute(cell, "text", 0)

            self._checkFile = self.find_widget("checkFile")

            self.connect_signals({ "on_checkFile_toggled" : self._fileToggled,
                                  "on_comboLanguage_changed" : self._languagesChanged })


            self._comboLanguage.set_active(recentLanguageIndex)

            self._dialectsEnabled = False

        return self._dialog

    def _languagesChanged(self, comboBox):
        language = self._languages[comboBox.get_active()]

        self._storeDialects.clear()

        if len(language.dialects):
            i = 0
            for dialect in language.dialects:
                self._storeDialects.append([dialect.name])
                if dialect.default:
                    self._comboDialect.set_active(i)
                i += 1

            self._labelDialect.set_sensitive(True)
            self._comboDialect.set_sensitive(True)

            self._dialectsEnabled = True
        else:
            self._labelDialect.set_sensitive(False)
            self._comboDialect.set_sensitive(False)

            self._dialectsEnabled = False

    def _fileToggled(self, toggleButton):
        self._fileChooserButton.set_sensitive(toggleButton.get_active())

    def _specificToggled(self, toggleButton):
        self._comboLanguage.set_sensitive(toggleButton.get_active())
        self._labelDialect.set_sensitive(toggleButton.get_active() and self._dialectsEnabled)
        self._comboDialect.set_sensitive(toggleButton.get_active() and self._dialectsEnabled)


class BuildImageDialog(GladeInterface):
    """
    Render the document to an image
    """

    _dialog = None
    _generator = ImageToolGenerator()

    def __init__(self):
        GladeInterface.__init__(self)
        self.filename = Resources().get_ui_file("build_image_dialog.ui")

    def run(self):
        dialog = self._getDialog()

        if dialog.run() == 1:

            if self.find_widget("radioPNG").get_active():
                self._generator.format = ImageToolGenerator.FORMAT_PNG
                self._generator.pngMode = self._storeMode[self._comboMode.get_active()][1]
            elif self.find_widget("radioJPEG").get_active():
                self._generator.format = ImageToolGenerator.FORMAT_JPEG
            elif self.find_widget("radioGIF").get_active():
                self._generator.format = ImageToolGenerator.FORMAT_GIF

            self._generator.open = True
            self._generator.resolution = self._spinResolution.get_value_as_int()
            self._generator.antialiasFactor = self._storeAntialias[self._comboAntialias.get_active()][1]
            self._generator.render_box = self.find_widget("radioBox").get_active()

            generate = True
        else:
            generate = False

        dialog.hide()

        if generate:
            return self._generator.generate()
        else:
            return None

    def _getDialog(self):
        if not self._dialog:
            self._dialog = self.find_widget("dialogRenderImage")
            self.find_widget("grid1").set_column_spacing(20)

            # PNG mode

            self._storeMode = Gtk.ListStore(str, int)    # label, mode constant
            self._storeMode.append([_("Monochrome"), ImageToolGenerator.PNG_MODE_MONOCHROME])
            self._storeMode.append([_("Grayscale"), ImageToolGenerator.PNG_MODE_GRAYSCALE])
            self._storeMode.append([_("RGB"), ImageToolGenerator.PNG_MODE_RGB])
            self._storeMode.append([_("RGBA"), ImageToolGenerator.PNG_MODE_RGBA])

            self._comboMode = self.find_widget("comboMode")
            self._comboMode.set_model(self._storeMode)
            cell = Gtk.CellRendererText()
            self._comboMode.pack_start(cell, True)
            self._comboMode.add_attribute(cell, "text", 0)
            self._comboMode.set_active(3)

            # anti-alias

            self._storeAntialias = Gtk.ListStore(str, int)    # label, factor
            self._storeAntialias.append([_("Off"), 0])
            self._storeAntialias.append([_("1×"), 1])
            self._storeAntialias.append([_("2×"), 2])
            self._storeAntialias.append([_("4×"), 4])
            self._storeAntialias.append([_("8×"), 8])

            self._comboAntialias = self.find_widget("comboAntialias")
            self._comboAntialias.set_model(self._storeAntialias)
            cell = Gtk.CellRendererText()
            self._comboAntialias.pack_start(cell, True)
            self._comboAntialias.add_attribute(cell, "text", 0)
            self._comboAntialias.set_active(3)

            # resolution

            self._spinResolution = self.find_widget("spinResolution")
            self._spinResolution.set_value(Environment().screen_dpi)

        return self._dialog


# ex:ts=4:et:
