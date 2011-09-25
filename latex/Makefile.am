SUBDIRS = base bibtex latex preferences tools util

plugindir = $(libdir)/gedit/plugins/latex

plugin_PYTHON = \
	appactivatable.py \
	gldefs.py \
	__init__.py \
	issues.py \
	outline.py \
	resources.py \
	util.py \
	views.py

DISTCLEANFILES = \
	gldefs.py

EXTRA_DIST = \
	gldefs.py.in

-include $(top_srcdir)/git.mk
