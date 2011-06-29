SUBDIRS = base bibtex icons latex preferences templates tools ui util

plugindir = $(libdir)/gedit/plugins



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
	preferences.xml.sample \
	symbols.xml \
	tools.xml


-include $(top_srcdir)/git.mk
