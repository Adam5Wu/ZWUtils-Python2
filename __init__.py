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
## The ZWUtils Module
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import sys

# Module list for * loading
__all__ = [ "DebugLog", "Threading", "ConfStore", "Generators", "ModComm",
			"UUID", "FileSystem", "PlatformOps", "ConsoleKit" ]

def __package_init():
	# For debugging only
	#print >>sys.stderr, "Package init: %s"%__name__
	pass

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__package_init()
except Exception, e:
	print >>sys.stderr, "Failed to initialize package '%s': %s"%(__name__,e)
	import traceback
	print >>sys.stderr, traceback.format_exc().strip()
	raise Exception("Could not continue")
