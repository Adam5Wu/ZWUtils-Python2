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
## Console Service Utilities
## Author: Zhenyu Wu
## Revision 1: Jul. 2012 - Initial Implementation
## Revision 1.5: Jul. 2013 - Refactored from a previous project
## Revision 1.5: Jan. 22 2016 - Initial Public Release
#=============================================================================

import sys
import types

import DebugLog
Log = DebugLog.getLogger(__name__)

def __module_init():
	Log.Fine("Initialized")

#=============================================================================
#------------------------- Convert string to boolean -------------------------
#=============================================================================
def StrToBoolean(str,default=None):
#------------------------ Acceptable boolean strings -------------------------
	BOOLEAN_TRUE = ['TRUE','YES','Y','ON','1']
	BOOLEAN_FALSE = ['FALSE','NO','N','OFF','0']
	
	iStr = str.upper()
	if iStr in BOOLEAN_TRUE:
		return True
	elif iStr in BOOLEAN_FALSE:
		return False
	else:
#----------------------- Handle no matching condition ------------------------
		if type(default) is types.BooleanType:
			print >>sys.stdout, "? Ignored invalid Boolean string '%s'"%str
			return default
		elif type(default) is types.NoneType:
			raise Exception("Invalid Boolean string '%s'"%str)
		else:
			raise Exception("Invalid Boolean string '%s' and default parameter '%s'"%(str,default))

#=============================================================================
#--------------------- Print seconds in hh:mm:ss format ----------------------
#=============================================================================
def DispSecTime(sec):
	ret = '' if sec >= 0 else '-'
	sec = abs(sec)
	if sec > 3600:
		ret = ret+"%d:"%(sec/3600)
		sec = sec%3600
	ret = ret+"%02d:%02d"%(sec/60,sec%60)
	return ret

#=============================================================================
#------------------------- Visual rotate bar helper --------------------------
#=============================================================================
def RotateBar(idx):
	BAR = ('-','\\','|','/')
	return "[%s]%s"%(BAR[idx%len(BAR)],'\b'*3)

#=============================================================================
#-------------------- Get input from a list of candidates --------------------
#=============================================================================
def InputFromList(SelType, SrcList, RejList=[], AcceptEnter=False, PromptList=True, UseCompleter=True, ExactMatch=False):
	if UseCompleter:
		import readline
	
#---------------------------- Validate parameters ----------------------------
	for item in RejList:
		if item not in SrcList:
			raise Exception("Rejection item [%s] is not a candidate"%item)
	DispList = []
	for item in SrcList:
		if item not in RejList:
			if item in DispList:
				print >>sys.stdout, "? Ignored duplicate candidate [%s]"%item
			else:
				if item == '':
					if not AcceptEnter:
						raise Exception('Empty item cannot be a candidate')
				else:
					DispList.append(item)
	
	if len(DispList) == 0:
		if not AcceptEnter:
			raise Exception('Empty list of candidates')
#----------------------------- Prompt selections -----------------------------
	if PromptList:
		print >>sys.stdout, "Select %s from: [%s]"%(SelType, '] ['.join(DispList)),
		
		if AcceptEnter:
			print >>sys.stdout, '(or enter)'
		else:
			print
	
	if AcceptEnter:
			DispList.append('')
	
#------------------------------ Selection loop -------------------------------
	if UseCompleter:
		IDC = InduceCompleter(DispList)
		def Induce_Completer(text,idx):
			return IDC.complete(text,idx)
		OC = readline.get_completer()
		readline.set_completer(Induce_Completer)
	
	if len(DispList) == 1:
		if UseCompleter:
			Sel = [DispList[0]]
		else:
			Sel = DispList[0]
	else:
		Sel = [None]
	
	if UseCompleter:
		def Induce_Startup():
			if Sel[0] is not None:
				readline.insert_text(Sel[0])
		OSH = None #readline.get_startup_hook()
		readline.set_startup_hook(Induce_Startup)
	while Sel not in DispList:
		if (type(Sel) is not types.StringType) and (Sel[0] is not None):
			if (Sel[0] not in SrcList) and (Sel[1] is None):
				print >>sys.stdout, "! No such %s [%s]"%(SelType, Sel[0])
			if Sel[0] in RejList:
				print >>sys.stdout, "! Not allowed to select %s [%s]"%(SelType, Sel[0])
		Sel = InduceFromList(raw_input('Your choice: ').strip(), DispList, exact=ExactMatch)
		if UseCompleter and (type(Sel) is not types.StringType):
			readline.remove_history_item(readline.get_current_history_length()-1)
	
	if UseCompleter:
		readline.set_completer(OC)
		readline.set_startup_hook(OSH)
	
	if Sel != '':
		print >>sys.stdout, "Selected %s [%s]"%(SelType,Sel)
	return Sel

