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
## Universal Unique Identifier
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import sys

import DebugLog
Log = DebugLog.getLogger(__name__)

import uuid

UUID_NULL = uuid.UUID("00000000-0000-0000-0000-000000000000")

MachineUUID = None
HostName = None
HostUID = None

def __module_init():
	Log.Fine("Initialized")

def LazyInit():
	global HostUID
	if HostUID is None:
		# Generate unique host identifier of the local host
		HostUID = MakeHostUID()
		Log.Fine("LocalHost UID: %s"%str(HostUID))
	
def FromStr(str):
	return uuid.UUID(str)

def MakeHostUID(hostname=None,machine_uid=None):
	if hostname is None:
		global HostName
		if HostName is None:
			# Fetch host name of the local host
			import socket
			HostName = socket.getfqdn()
			Log.Fine("LocalHost name: %s"%HostName)
		hostname = HostName
	
	if machine_uid is None:
		global MachineUUID
		if MachineUUID is None:
			# Fetch unique identifier of the local machine
			import PlatformOps
			StrUUID = PlatformOps.GetMachineUUID()
			if StrUUID is not None:
				try:
					MachineUUID = FromStr(StrUUID)
				except Exception, e:
					Log.Warn("Failed to initialize machine UUID - %s"%e)
			if MachineUUID is None:
				MachineUUID = UUID_NULL
				Log.Warn("Could not acquire local machine's UUID, using stub value...")
			Log.Fine("Machine UUID: %s"%str(MachineUUID))
		machine_uid = MachineUUID
	
	return uuid.uuid5(machine_uid,hostname)
	
def HostNamespacedIdent(namespace,name,host_uid=None):
	if host_uid is None:
		LazyInit()
		host_uid = str(HostUID)
	return uuid.uuid5(namespace,"%s:%s"%(host_uid,name))

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	Log.LogExcept("Failed to initialize module '%s'"%__name__)
	raise Exception("Could not continue")
