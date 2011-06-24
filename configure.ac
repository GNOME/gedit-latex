dnl Process this file with autoconf to produce a configure script.

AC_PREREQ([2.63])

m4_define(gedit_latex_major_version,  2)
m4_define(gedit_latex_minor_version,  90)
m4_define(gedit_latex_micro_version,  0)
m4_define(gedit_latex_version, gedit_latex_major_version.gedit_latex_minor_version.gedit_latex_micro_version)

AC_INIT([gedit-latex],
        [gedit_latex_version],
        [http://bugzilla.gnome.org/enter_bug.cgi?product=gedit],
        [gedit-latex])

AC_CONFIG_HEADERS([config.h])
AC_CONFIG_SRCDIR([latex])
AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_AUX_DIR([build-aux])
AC_PREFIX_PROGRAM([gedit])

AM_INIT_AUTOMAKE([1.11 tar-ustar dist-xz no-dist-gzip])
AM_MAINTAINER_MODE([enable])

AM_SILENT_RULES([yes])

# Check for programs
AC_PROG_CC
AC_PROG_INSTALL
AC_PROG_MAKE_SET

AM_PATH_PYTHON

# Initialize libtool
LT_PREREQ([2.2])
LT_INIT([disable-static])

# ================================================================
# Gettext stuff.
# ================================================================
IT_PROG_INTLTOOL([0.40.0])

AM_GNU_GETTEXT_VERSION([0.17])
AM_GNU_GETTEXT([external])

GETTEXT_PACKAGE=gedit-latex
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE,"$GETTEXT_PACKAGE", [Gettext package])

# ================================================================
# Start of pkg-config checks
# ================================================================

PKG_CHECK_MODULES(GEDIT, [
	glib-2.0 >= 2.26.0
	gio-2.0 >= 2.26.0
	gtk+-3.0 >= 3.0.0
	gtksourceview-3.0 >= 3.0.0
	libpeas-1.0 >= 0.7.3
	libpeas-gtk-1.0 >= 0.7.3
	gedit >= 3.0.0
])

dnl ================================================================
dnl GSettings stuff
dnl ================================================================

GLIB_GSETTINGS

# ================================================================
# Misc
# ================================================================
AC_PATH_PROG(GLIB_GENMARSHAL, glib-genmarshal)

AC_CONFIG_FILES([
Makefile
latex/gldefs.py
latex/latex.plugin.desktop.in
latex/Makefile
latex/base/Makefile
latex/bibtex/Makefile
latex/icons/Makefile
latex/latex/Makefile
latex/preferences/Makefile
latex/templates/Makefile
latex/tools/Makefile
latex/ui/Makefile
latex/util/Makefile
po/Makefile.in])

AC_OUTPUT

echo "

Configuration:

	Source code location:   ${srcdir}
	Compiler:               ${CC}
	Prefix:			${prefix}

Note: you have to install this plugin into the same prefix as your gedit
installation (probably /usr if you're using your distro packages, /usr/local
if you have compiled it on your own).
"

