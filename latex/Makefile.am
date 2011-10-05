SUBDIRS = bibtex latex preferences tools util

plugindir = $(libdir)/gedit/plugins/latex

plugin_PYTHON = \
	action.py \
	appactivatable.py \
	completion.py \
	config.py \
	editor.py \
	file.py \
	gldefs.py \
	__init__.py \
	issues.py \
	job.py \
	outline.py \
	panelview.py \
	resources.py \
	singleton.py \
	snippetmanager.py \
	tabdecorator.py \
	util.py \
	views.py \
	windowactivatable.py \
	windowcontext.py

DISTCLEANFILES = \
	gldefs.py

EXTRA_DIST = \
	gldefs.py.in

-include $(top_srcdir)/git.mk