#=============================================================================
#---------------------- Induce item from candidate list ----------------------
#=============================================================================
def InduceFromList(Pfx, SrcList, quiet=False, exact=False):
#------------------------- Case-sensitive induction --------------------------
	canitems = []
	for item in SrcList:
		if item.startswith(Pfx):
			if (item == Pfx) and (not quiet):
				return Pfx
			else:
				if item != '':
					canitems.append(item)
	if len(canitems) > 0:
		if quiet:
			return canitems
		if len(canitems) == 1 and not exact:
			return canitems[0]
		else:
			print >>sys.stdout, "Candidates: [%s]"%'] ['.join(canitems)
			return [Pfx, canitems]
	
#------------------------ Case-insensitive induction -------------------------
	Pfx_lower = Pfx.lower()
	for item in SrcList:
		if item.lower().startswith(Pfx_lower):
			if item != '':
				canitems.append(item)
	if len(canitems) > 0:
		if quiet:
			return canitems
		if len(canitems) == 1:
			return canitems[0]
		else:
			print >>sys.stdout, "Possible candidates: [%s]"%'] ['.join(canitems)
			return [Pfx, canitems]
	
#-------------------------- Fail to find any match ---------------------------
	if not quiet:
		return [Pfx, None]
	else:
		return None

#=============================================================================
#--------------- Readline Completer using the Induction Engine ---------------
#=============================================================================
class InduceCompleter:
	def __init__(self, list):
		self.list = list
	def complete(self,text,idx):
		candidates = InduceFromList(text, self.list, quiet=True)
		while text in candidates:
			candidates.remove(text)
		if (candidates is not None) and (idx < len(candidates)):
			return candidates[idx]
		return None

#=============================================================================
#---------- Prompt for choices that can be selected by a single key ----------
#=============================================================================
def OneKeyChoice(Prompt, Keys, DefKey=None):
#---------------------------- Validate parameters ----------------------------
	if len(Keys) == 0:
		raise Exception('Empty list of keys')
	KeyList = []
	for item in Keys:
		Key = item[0]
		if Key != Key.lower():
			raise Exception("Key for selection '%s' must be lower case"%item)
		if Key is KeyList:
			raise Exception("Key for selection '%s' already assigned"%item)
		else:
			KeyList.append(Key)
	if DefKey is not None:
		if len(DefKey) != 1:
			raise Exception("Invalid default key '%s'"%DefKey)
		if DefKey not in KeyList:
			raise Exception("Default key '%s' not in list of keys"%DefKey)
	keyprompt = ''
	for key in Keys:
		keyprompt = keyprompt+"\033[30;47m%s\033[0m%s/"%(key[0],key[1:])

#------------------------------ Selection loop -------------------------------
	if len(KeyList) == 1:
		conin = KeyList[0]
	else:
		conin = None
	while conin is None:
		print >>sys.stdout, "%s [%s]"%(Prompt,keyprompt[:-1]),
		if DefKey is not None:
			print >>sys.stdout, "(%s)"%DefKey,
		conin = raw_input()
		
		if conin == '':
			if DefKey is not None:
				conin = DefKey
			else:
				conin = None
		else:
			SelKey = conin.lower()
			if SelKey in KeyList:
				pass
			else:
				conin = None
	return conin

#=============================================================================
#-------------------------- Decoding Stream Writer ---------------------------
#=============================================================================
class StreamDecodeWriter:
	def __init__(self, stream, decoder, errors='strict'):
		self.stream = stream
		self.decoder = decoder
		self.errors = errors
	def write(self, object):
		data, consumed = self.decoder(object, self.errors)
		self.stream.write(data)
	def writelines(self, list):
		self.write(''.join(list))
	def reset(self):
		pass
	def __getattr__(self, name, getattr=getattr):
		return getattr(self.stream, name)
	def __enter__(self):
		return self
	def __exit__(self, _type, _value, _tb):
		self.stream.close()

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	Log.LogExcept("Failed to initialize module '%s'"%__name__)
	raise Exception("Could not continue")
