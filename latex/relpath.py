# -*- coding: utf-8 -*-

# http://www.koders.com/python/fid663562CE0A76349E3DA5EE4E0747B1B733A510AD.aspx

#----------------------------------------------------------------------
# Name:        relpath.py
# Purpose:
#
# Author:      Riaan Booysen
#
# Created:     1999
# RCS-ID:      $Id: relpath.py,v 1.9 2006/10/09 15:14:32 riaan Exp $
# Copyright:   (c) 1999 - 2003 Riaan Booysen
# Licence:     GPL
#----------------------------------------------------------------------

##b = 'c:\\a\\b\\f\\d'
##d = 'c:\\a\\b\\f\\h.txt'
##d = 'c:\\a\\b\\h\\i\\j.txt'
##e = 'd:\\z\\x\\y\\j\\k.txt'

import os

def splitpath(apath):
    """ Splits a path into a list of directory names """
    path_list = []
    drive, apath = os.path.splitdrive(apath)
    head, tail = os.path.split(apath)
    while 1:
        if tail:
            path_list.insert(0, tail)
        newhead, tail = os.path.split(head)
        if newhead == head:
            break
        else:
            head = newhead
    if drive:
        path_list.insert(0, drive)
    return path_list


def relpath(base, comp):
    """ Return a path to file comp relative to path base. """
    protsplitbase = base.split('://')
    if len(protsplitbase) == 1:
        baseprot, nbase = 'file', protsplitbase[0]
    elif len(protsplitbase) == 2:
        baseprot, nbase = protsplitbase
    elif len(protsplitbase) == 3:
        baseprot, nbase, zipentry = protsplitbase
    else:
        raise Exception, 'Unhandled path %s'%`protsplitbase`

    protsplitcomp = comp.split('://')
    if len(protsplitcomp) == 1:
        compprot, ncomp  = 'file', protsplitcomp[0]
    elif len(protsplitcomp) == 2:
        compprot, ncomp = protsplitcomp
    elif len(protsplitcomp) == 3:
        compprot, ncomp, zipentry = protsplitcomp
    else:
        raise Exception, 'Unhandled path %s'%`protsplitcomp`

    if baseprot != compprot:
        return comp

    base_drive, base_path = os.path.splitdrive(nbase)
    comp_drive, comp_path = os.path.splitdrive(ncomp)
    base_path_list = splitpath(base_path)
    comp_path_list = splitpath(comp_path)

    if base_drive != comp_drive:
        return comp

    # relative path defaults to the list of files with
    # a greater index then the entire base
    rel_path = comp_path_list[len(base_path_list):]
    # find the first directory for which the 2 paths differ
    found = -1
    idx = 0
    for idx in range(len(base_path_list)):
        if base_path_list[idx].lower() != comp_path_list[idx].lower():
            rel_path = comp_path_list[idx:]
            found = 0
            break
    for cnt in range(max(len(base_path_list) - idx + found, 0)):
        rel_path.insert(0, os.pardir)

    return os.path.join(*rel_path)

# ex:ts=8:et:
