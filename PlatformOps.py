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
## Unified Platform/OS Dependent Operations
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import os
import re
import sys
import time
import threading
import platform
import subprocess

import DebugLog
Log = DebugLog.getLogger(__name__)

PLATFORM = None
PROCESSOR = None
OS_NAME = None
OS_MAJORVER = None
OS_MINORVER = None

def __module_init():
	global PLATFORM
	PLATFORM = platform.system()
	Log.Fine("Running on '%s' platform"%PLATFORM)
	
	global OS_NAME,OS_VERSION
	if PLATFORM in OSInfo_PLATFORMS:
		OSInfo_PLATFORMS[PLATFORM]()
		Log.Fine("Normalized Platform: '%s'; OS: '%s'; VERSION: '%s|%s|%s'"%(PLATFORM,OS_NAME,PROCESSOR,OS_MAJORVER,OS_MINORVER))
	else:
		raise Exception("Unsupported platform '%s' for OS versioning"%PLATFORM)
	
	Log.Fine("Initialized")

def GetOSVersions_Linux():
	(osname, osversion, codename) = platform.linux_distribution()
	NormalizeName = re.match(r'(.*)\sLINUX.*', osname, re.IGNORECASE)
	if NormalizeName:
		osname = NormalizeName.group(1)
	osname = osname[:1].upper() + osname[1:]
	NormalizeVer = re.match(r'([^.]*(\.[^.]*)?)(\.?.*)?', osversion)
	if NormalizeVer:
		osversion = NormalizeVer.group(1)
	global PROCESSOR
	PROCESSOR = platform.machine()
	release = platform.release()
	global OS_NAME,OS_MAJORVER,OS_MINORVER
	OS_NAME = osname
	OS_MAJORVER = osversion
	OS_MINORVER = release

def GetOSVersions_Windows():
	(osrelease, osversion, splevel, proctype) = platform.win32_ver()
	global PROCESSOR
	PROCESSOR = platform.machine()
	global OS_NAME,OS_MAJORVER,OS_MINORVER
	OS_NAME = osrelease
	OS_MAJORVER = splevel
	OS_MINORVER = osversion

def GetOSVersions_MacOSX():
	global PROCESSOR
	PROCESSOR = platform.processor()
	if PROCESSOR == 'i386':
		PROCESSOR = ('i386','x86_64')[sys.maxsize.bit_length() > 32]
	release = platform.release()
	global PLATFORM,OS_NAME,OS_MAJORVER,OS_MINORVER
	OS_NAME = PLATFORM
	NormalizeVer = re.match(r'([^.]*)\.(.*)', release)
	OS_MAJORVER = NormalizeVer.group(1)
	OS_MINORVER = NormalizeVer.group(2)
	PLATFORM = "MacOS"

OSInfo_PLATFORMS = {}
OSInfo_PLATFORMS['Linux'] = GetOSVersions_Linux
OSInfo_PLATFORMS['Windows'] = GetOSVersions_Windows
OSInfo_PLATFORMS['Darwin'] = GetOSVersions_MacOSX

#----------------------------- Get Machine UUID ------------------------------
def GetMachineUUID():
	if PLATFORM in GetMachineUUID_PLATFORMS:
		return GetMachineUUID_PLATFORMS[PLATFORM]()
	else:
		raise Exception("Unsupported platform '%s' for collecting machine UUID"%PLATFORM)

def GetMachineUUID_Linux():
	MachineUUID = None
	# First try - non-privileged command
	try:
		MachineUUID = subprocess.check_output(["hal-get-property","--udi","/org/freedesktop/Hal/devices/computer","--key","system.hardware.uuid"]).strip()
		if len(MachineUUID) == 0:
			Log.Warn("Command 'hal-get-property' did not return any result")
			MachineUUID = None
	except Exception,e:
		Log.Warn("Failed to invoke 'hal-get-property': %s"%e)
	
	if MachineUUID is None:
		# Second try - privileged command
		try:
			MachineUUID = subprocess.check_output(["dmidecode","-s","system-uuid"]).strip()
			if len(MachineUUID) == 0:
				Log.Warn("Command 'dmidecode' did not return any result")
				MachineUUID = None
		except Exception,e:
			Log.Warn("Failed to invoke 'dmidecode': %s"%e)
	
	if MachineUUID is None:
		Log.Warn("Could not get machine UUID.\n"
				 "In order to enable this feature, you may:\n"
				 "1. Install the 'hal' package, which supports non-privileged machine UUID query; or\n"
				 "2. Install the 'dmidecode' package, and run this program as 'root'")
	return MachineUUID

def GetMachineUUID_Windows():
	from Lib import wmi
	return wmi.WMI().Win32_ComputerSystemProduct()[0].UUID

def GetMachineUUID_MacOS():
	raise Exception("Implement Me!")

GetMachineUUID_PLATFORMS = {}
GetMachineUUID_PLATFORMS['Linux'] = GetMachineUUID_Linux
GetMachineUUID_PLATFORMS['Windows'] = GetMachineUUID_Windows
GetMachineUUID_PLATFORMS['MacOS'] = GetMachineUUID_MacOS

#--------------------- Check for Administrator Privilege ---------------------

def TellRoot():
	if PLATFORM in TellRoot_PLATFORMS:
		return TellRoot_PLATFORMS[PLATFORM]()
	else:
		raise Exception("Unsupported platform '%s' for check administrator privilege"%PLATFORM)

def TellRoot_Linux():
	EUID = os.geteuid()
	isRoot = EUID == 0
	Log.Fine("%s as 'root' (Effective UID is %d)"%(("Not running","Running")[isRoot],EUID))
	return isRoot

def TellRoot_Windows():
	# Platform dependent package, do not move to top!
	from win32com.shell import shell
	isRoot = shell.IsUserAnAdmin()
	Log.Fine("%s as an administrator"%("Not running","Running")[isRoot])
	return isRoot
	
def TellRoot_MacOS():
	raise Exception("Implement Me!")

TellRoot_PLATFORMS = {}
TellRoot_PLATFORMS['Linux'] = TellRoot_Linux
TellRoot_PLATFORMS['Windows'] = TellRoot_Windows
TellRoot_PLATFORMS['MacOS'] = TellRoot_MacOS

#------------------- Check for Multiple Program Instances --------------------

MIN_SLEEPRES = 0.01

def RobustSingleInstance(lockfile_rel,required=False,Timeout=8,TimeRes=0.5):
	if TimeRes < MIN_SLEEPRES:
		raise Exception("Invalid timer resolution (%.2f, expect >= %.2f sec)"%(TimeRes,MIN_SLEEPRES))
	
	Locked = False
	TimeWait = 0
	while TimeWait < Timeout:
		Locked = SingleInstance(lockfile_rel)
		if not Locked:
			TimeWait+= TimeRes
			time.sleep(TimeRes if TimeWait <= Timeout else (Timeout-TimeWait+TimeRes))
		else:
			return TimeWait
	
	if SingleInstance(lockfile_rel):
		return Timeout
	else:
		if required:
			raise Exception("Failed to lock instance file '%s'%s"%(lockfile_rel,('',"in %.2f seconds"%Timeout)[Timeout>0]))
		else:
			Log.Warn("Unable to lock instance file '%s'%s"%(lockfile_rel,('',"in %.2f seconds"%Timeout)[Timeout>0]))
			return None

SingleInstance_LockHandle = None

def SingleInstance(lockfile_rel,required=False):
	if PLATFORM in SingleInstance_PLATFORMS:
		return SingleInstance_PLATFORMS[PLATFORM](lockfile_rel,required)
	else:
		raise Exception("Unsupported platform '%s' for single instance probing"%PLATFORM)

def SingleInstance_Linux(lockfile_rel,required):
	Locked = False
	LockFile = os.path.abspath(lockfile_rel)
	
	# Ensure lock file parent directory exsits
	LockDir = os.path.dirname(LockFile)
	if not os.path.exists(LockDir):
		os.makedirs(LockDir)
	
	# Create and request exclusive (EX) non-blocking (NB) advisory lock.
	# Code borrowed from http://linux.byexamples.com/archives/494/how-can-i-avoid-running-a-python-script-multiple-times-implement-file-locking/
	Log.Fine("Creating instance file '%s'..."%lockfile_rel)
	global SingleInstance_LockHandle
	SingleInstance_LockHandle = open(LockFile, 'w+')
	# Platform dependent package, do not move to top!
	import fcntl
	try:
		Log.Fine("Locking instance file '%s'..."%lockfile_rel)
		fcntl.lockf(SingleInstance_LockHandle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
		Locked = True
	except Exception,e:
		SingleInstance_LockHandle = None
		if required:
			raise Exception("Failed to lock instance file '%s' - %s"%(lockfile_rel,e))
		else:
			Log.Warn("Unable to lock instance file '%s' - %s"%(lockfile_rel,e))
	return Locked

def SingleInstance_Windows(lockfile_rel,required):
	LockFile = 'Global\\'+os.path.abspath(lockfile_rel).replace('\\','_')
	
	# Platform dependent package, do not move to top!
	import win32api
	# Platform dependent package, do not move to top!
	import win32event
	# Platform dependent package, do not move to top!
	import winerror
	
	Log.Fine("Creating named mutex '%s'..."%LockFile)
	global SingleInstance_LockHandle
	SingleInstance_LockHandle = win32event.CreateMutex(None, True, LockFile)
	ErrCode = win32api.GetLastError()
	
	Locked = (ErrCode == 0)
	if not Locked:
		SingleInstance_LockHandle = None
		ErrMessage = win32api.FormatMessage(ErrCode)
		if ErrCode != winerror.ERROR_ALREADY_EXISTS:
			raise Exception("Error creating instance mutex '%s' - %s"%(lockfile_rel,ErrMessage))
		if required:
			raise Exception("Failed to create instance mutex '%s' - %s"%(lockfile_rel,ErrMessage))
		else:
			Log.Warn("Unable to create instance mutex '%s' - %s"%(lockfile_rel,ErrMessage))
	return Locked

def SingleInstance_MacOS(lockfile_rel,required):
	raise Exception("Implement Me!")

SingleInstance_PLATFORMS = {}
SingleInstance_PLATFORMS['Linux'] = SingleInstance_Linux
SingleInstance_PLATFORMS['Windows'] = SingleInstance_Windows
SingleInstance_PLATFORMS['MacOS'] = SingleInstance_MacOS

def ReleaseSingleInstance(lockfile_rel):
	if PLATFORM in SingleInstance_Release_PLATFORMS:
		return SingleInstance_Release_PLATFORMS[PLATFORM](lockfile_rel)
	else:
		raise Exception("Unsupported platform '%s' for single instance releasing"%PLATFORM)
	
def SingleInstance_Release_Linux(lockfile_rel):
	if SingleInstance_LockHandle:
		SingleInstance_LockHandle.close()
		return True
	return False

def SingleInstance_Release_Windows(lockfile_rel):
	if SingleInstance_LockHandle:
		# Platform dependent package, do not move to top!
		import win32event
		win32event.ReleaseMutex(SingleInstance_LockHandle)
		return True
	return False

def SingleInstance_Release_MacOS(lockfile_rel):
	raise Exception("Implement Me!")

SingleInstance_Release_PLATFORMS = {}
SingleInstance_Release_PLATFORMS['Linux'] = SingleInstance_Release_Linux
SingleInstance_Release_PLATFORMS['Windows'] = SingleInstance_Release_Windows
SingleInstance_Release_PLATFORMS['MacOS'] = SingleInstance_Release_MacOS

#----------------------------- Generate PID File -----------------------------

def GeneratePID(pidfile_rel):
	if PLATFORM in GeneratePID_PLATFORMS:
		return GeneratePID_PLATFORMS[PLATFORM](pidfile_rel)
	else:
		raise Exception("Unsupported platform '%s' for PID file generation"%PLATFORM)

def GeneratePID_Linux_Windows(pidfile_rel):
	Succeed = False
	PIDFile = os.path.abspath(pidfile_rel)
	
	try:
		# Ensure pid file parent directory exsits
		PIDDir = os.path.dirname(PIDFile)
		if not os.path.exists(PIDDir):
			os.makedirs(PIDDir)
		
		# Create PID file
		pid = os.getpid()
		Log.Fine("Program running with PID: %d"%pid)
		fpid = file(PIDFile,"w+")
		try:
			fpid.write(str(pid))
		finally:
			fpid.close()
		Succeed = True
	except:
		Log.LogExcept("Failed to create PID file '%s'"%pidfile_rel)
	return Succeed

def GeneratePID_MacOS(pidfile_rel):
	raise Exception("Implement Me!")

GeneratePID_PLATFORMS = {}
GeneratePID_PLATFORMS['Linux'] = GeneratePID_Linux_Windows
GeneratePID_PLATFORMS['Windows'] = GeneratePID_Linux_Windows
GeneratePID_PLATFORMS['MacOS'] = GeneratePID_MacOS

#----------------------------- Retrieve PID File -----------------------------

def RetrievePID(pidfile_rel):
	if PLATFORM in RetrievePID_PLATFORMS:
		return RetrievePID_PLATFORMS[PLATFORM](pidfile_rel)
	else:
		raise Exception("Unsupported platform '%s' for PID file retrieval"%PLATFORM)

def RetrievePID_Linux_Windows(pidfile_rel):
	PIDFile = os.path.abspath(pidfile_rel)
	
	PID = None
	try:
		fpid = file(PIDFile,"r")
		try:
			PID = int(fpid.readline())
		finally:
			fpid.close()
	except:
		Log.LogExcept("Failed to read PID file '%s'"%pidfile_rel)
	return PID

def RetrievePID_MacOS(pidfile_rel):
	raise Exception("Implement Me!")

RetrievePID_PLATFORMS = {}
RetrievePID_PLATFORMS['Linux'] = RetrievePID_Linux_Windows
RetrievePID_PLATFORMS['Windows'] = RetrievePID_Linux_Windows
RetrievePID_PLATFORMS['MacOS'] = RetrievePID_MacOS

#----------------------------- Remove PID File -----------------------------

def RemovePID(pidfile_rel):
	if PLATFORM in RemovePID_PLATFORMS:
		return RemovePID_PLATFORMS[PLATFORM](pidfile_rel)
	else:
		raise Exception("Unsupported platform '%s' for PID file removal"%PLATFORM)

def RemovePID_Linux_Windows(pidfile_rel):
	Succeed = False
	PIDFile = os.path.abspath(pidfile_rel)
	
	Succeed = not os.path.exists(PIDFile)
	if not Succeed:
		try:
			os.remove(PIDFile)
			Succeed = True
		except:
			Log.LogExcept("Failed to remove PID file '%s'"%pidfile_rel)
	return Succeed

def RemovePID_MacOS(pidfile_rel):
	raise Exception("Implement Me!")

RemovePID_PLATFORMS = {}
RemovePID_PLATFORMS['Linux'] = RemovePID_Linux_Windows
RemovePID_PLATFORMS['Windows'] = RemovePID_Linux_Windows
RemovePID_PLATFORMS['MacOS'] = RemovePID_MacOS

#--------------------------- Daemonize the Program ---------------------------

def Daemonize(callback=None):
	if PLATFORM in Daemonize_PLATFORMS:
		return Daemonize_PLATFORMS[PLATFORM](callback)
	else:
		raise Exception("Unsupported platform '%s' for daemonization"%PLATFORM)

def Daemonize_Linux(callback):
	# Code borrowed from: http://code.activestate.com/recipes/278731-creating-a-daemon-the-python-way/
	# Create a communication cord between the parent and daemon child
	CordR,CordW = os.pipe()
	
	try:
		# Fork a child process so the parent can exit.  This returns control to
		# the command-line or shell.  It also guarantees that the child will not
		# be a process group leader, since the child receives a new process ID
		# and inherits the parent's process group ID.  This step is required
		# to insure that the next call to os.setsid is successful.
		pid = os.fork()
	except OSError, e:
		raise Exception, "Stage 1: %s (%d)" % (e.strerror, e.errno)
	
	if pid == 0:	# The first child.
		# To become the session leader of this new session and the process group
		# leader of the new process group, we call os.setsid().  The process is
		# also guaranteed not to have a controlling terminal.
		os.setsid()
		
		# Is ignoring SIGHUP necessary?
		#
		# It's often suggested that the SIGHUP signal should be ignored before
		# the second fork to avoid premature termination of the process.  The
		# reason is that when the first child terminates, all processes, e.g.
		# the second child, in the orphaned group will be sent a SIGHUP.
		#
		# "However, as part of the session management system, there are exactly
		# two cases where SIGHUP is sent on the death of a process:
		#
		#   1) When the process that dies is the session leader of a session that
		#      is attached to a terminal device, SIGHUP is sent to all processes
		#      in the foreground process group of that terminal device.
		#   2) When the death of a process causes a process group to become
		#      orphaned, and one or more processes in the orphaned group are
		#      stopped, then SIGHUP and SIGCONT are sent to all members of the
		#      orphaned group." [2]
		#
		# The first case can be ignored since the child is guaranteed not to have
		# a controlling terminal.  The second case isn't so easy to dismiss.
		# The process group is orphaned when the first child terminates and
		# POSIX.1 requires that every STOPPED process in an orphaned process
		# group be sent a SIGHUP signal followed by a SIGCONT signal.  Since the
		# second child is not STOPPED though, we can safely forego ignoring the
		# SIGHUP signal.  In any case, there are no ill-effects if it is ignored.
		#
		# import signal           # Set handlers for asynchronous events.
		# signal.signal(signal.SIGHUP, signal.SIG_IGN)
		
		# Refresh logger PID
		DebugLog.refreshPID()
		try:
			# Fork a second child and exit immediately to prevent zombies.  This
			# causes the second child process to be orphaned, making the init
			# process responsible for its cleanup.  And, since the first child is
			# a session leader without a controlling terminal, it's possible for
			# it to acquire one by opening a terminal in the future (System V-
			# based systems).  This second fork guarantees that the child is no
			# longer a session leader, preventing the daemon from ever acquiring
			# a controlling terminal.
			pid = os.fork()	# Fork a second child.
		except OSError, e:
			raise Exception, "Stage 2: %s [%d]" % (e.strerror, e.errno)
		
		if pid == 0:	# The second child.
			# Refresh logger PID
			DebugLog.refreshPID()
			# Close the read end of the cord
			os.close(CordR)
			return CordW
		else:
			# exit() or _exit()?  See below.
			os._exit(0)	# Exit parent (the first child) of the second child.
	else:
		# Close the write end of the cord
		os.close(CordW)
		# Process callback hook
		if callback is not None:
			callback(CordR)
		# exit() or _exit()?
		# _exit is like exit(), but it doesn't call any functions registered
		# with atexit (and on_exit) or any registered signal handlers.  It also
		# closes any open file descriptors.  Using exit() may cause all stdio
		# streams to be flushed twice and any temporary files may be unexpectedly
		# removed.  It's therefore recommended that child branches of a fork()
		# and the parent branch(es) of a daemon use _exit().
		Log.Fine("Parent process exiting...")
		os._exit(0)	# Exit parent of the first child.

def Daemonize_Windows(callback):
	# Platform dependent package, do not move to top!
	import servicemanager
	if servicemanager.RunningAsService():
		Log.Warn('Daemonization is not required when running as a service')
	else:
		raise Exception('Daemonization is achieved by running as a service')
	
def Daemonize_MacOS(callback):
	raise Exception("Implement Me!")

Daemonize_PLATFORMS = {}
Daemonize_PLATFORMS['Linux'] = Daemonize_Linux
Daemonize_PLATFORMS['Windows'] = Daemonize_Windows
Daemonize_PLATFORMS['MacOS'] = Daemonize_MacOS

#--------------------------- Redirect Standard I/O ---------------------------

def RedirectStdIO(stdin=None,stdout=None,stderr=None):
	if PLATFORM in RedirectStdIO_PLATFORMS:
		return RedirectStdIO_PLATFORMS[PLATFORM](stdin,stdout,stderr)
	else:
		raise Exception("Unsupported platform '%s' for standard I/O redirection"%PLATFORM)

Redirect_STDIN = None
Redirect_STDOUT = None
Redirect_STDERR = None

def RedirectStdIO_Linux(stdin,stdout,stderr):
	Log.Fine("Redirecting standard I/O...")
	
	if stdin is None:
		stdin = '/dev/null'
	global Redirect_STDIN
	Redirect_STDIN = open(stdin, 'r')
	os.dup2(Redirect_STDIN.fileno(), 0)	# standard input (0)
	
	if stdout is None:
		stdout = '/dev/null'
	global Redirect_STDOUT
	Redirect_STDOUT = open(stdout, 'w')
	os.dup2(Redirect_STDOUT.fileno(), 1)	# standard output (1)
	
	if stderr is None:
		stderr = '/dev/null'
	global Redirect_STDERR
	Redirect_STDERR = open(stderr, 'w')
	os.dup2(Redirect_STDOUT.fileno(), 2)	# standard error (2)
	
	return True

def RedirectStdIO_Windows(stdin,stdout,stderr):
	Log.Fine("Redirecting standard I/O...")
	
	if stdin is None:
		stdin = 'NUL'
	global Redirect_STDIN
	Redirect_STDIN = open(stdin, 'r')
	os.dup2(Redirect_STDIN.fileno(), 0)	# standard input (0)
	
	if stdout is None:
		stdout = 'NUL'
	global Redirect_STDOUT
	Redirect_STDOUT = open(stdout, 'w')
	os.dup2(Redirect_STDOUT.fileno(), 1)	# standard output (1)
	
	if stderr is None:
		stderr = 'NUL'
	global Redirect_STDERR
	Redirect_STDERR = open(stderr, 'w')
	os.dup2(Redirect_STDOUT.fileno(), 2)	# standard error (2)
	
	return True
	
def RedirectStdIO_MacOS(stdin,stdout,stderr):
	raise Exception("Implement Me!")

RedirectStdIO_PLATFORMS = {}
RedirectStdIO_PLATFORMS['Linux'] = RedirectStdIO_Linux
RedirectStdIO_PLATFORMS['Windows'] = RedirectStdIO_Windows
RedirectStdIO_PLATFORMS['MacOS'] = RedirectStdIO_MacOS

#------------------------------ Alertable Wait -------------------------------

def AlertableWait(key, waitsec):
	if PLATFORM in AlertableWait_PLATFORMS:
		return AlertableWait_PLATFORMS[PLATFORM](key, waitsec)
	else:
		raise Exception("Unsupported platform '%s' for alertable wait"%PLATFORM)

AlertHandleLock = threading.Lock()
AlertHandles = {}

def AlertableWait_Linux_Windows(key, waitsec):
	AlertHandleLock.acquire()
	try:
		if key in AlertHandles:
			raise Exception("Alertable key '%s' already in use"%key)
		AlertHandles[key] = threading.Event()
	finally:
		AlertHandleLock.release()
	
	try:
		return AlertHandles[key].wait(waitsec)
	finally:
		AlertHandleLock.acquire()
		try:
			del AlertHandles[key]
		finally:
			AlertHandleLock.release()

def AlertableWait_MacOS(key, waitsec):
	raise Exception("Implement Me!")

AlertableWait_PLATFORMS = {}
AlertableWait_PLATFORMS['Linux'] = AlertableWait_Linux_Windows
AlertableWait_PLATFORMS['Windows'] = AlertableWait_Linux_Windows
AlertableWait_PLATFORMS['MacOS'] = AlertableWait_MacOS

def WaitAlert(key):
	if PLATFORM in WaitAlert_PLATFORMS:
		return WaitAlert_PLATFORMS[PLATFORM](key)
	else:
		raise Exception("Unsupported platform '%s' for wait alert"%PLATFORM)

def WaitAlert_Linux_Windows(key):
	AlertHandleLock.acquire()
	try:
		if key not in AlertHandles:
			raise Exception("Alertable key '%s' not in use"%key)
		AlertHandles[key].set()
	finally:
		AlertHandleLock.release()

def WaitAlert_MacOS():
	raise Exception("Implement Me!")

WaitAlert_PLATFORMS = {}
WaitAlert_PLATFORMS['Linux'] = WaitAlert_Linux_Windows
WaitAlert_PLATFORMS['Windows'] = WaitAlert_Linux_Windows
WaitAlert_PLATFORMS['MacOS'] = WaitAlert_MacOS
	
#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	Log.LogExcept("Failed to initialize module '%s'"%__name__)
	raise Exception("Could not continue")
