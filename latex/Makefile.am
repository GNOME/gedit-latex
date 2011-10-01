SUBDIRS = base bibtex latex preferences tools util

plugindir = $(libdir)/gedit/plugins/latex

plugin_PYTHON = \
	appactivatable.py \
	file.py \
	gldefs.py \
	__init__.py \
	issues.py \
	outline.py \
	resources.py \
	singleton.py \
	snippetmanager.py \
	util.py \
	views.py \
	windowactivatable.py

DISTCLEANFILES = \
	gldefs.py

EXTRA_DIST = \
	gldefs.py.in

-include $(top_srcdir)/git.mk
