SUBDIRS = base bibtex icons latex preferences templates tools ui util

plugindir = $(libdir)/gedit/plugins

plugin_in_files = latex.plugin.desktop.in

%.plugin: %.plugin.desktop.in $(INTLTOOL_MERGE) $(wildcard $(top_srcdir)/po/*po)
	$(INTLTOOL_MERGE) $(top_srcdir)/po $< $@ -d -u -c $(top_builddir)/po/.intltool-merge-cache

plugin_DATA = $(plugin_in_files:.plugin.desktop.in=.plugin)

gsettings_SCHEMAS = org.gnome.gedit.plugins.latex.gschema.xml

@INTLTOOL_XML_NOMERGE_RULE@
@GSETTINGS_RULES@

pluginlatexdir = $(plugindir)/latex

pluginlatex_PYTHON = \
	gldefs.py \
	__init__.py \
	issues.py \
	outline.py \
	relpath.py \
	util.py \
	views.py

pluginlatex_DATA = \
	bibtex.xml \
	latex.xml \
	listings.xml \
	symbols.xml \
	tools.xml

EXTRA_DIST = $(plugin_in_files)  org.gnome.gedit.plugins.latex.gschema.xml.in.in

CLEANFILES = $(plugin_DATA) $(gsettings_SCHEMAS)

DISTCLEANFILES = $(plugin_DATA) $(gsettings_SCHEMAS)

-include $(top_srcdir)/git.mk
