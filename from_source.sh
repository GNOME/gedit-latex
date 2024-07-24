#! /bin/bash


if [ "$1" = "remove" ]; then
    echo "Remove links for local gedit-latex"
    unlink ~/.local/share/gedit/plugins/latex
    unlink ~/.local/share/gedit/plugins/latex.plugin
else
    echo "Install links for local gedit-latex"
    # Prepare compiled files:
    mkdir -p build
    meson setup build
    cd build
    ninja
    cd ..
    ln -sf `pwd`/build/gldefs.py `pwd`/latex/gldefs.py

    # Link them where appropriate
    ln -s `pwd`/latex ~/.local/share/gedit/plugins/latex
    ln -s `pwd`/build/latex.plugin ~/.local/share/gedit/plugins/latex.plugin
fi

echo "Done"
