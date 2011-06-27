SUBDIRS = base bibtex icons latex preferences templates tools ui util

plugindir = $(libdir)/gedit/plugins/latex

gsettings_SCHEMAS = org.gnome.gedit.plugins.latex.gschema.xml

@INTLTOOL_XML_NOMERGE_RULE@
@GSETTINGS_RULES@

plugin_PYTHON = \
	gldefs.py \
	__init__.py \
	issues.py \
	outline.py \
	relpath.py \
	util.py \
	views.py

plugin_DATA = \
	bibtex.xml \
	latex.xml \
	listings.xml \
	symbols.xml \
	tools.xml

EXTRA_DIST = org.gnome.gedit.plugins.latex.gschema.xml.in.in

CLEANFILES = $(gsettings_SCHEMAS)

DISTCLEANFILES = $(gsettings_SCHEMAS)

-include $(top_srcdir)/git.mk
