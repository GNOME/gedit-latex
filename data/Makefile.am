SUBDIRS= icons templates ui

plugindir = $(datadir)/gedit/plugins/latex

gsettings_SCHEMAS = org.gnome.gedit.plugins.latex.gschema.xml
@INTLTOOL_XML_NOMERGE_RULE@
@GSETTINGS_RULES@

plugin_DATA = \
	bibtex.xml \
	latex.xml \
	listings.xml \
	symbols.xml \
	tools.xml

EXTRA_DIST = \
	plugin_DATA \
	org.gnome.gedit.plugins.latex.gschema.xml.in.in

CLEANFILES = $(gsettings_SCHEMAS)

DISTCLEANFILES = $(gsettings_SCHEMAS)

include $(top_srcdir)/git.mk
