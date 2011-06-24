SUBDIRS = latex po

ACLOCAL_AMFLAGS = -I m4 ${ACLOCAL_FLAGS}

EXTRA_DIST =			\
	autogen.sh		\
	gedit-latex.doap	\
	intltool-extract.in 	\
	intltool-merge.in 	\
	intltool-update.in

DISTCLEANFILES = 		\
	intltool-extract 	\
	intltool-merge 		\
	intltool-update

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

-include $(top_srcdir)/git.mk
