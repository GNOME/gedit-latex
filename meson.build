project(
  'gedit-latex', 'c', # vala is added below if needed, with add_languages().
  version: '46.2.2',
  meson_version: '>= 0.50'
)

gnome = import('gnome')
i18n = import('i18n')
pkg = import('pkgconfig')
python = import('python')

# Paths
root_include_dir = include_directories('.')

srcdir = meson.current_source_dir()

libdir = join_paths(get_option('prefix'), get_option('libdir'))
datadir = join_paths(get_option('prefix'), get_option('datadir'))

pkglibdir = join_paths(libdir, 'gedit')
pkgdatadir = join_paths(datadir, 'gedit','plugins','latex')

appstreamdir = join_paths(datadir, 'metainfo')
glibdir = join_paths(datadir, 'glib-2.0')
localedir = join_paths(datadir, 'locale')

# Dependencies in common for all plugins
libpeas_dep = dependency('libpeas-1.0', version: '>= 1.14.1')
gedit_dep = dependency('gedit', version: '>= 3.30')

appstream_util = find_program('appstream-util', required: false)
python3 = python.find_installation('python3')

# config.h
config_h = configuration_data()
config_h.set_quoted('GETTEXT_PACKAGE', meson.project_name())

configure_file(
  output: 'config.h',
  configuration: config_h
)

# latex.plugin
plugin_in = configuration_data()
plugin_in.set('VERSION', meson.project_version())
latex_plugin_in = configure_file(
  input: 'latex.plugin.desktop.in.in',
  output: 'latex.plugin.desktop.in',
  configuration: plugin_in,
  install: false,
)

msgfmt_plugin_cmd = [
  find_program('msgfmt'),
  '--desktop',
  '--keyword=Name',
  '--keyword=Description',
  '--template=@INPUT@',
  '-d', join_paths(srcdir, 'po'),
  '--output=@OUTPUT@'
]


latex_plugin = custom_target(
  'latex.plugin',
  input: latex_plugin_in,
  output: 'latex.plugin',
  command: msgfmt_plugin_cmd,
  install: true,
  install_dir: join_paths(
    pkglibdir,
    'plugins',
  )
)

gpdefs_py = configuration_data()
gpdefs_py.set('GETTEXT_PACKAGE', meson.project_name())

configure_file(
  input: 'gldefs.py.in',
  output: 'gldefs.py',
  configuration: gpdefs_py,
  install: true,
  install_dir: join_paths(
    pkglibdir,
    'plugins',
    'latex',
  )
)

subdir('po')

install_subdir(
  'data',
  install_dir: pkgdatadir,
  strip_directory: true,
)

install_subdir(
  'latex',
  install_dir: join_paths(
    pkglibdir,
    'plugins',
  )
)

install_data(
  'org.gnome.gedit.plugins.latex.gschema.xml',
  install_dir: join_paths(
    glibdir,
    'schemas',
  )
)
meson.add_install_script(
  'build-aux/meson/post_install.py',
  libdir,
  datadir
)


# Summary message

summary = [
  'Configuration:',
  '',
  '        gedit-latex version @0@'.format(meson.project_version()),
  '',
  '        Prefix: @0@'.format(get_option('prefix')),
]

message('\n'.join(summary))
