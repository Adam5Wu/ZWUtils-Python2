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
## The Universal Main Function
## Desc: Invokes a configurable "Run Module"
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import sys

Log = None
Config = None

def __module_init():
	# For debugging only
	#print >>sys.stderr, "Module init: %s [%s]"%(__name__,os.getcwd())
	
	if __name__ != "__main__":
		raise Exception("This module must be the main module!")
	import os
	sys.path.append(os.getcwd())
	
	# Load configurations
	global Config
	import Config
	
	# Get the Main logger
	from Utilities import DebugLog
	global Log
	Log = DebugLog.getLogger("Main")
	Log.Fine("Initialized")

def RunModule(args):
	Log.Fine("Initializing run module...")
	Config.RUN_MODULE.Init(sys.modules[__name__])
	Log.Fine("Starting run module...")
	try:
		return Config.RUN_MODULE.Run(args)
	finally:
		Log.Fine("Run module terminated, finalizing...")
		Config.RUN_MODULE.FInit()
		Log.Fine("Run module finalized")

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	print >>sys.stderr, "Failed to initialize main module: %s"%e
	import traceback
	print >>sys.stderr, traceback.format_exc().strip()
	sys.exit(1)

try:
	if not RunModule(sys.argv):
		sys.exit(4)
except KeyboardInterrupt:
	Log.Warn('Keyboard interrupted')
	sys.exit(3)
except SystemExit:
	raise
except:
	Log.LogExcept("Exception during run module execution")
	sys.exit(2)
