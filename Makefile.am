SUBDIRS = data latex po

ACLOCAL_AMFLAGS = -I m4 ${ACLOCAL_FLAGS}

plugindir = $(libdir)/gedit/plugins

plugin_in_files = latex.plugin.desktop.in

%.plugin: %.plugin.desktop.in $(INTLTOOL_MERGE) $(wildcard $(top_srcdir)/po/*po)
	$(INTLTOOL_MERGE) $(top_srcdir)/po $< $@ -d -u -c $(top_builddir)/po/.intltool-merge-cache

plugin_DATA = $(plugin_in_files:.plugin.desktop.in=.plugin)

EXTRA_DIST =			\
	autogen.sh		\
	gedit-latex.doap	\
	intltool-extract.in 	\
	intltool-merge.in 	\
	intltool-update.in	\
	$(plugin_in_files)

CLEANFILES =			\
	$(plugin_DATA)

DISTCLEANFILES = 		\
	intltool-extract 	\
	intltool-merge 		\
	intltool-update		\
	$(plugin_DATA)

MAINTAINERCLEANFILES = 		\
	aclocal.m4		\
	config.guess		\
	config.h.in		\
	config.sub		\
	depcomp			\
	install-sh		\
	ltmain.sh		\
	missing			\
	mkinstalldirs		\
	py-compile		\
	`find "$(srcdir)" -type f -name Makefile.in -print`

dist-hook:
	@if test -d "$(srcdir)/.git"; \
	then \
		echo Creating ChangeLog && \
		(GIT_DIR=$(top_srcdir)/.git \
		  ./missing --run git log --stat -M -C --name-status  --date=short --no-color) | \
		  fmt --split-only > ChangeLog.tmp \
		&& mv -f ChangeLog.tmp $(top_distdir)/ChangeLog \
		|| ( rm -f ChangeLog.tmp ; \
		  echo Failed to generate ChangeLog >&2 ); \
	else \
		echo A git clone is required to generate a ChangeLog >&2; \
	fi

-include $(top_srcdir)/git.mk
