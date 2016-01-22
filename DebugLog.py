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
## Debug Logging Utilities
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import sys
import os
import traceback

import time
import gzip
import StringIO
import logging
import threading

RootLogger = None
SubLoggerID = 0
LoggerLock = None

BackLog = []
LogTargets = {}
Log = None
BaseDir = None

DefLogLevel = None
DefLogTarget = None
DefLogPID = None

# Logging Configurations
LOG_LEVEL = 'ERROR'
#LOG_LEVEL = 'NOTSET'
LOG_TARGET = '>STDERR'
LOG_FORMAT = '%(LGR_PID)s\t%(asctime)s\t%(LGR_name)s\t%(levelname)s\t%(message)s'
LOG_EXCEPTION_TRACE = True

def __module_init():
	# For debugging only
	#print >>sys.stderr, "Module init: %s"%__name__
	refreshPID()
	
	global RootLogger, LoggerLock
	RootLogger = logging.getLogger()
	LoggerLock = threading.Lock()

class DebugLogger:
	LoggerLock = threading.Lock()
	SubLoggerID = 0
	LoggerName = None
	ParentLogger = None
	Logger = None
	LGRName = None
	# Constructor for a root or chain logger
	def __init__(self,name,logger,parent=None):
		ParentLogger = parent
		self.LGRName = (name,"(No Name)")[name is None]
		while ParentLogger is not None:
			self.LGRName = "%s."%(ParentLogger.LoggerName,'?')[ParentLogger.LoggerName is None]+self.LGRName
			ParentLogger = ParentLogger.ParentLogger
		self.ParentLogger = parent
		self.LoggerName = name
		self.Logger = logger
	# Configuration
	def addTarget(self,target):
		self.Logger.addHandler(target)
		self.Logger.propagate = False
	def flushTargets(self):
		for handler in self.Logger.handlers:
			self.Logger.removeHandler(handler)
	def setPropagate(self,propagate):
		self.Logger.propagate = propagate
	def setLevel(self,level):
		self.Logger.setLevel(level)
	# Forking
	def getLogger(self,ExtName=None):
		self.LoggerLock.acquire()
		try:
			SubLogger = self.Logger.getChild(str(self.SubLoggerID))
			self.SubLoggerID = self.SubLoggerID + 1
		finally:
			self.LoggerLock.release()
		return DebugLogger(ExtName,SubLogger,self)
	# Logging functions
	@staticmethod
	def __DoLog(func,msg,extra):
		global BackLog
		if BackLog is not None:
			BackLog.append((func,msg,extra))
		else:
			func(msg, extra=extra)
	def Fine(self,msg):
		self.__DoLog(self.Logger.debug,msg,{'LGR_name':self.LGRName,'LGR_PID':DefLogPID})
	def Info(self,msg):
		self.__DoLog(self.Logger.info,msg,{'LGR_name':self.LGRName,'LGR_PID':DefLogPID})
	def Warn(self,msg):
		self.__DoLog(self.Logger.warning,msg,{'LGR_name':self.LGRName,'LGR_PID':DefLogPID})
	def Error(self,msg):
		self.__DoLog(self.Logger.error,msg,{'LGR_name':self.LGRName,'LGR_PID':DefLogPID})
	def Fatal(self,msg):
		self.__DoLog(self.Logger.critical,msg,{'LGR_name':self.LGRName,'LGR_PID':DefLogPID})
	def LogExcept(self,msg=None):
		self.__DoLog(self.Logger.error,"[Exception]%s\n--------\n%s\n--------"%((" %s"%msg,'')[msg is None],
					 (sys.exc_value,traceback.format_exc().strip())[LOG_EXCEPTION_TRACE]),
					 {'LGR_name':self.LGRName,'LGR_PID':DefLogPID})

def parseTarget(target):
	Type = None
	Obj = None
	Mod = None
	if target[0] == '>':
		Type = "Stream"
		Obj = target[1:]
	else:
		Type = "File"
		Obj = target[1:]
		if target[0] == '!':
			Mod = "Rotate"
		elif target[0] == '*':
			Mod = "Truncate"
		elif target[0] == '+':
			Mod = "Append"
		else:
			Mod = target[0]
	return (Type,Obj,Mod)
	
