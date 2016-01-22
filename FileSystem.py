# Copyright (c) 2011 - 2016, Zhenyu Wu, NEC Labs America Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of ZWUtils-Java nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#=============================================================================
## File System Operations
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import sys

import DebugLog
Log = DebugLog.getLogger(__name__)

import os
import stat
import time
import types

def __module_init():
	Log.Fine("Initialized")

UNIT = [ "bytes", "KB", "MB", "GB", "TB" ]

def GetRelPath(path):
	# Working with pyInstaller
	try:
		base_path = sys._MEIPASS
	except AttributeError:
		base_path = os.path.abspath('.')
	
	return os.path.join(base_path,path)

def FileSize(count):
	UCnt = 1
	while UCnt < len(UNIT):
		if abs(count) < 1024:
			break
		UCnt+= 1
		count = count / 1024.0
	UCnt-= 1
	return "%s %s"%((str(count),"%.2f"%count)[UCnt > 0],UNIT[UCnt])

def GetList(path,reclimit=0,include={},exclude={},follow={},enddecor=None):
	_include = {'File':True,'Dir':False,'Other':False}
	_exclude = {'Link':False,'Mount':False}
	_follow = {'Link':True,'Mount':True}
	for key in _include:
		if key in include:
			_include[key] = include[key]
	for key in _exclude:
		if key in exclude:
			_exclude[key] = exclude[key]
	for key in _follow:
		if key in follow:
			_follow[key] = follow[key]
	if enddecor not in (True,False,None):
		raise Exception("Unrecognized item-end decoration flag '%s'"%enddecor)
	
	retlist = []
	reclist = []
	dirlist = ['']
	while len(dirlist) > 0:
		while len(dirlist) > 0:
			tok = dirlist.pop()
			listdir = os.path.join(path,tok)
			entries = os.listdir(listdir)
			for entry in entries:
				entrypath = os.path.join(listdir,entry)
				entryfrag = os.path.join(tok,entry)
				if os.path.isfile(entrypath):
					if _include['File']:
						addentry = entryfrag
						if _exclude['Link'] and os.path.islink(entrypath):
							addentry = None
						if addentry is not None:
							retlist.append(addentry)
				elif os.path.isdir(entrypath):
					if _include['Dir']:
						addentry = entryfrag
						if _exclude['Link'] and os.path.islink(entrypath):
							addentry = None
						elif _exclude['Mount'] and os.path.ismount(entrypath):
							addentry = None
						if addentry is not None:
							if enddecor is None:
								if _include['File'] or _include['Other']:
									retlist.append(addentry+'/')
								else:
									retlist.append(addentry)
							else:
								retlist.append(addentry+('/' if enddecor else ''))
					if reclimit is None or reclimit > 0:
						addentry = entryfrag
						if not _follow['Link'] and os.path.islink(entrypath):
							addentry = None
						elif not _follow['Mount'] and os.path.ismount(entrypath):
							addentry = None
						if addentry is not None:
							reclist.append(addentry)
				else:
					if _include['Other']:
						addentry = entryfrag
						if _exclude['Link'] and os.path.islink(entrypath):
							addentry = None
						if addentry is not None:
							if enddecor is None:
								if _include['File'] or _include['Dir']:
									retlist.append(addentry+'?')
								else:
									retlist.append(addentry)
							else:
								retlist.append(addentry+('?' if enddecor else ''))
		dirlist = reclist
		reclist = []
		if reclimit is not None:
			reclimit-= 1
	return retlist

def ListDir(path, sortspecs={}):
	entries = os.listdir(path)
	dirlist = []
	maxfname = 0
	if len(entries) > 0:
		if type(sortspecs) is not types.DictType:
			raise Exception("Unexpected sorting specification '%s' %s"%(sortspecs,type(sortspecs)))
		for entry in entries:
			pathname = os.path.join(path,entry)
			fstat = os.stat(pathname)
			lstat = os.lstat(pathname)
			ftype = "FILE"
			fname = entry
			finfo = FileSize(fstat.st_size)
			if stat.S_ISDIR(fstat.st_mode):
				ftype = "DIR"
				finfo = "<DIR>"
			if stat.S_ISLNK(lstat.st_mode):
				finfo = "<SYMLINK>"
				fname = "%s [%s]"%(entry,os.path.relpath(os.path.realpath(pathname),path))
			dirlist.append((fname,"%-12s%s"%(finfo,time.ctime(fstat.st_mtime)),ftype))
			if maxfname < len(fname):
				maxfname = len(fname)
		if 'sortname' in sortspecs:
			dirlist.sort(key=lambda diritem: diritem[0], reverse=(True if sortspecs['sortname'] else False))
		if 'sortdir' in sortspecs:
			dirlist.sort(key=lambda diritem: diritem[2], reverse=(True if sortspecs['sortdir'] else False))
	else:
		dirlist = [("(Empty)","",None)]
	for diritem in dirlist:
		print >>sys.stdout, ('%-'+str(maxfname+3)+'s')%diritem[0]+diritem[1]

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	Log.LogExcept("Failed to initialize module '%s'"%__name__)
	raise Exception("Could not continue")
