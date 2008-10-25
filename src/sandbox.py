#!/usr/bin/env python

import os, sys

#read_fd, write_fd = os.pipe()
#
#pid = os.fork()
#
#if pid:
#	#
#    # we are the parent
#    #
#    os.close(write_fd) # use os.close() to close a file descriptor
#    read_file = os.fdopen(read_fd) # turn r into a file object
#    
#    print "parent: reading"
#    
#    txt = read_file.read()
#    os.waitpid(pid, 0) # make sure the child process gets cleaned up
#    
#    print "parent: got it; text =", txt
#else:
#	#
#    # we are the child
#    #
#    os.close(read_fd)
#    write_file = os.fdopen(write_fd, 'w')
#    
#    print "child: writing"
#    
#    write_file.write("here's some text from the child")
#    write_file.close()
#    
#    print "child: closing"
#    
#    sys.exit(0)


#gtk.gdk.threads_init()

#import threading
#
#class ThreadedProcess(object):
#	def run(self, callable):
#		self.__callable = callable
#		t = threading.Thread(target=self.__run)
#		t.start()
# 	
# 	def __run(self):
# 		r = self.__callable.__call__()
# 		self._on_child_returned(r)
# 
#  	def _on_child_returned(self, r):
#  		pass


#
# This crashes gedit when _on_child_returned is called.
#

import gobject

class ForkedProcess(object):
	"""
	This runs a callable in a subprocess
	"""
	def run(self, callable):
		"""
		Run a callable in a child process
		"""
		pid = os.fork()
		if pid:
			#
			# parent code
			#
			gobject.child_watch_add(pid, self.__on_exit)
		else:
			#
			# child code, pid==None
			#
			r = callable.__call__()
			#self.__on_child_returned(r)
	
	def __on_exit(self, pid, condition):
		print "EXIT"
		self._on_child_returned(None)
	
#	def __on_child_returned(self, r):
#		self._on_child_returned(r)
	
	def _on_child_returned(self, r):
		"""
		The child callable has returned
		"""
		pass