def addTarget(target):
	_LOG_TARGET = None
	
	if target is not None:
		global LogTargets
		if target in LogTargets:
			# Note: this line will not trigger before initialization finish
			Log.Warn("Log target '%s' already added")
			return LogTargets[target]
		
		(Type,Obj,Mod) = parseTarget(target)
		# Will trigger pychecker warning, do not move to top for now.
		import logging.handlers
		if Type == "Stream":
			if Obj == 'STDERR':
				_LOG_TARGET = sys.stderr
			elif Obj == 'STDOUT':
				_LOG_TARGET = sys.stdout
			elif Obj == 'MEM':
				_LOG_TARGET = StringIO.StringIO()
			elif Obj == 'NULL':
				RootLogger.addHandler(logging.NullHandler())
			else:
				raise Exception("Unknown [%s] logging target specifier: '%s'"%(Type,Obj))
			if _LOG_TARGET is not None:
				__addTarget(logging.StreamHandler(_LOG_TARGET))
		elif Type == "File":
			if Mod == "Rotate":
				TargetPathName = __prepareFileTarget(Obj)
				
				class TimedRotatingSharedFileHandler(logging.handlers.TimedRotatingFileHandler):
					def _open(self):
						import PlatformOps
						if PlatformOps.PLATFORM == "Windows":
							import win32file
							OSFHandle = win32file.CreateFile(self.baseFilename,
											win32file.GENERIC_READ | win32file.GENERIC_WRITE,
											win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
											None, win32file.OPEN_ALWAYS, 0, 0)
							import msvcrt
							FDFlags = os.O_TEXT | ( os.O_APPEND if self.mode == 'a' else 0 )
							FD = msvcrt.open_osfhandle(OSFHandle, FDFlags)
							stream = os.fdopen(FD, self.mode)
							OSFHandle.Detach()
							return stream
						else:
							return logging.FileHandler._open(self)
				
				class GZTimedRotatingFileHandler(TimedRotatingSharedFileHandler):
				    def doRollover(self):
						# Figure out the rollover target file name
						currentTime = int(time.time())
						dstNow = time.localtime(currentTime)[-1]
						t = self.rolloverAt - self.interval
						if self.utc:
							timeTuple = time.gmtime(t)
						else:
							timeTuple = time.localtime(t)
							dstThen = timeTuple[-1]
							if dstNow != dstThen:
								if dstNow:
									addend = 3600
								else:
									addend = -3600
								timeTuple = time.localtime(t + addend)
						dfn = self.baseFilename + "." + time.strftime(self.suffix, timeTuple)
						try:
							# Perform the old rollover
							logging.handlers.TimedRotatingFileHandler.doRollover(self)
							# If succeed, perform gzip
							if os.path.exists(dfn):
								zfn = dfn+'.gz'
								if os.path.exists(zfn):
									os.remove(zfn)
								gzipFile = gzip.GzipFile(zfn, 'wb')
								gzipFile.write(file(dfn, 'rb').read())
								gzipFile.close()
								os.remove(dfn)
						except Exception, e:
							print >>sys.stderr, "WARNING: Failed to rotate log file '%s': %s"%(dfn,e)
				
				_LOG_TARGET = GZTimedRotatingFileHandler(TargetPathName,when='midnight',utc=True)
			elif Mod == "Truncate":
				TargetPathName = __prepareFileTarget(Obj)
				_LOG_TARGET = logging.FileHandler(TargetPathName, 'w+')
			elif Mod == "Append":
				TargetPathName = __prepareFileTarget(Obj)
				_LOG_TARGET = logging.FileHandler(TargetPathName, 'a')
			else:
				raise Exception("Unknown [%s] logging target specifier: '%s' (%s)"%(Type,Obj,Mod))
			if _LOG_TARGET is not None:
				__addTarget(_LOG_TARGET)
		else:
			raise Exception("Unrecognized logging target specifier: '%s' (Type: %s)"%(target,Type))
		LogTargets[target] = _LOG_TARGET
	
	return _LOG_TARGET

def __prepareFileTarget(logfile):
	# Ensure log file parent direct exsits
	if logfile[0] == '/':
		LogPathName = logfile
	elif logfile[0] == '~':
		LogPathName = os.path.expanduser(logfile)
	else:
		LogPathName = os.path.join(BaseDir,logfile)
	LogDir = os.path.dirname(LogPathName)
	if not os.path.exists(LogDir):
		os.makedirs(LogDir)
	# Ensure log file could be created
	open(LogPathName,'a').close()
	return LogPathName

def __addTarget(target):
	target.setFormatter(logging.Formatter(LOG_FORMAT))
	RootLogger.addHandler(target)

def flushTargets():
	for handler in RootLogger.handlers:
		RootLogger.removeHandler(handler)
	global LogTargets
	LogTargets = {}

def setLevel(level):
	RootLogger.setLevel(level)
	return getLevel()

def getLevel():
	return RootLogger.getEffectiveLevel()

def refreshPID():
	global DefLogPID
	DefLogPID = os.getpid()

def initialize(confFile,LogBaseDir=None):
	global BackLog
	if BackLog is None:
		raise Exception("Already initialized")
	global BaseDir
	BaseDir = os.getcwd() if LogBaseDir is None else LogBaseDir

	# Handle logging configurations
	global LOG_LEVEL, LOG_TARGET, LOG_EXCEPTION_TRACE
	LOG_LEVEL = confFile.getTextDef("Logging", "LogLevel", LOG_LEVEL)
	LOG_TARGET = confFile.getTextDef("Logging", "LogTarget", LOG_TARGET)
	LOG_EXCEPTION_TRACE = confFile.getBoolDef("Logging", "ExceptionTrace", LOG_EXCEPTION_TRACE)
	
	global DefLogLevel, DefLogTarget
	DefLogLevel = setLevel(LOG_LEVEL)
	DefLogTarget = addTarget(LOG_TARGET)
	
	# Write the heading of the new debug log
	RootLogger.info("=== Start of Debug Log ===",extra={'LGR_name':__name__,'LGR_PID':DefLogPID})
	
	# Process backed logs
	for (func,msg,extra) in BackLog:
		func(msg, extra=extra)
	BackLog = None
	
	# Get the Module logger
	global Log
	Log = getLogger(__name__)
	Log.Fine("Initialized")

def getLogger(BaseName=None):
	global SubLoggerID
	LoggerLock.acquire()
	try:
		SubLogger = RootLogger.getChild(str(SubLoggerID))
		SubLoggerID = SubLoggerID + 1
	finally:
		LoggerLock.release()
	return DebugLogger(BaseName,SubLogger)

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	print >>sys.stderr, "Failed to initialize module '%s': %s"%(__name__,e)
	print >>sys.stderr, traceback.format_exc().strip()
	raise Exception("Could not continue")
