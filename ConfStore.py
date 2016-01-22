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
## Configuration Storage
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import os
import codecs
import StringIO

import DebugLog
Log = DebugLog.getLogger(__name__)

import ConfigParser

def __module_init():
	Log.Fine("Initialized")

class ConfigFile:
	Log = None
	PathName = None
	LastMod = None
	Parser = None
	def __init__(self,pathname=None):
		if pathname is not None:
			self.load(pathname)
	def load(self,pathname):
		self.PathName = pathname
		try:
			self.LastMod = os.stat(pathname).st_mtime
			ConfFile = codecs.open(pathname,'r','utf-8-sig')
		except Exception,e:
			Log.Warn("Could not open file '%s' - %s"%(pathname,e))
			# Create an empty file-like object
			ConfFile = StringIO.StringIO()
		self.loadData(os.path.basename(pathname),ConfFile)
	def refresh(self):
		try:
			NewMod = os.stat(self.PathName).st_mtime
			if NewMod == self.LastMod:
				return False
			self.LastMod = NewMod
			Log.Fine("Configuration '%s' changed, reloading..."%self.PathName)
			ConfFile = codecs.open(self.PathName,'r','utf-8-sig')
			self.loadData(os.path.basename(self.PathName),ConfFile)
			return True
		except Exception,e:
			if self.LastMod != None:
				Log.Warn("Could not open file '%s' - %s"%(self.PathName,e))
				self.LastMod = None
			return False
	def loadData(self,name,filehandle):
		Parser = ConfigParser.RawConfigParser(allow_no_value=True)
		Parser.optionxform=str
		Parser.readfp(filehandle)
		self.Parser = Parser
		self.Log = DebugLog.getLogger("ConfigFile[%s]"%name)
		self.Log.Fine("Loaded %d sections"%len(Parser.sections()))
	def __getValueDef(self,func,section,key,defval=None):
		try:
			val = func(section,key)
			self.Log.Fine("%s.%s = %s"%(section,key,val))
			return val
		except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
			self.Log.Fine("%s.%s : %s"%(section,key,defval))
			return defval
		except ValueError:
			self.Log.Warn("%s.%s ~ %s [%s]"%(section,key,defval,ValueError.args[0]))
			return defval
	def getTextDef(self,section,key,defval=None):
		return self.__getValueDef(self.Parser.get,section,key,defval)
	def getIntDef(self,section,key,defval=None):
		return self.__getValueDef(self.Parser.getint,section,key,defval)
	def getFloatDef(self,section,key,defval=None):
		return self.__getValueDef(self.Parser.getfloat,section,key,defval)
	def getBoolDef(self,section,key,defval=None):
		try:
			return self.Parser.getboolean(section,key)
		except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
			return defval
	def hasOption(self,section,option):
		return self.Parser.has_option(section,option)
	def getSections(self):
		return self.Parser.sections()
	def hasSection(self,section):
		return self.Parser.has_section(section)
	def getSection(self,section):
		if not self.hasSection(section):
			self.Log.Warn('Section [%s] not found'%section)
			return None
		else:
			sectiondata = self.Parser.items(section)
			self.Log.Fine('Section [%s]:'%section)
			for (key, val) in sectiondata:
				self.Log.Fine('\t%s = %s'%(key,val))
			return sectiondata
	def removeSection(self,section):
		return self.Parser.remove_section(section)
	def set(self,section,key,val):
		if not self.Parser.has_section(section):
			self.Log.Fine('New section [%s]'%section)
			self.Parser.add_section(section)
		self.Log.Fine("%s.%s < %s"%(section,key,val))
		self.Parser.set(section,key,val)
	def unset(self,section,key):
		self.Log.Fine("%s.%s *"%(section,key))
		self.Parser.remove_option(section,key)
	def save(self,altpathname=None):
		if altpathname is not None:
			outpathname = altpathname
		else:
			outpathname = self.PathName
		self.Parser.write(open(outpathname,'w'))
		self.Log.Fine("Saved %d sections"%len(self.Parser.sections()))

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	Log.LogExcept("Failed to initialize module '%s'"%__name__)
	raise Exception("Could not continue")
