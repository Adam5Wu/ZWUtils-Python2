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
## Communication Supplemental Module
## Author: Zhenyu Wu
## Revision 1: Jul. 2013 - Initial Implementation
## Revision 1: Jan. 22 2016 - Initial Public Release
#=============================================================================

import DebugLog
import PlatformOps
Log = DebugLog.getLogger(__name__)

import httplib

def __module_init():
	Log.Fine("Initialized")

class HTTPClient:
	Log = None
	ServerName = None
	ServerPort = None
	Connection = None
	Timeout = None
	def __init__(self,server,port=80,timeout=None,sslcontext=None):
		self.Log = DebugLog.getLogger("HTTPClient")
		self.Timeout = timeout
		self.SSLContext = sslcontext
		self.ChangeServer(server,port)
	def ChangeServer(self,server,port=80):
		if self.Connection is not None:
			self.Connection.close()
		self.ServerName = server
		self.ServerPort = port
		if self.SSLContext:
			self.Connection = httplib.HTTPSConnection(self.ServerName,self.ServerPort, strict=True,timeout=self.Timeout,context=self.SSLContext)
		else:
			self.Connection = httplib.HTTPConnection(self.ServerName,self.ServerPort, strict=True,timeout=self.Timeout)
	def Request(self,method,url,headers=None,data=None,cliaddrhdr=None):
		if self.Connection.sock is None:
			self.Log.Info("Connecting to %s:%s..."%(self.ServerName,self.ServerPort))
			self.Connection.connect()
		
		if headers is None:
			headers = {}
		if data is not None:
			data = str(data)
			headers['Content-Length'] = str(len(data))
			self.Log.Info("%s %s (%d headers, %d bytes content)"%(method,url,len(headers),len(data)))
		else:
			self.Log.Info("%s %s (%d headers)"%(method,url,len(headers)))
		
		try:
			if cliaddrhdr is not None:
				headers[cliaddrhdr] = self.Connection.sock.getsockname()[0]
			self.Connection.request(method,url,data,headers)
			Response = self.Connection.getresponse()
			if Response.length is not None:
				self.Log.Info("%d - '%s' (%d headers, %d bytes content)"%(Response.status,Response.reason,len(Response.getheaders()),Response.length))
			else:
				self.Log.Info("%d - '%s' (%d headers)"%(Response.status,Response.reason,len(Response.getheaders())))
			return Response
		except:
			self.Connection.close()
			raise Exception('Failed to complete request, connection closed')

if PlatformOps.PLATFORM == 'Linux':
	# Support for poll is not clear on non-Linux platforms
	import select
	import errno

	import BaseHTTPServer
	import SocketServer
	import socket
	
	import os
	import fcntl
	import time
	import threading

	class HTTPServer(BaseHTTPServer.HTTPServer):
		Log = None
		CusVer = None
		CommandHandlers = {}
		RequestTable = {}
		PendingRequest = {}
		AcceptRequest = {}
		Poll = select.poll()
		class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
			Log = None
			SSLPeer = None
			def __init__(self,request,client_address,server):
				self.Log = server.Log.getLogger("Handler")
				self.dofinish = self.finish
				self.finish = self._finish
				self.dosetup = self.setup
				self.setup = self._setup
				self.SockFD = request.fileno()
				BaseHTTPServer.BaseHTTPRequestHandler.__init__(self,request,client_address,server)
			def __getattr__(self,name):
				if name.startswith('do_'):
					if self.command in self.server.CommandHandlers:
						return self.HandleCommands
					self.Log.Warn("[%s] Could not find handler for command '%s'"%("%s:%s"%self.client_address,self.command))
				raise AttributeError
			def _setup(self):
				self.close_connection = 0
				self.server.PendingRequest[self.SockFD] = self
			def handle(self):
				self.handler = threading.Thread(target=self.greet, name="Greeting-%s:%s"%self.client_address)
				self.handler.daemon = True
				self.handler.start()
			def greet(self):
				try:
					try:
						if self.server.SSLContext:
							connection = self.request
							# Set the timeout to prevent blocking
							connection.settimeout(self.timeout)
							if self.server.AccpetNonSSL:
								try:
									handshake = connection.recv(4, socket.MSG_PEEK)
									if len(handshake) < 1 or ord(handshake[0]) != 0x16:
										# Non-SSL connection
										self.SSLPeer = 'N/A'
								except socket.timeout:
									# No handshake received, assuming non-SSL
									self.SSLPeer = 'N/A'
							if self.SSLPeer is None:
								self.Log.Fine("[%s] SSL handshaking..."%("%s:%s"%self.client_address))
								# Turn off Nagle to speed up communication
								connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
								self.request = self.server.SSLContext.wrap_socket(connection,server_side=True,do_handshake_on_connect=True)
								# Set wrapper socket timeout
								connection.settimeout(None)
								self.request.settimeout(self.timeout)
								# Really do the handshake
								self.request.do_handshake()
								if not self.disable_nagle_algorithm:
									# Restore Nagle if necessary
									connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, False)
								self.Log.Fine("[%s] SSL checking peer certificate..."%("%s:%s"%self.client_address))
								self.SSLPeer = self.request.getpeercert()
								self.Log.Fine("[%s] SSL connected."%("%s:%s"%self.client_address))
								if self.SSLPeer is None:
									self.SSLPeer = {}
						else:
							self.SSLPeer = 'N/A'
					finally:
						self.dosetup()
					# Connection established, wait to get served
					del self.server.PendingRequest[self.SockFD]
					self.server.AcceptRequest[self.SockFD] = self
					# Ring the service bell
					os.write(self.server.ReqSignal, '!')
				except Exception,e:
					self.Log.Warn("[%s] Failed to accept request connection - %s"%("%s:%s"%self.client_address,e))
					self.close_connection = 1
			def _finish(self):
				pass
			def teardown(self, unreg):
				if unreg:
					self.server.Poll.unregister(self.SockFD)
					del self.server.RequestTable[self.SockFD]
				try:
					self.dofinish()
				except Exception,e:
					self.Log.Warn("[%s] Failed to gracefully terminate connection - %s"%("%s:%s"%self.client_address,e))
				self.server.close_handler(self)
			def ServeRequest(self):
				try:
					self.Log.Info("[%s] Handling request..."%("%s:%s"%self.client_address))
					self.handle_one_request()
				except Exception,e:
					self.Log.Warn("[%s] Failed to handle request - %s"%("%s:%s"%self.client_address,e))
					self.close_connection = 2
			def HandleCommands(self):
				if 'Content-Length' in self.headers:
					self.ContentLen = int(self.headers['Content-Length'])
					self.Log.Info("[%s] %s %s (%d headers, %d bytes content)"%("%s:%s"%self.client_address,self.command,self.path,len(self.headers),self.ContentLen))
				else:
					self.ContentLen = None
					self.Log.Info("[%s] %s %s (%d headers)"%("%s:%s"%self.client_address,self.command,self.path,len(self.headers)))
				
				self.RespData = None
				self.RespHeading = None
				self.RespHeaders = {}
				
				Resp_wfile = self.wfile
				self.wfile = None
				Resp_send_response = self.send_response
				self.send_response = self._send_response
				Resp_send_error = self.send_error
				self.send_error = self._send_error
				Resp_send_header = self.send_header
				self.send_header = self._send_header
				Resp_end_headers = self.end_headers
				self.end_headers = self._end_headers
				try:
					try:
						self.server.CommandHandlers[self.command](self)
					except:
						self.Log.LogExcept("Error handling request")
						self.send_error(500)
					
					if self.RespHeading is None:
						if self.RespData is None:
							self.send_response(204)
						else:
							self.send_response(200)
				finally:
					self.send_response = Resp_send_response
					self.send_error = Resp_send_error
					self.send_header = Resp_send_header
					self.end_headers = Resp_end_headers
					self.wfile = Resp_wfile
				
				self.Log.Fine("Request handled, sending response...")
				RespMessage = self.RespHeading['Message'] if self.RespHeading['Message'] is not None else self.responses[self.RespHeading['Code']][0]
				if self.RespHeading['Error']:
					self.send_error(self.RespHeading['Code'],self.RespHeading['Message'])
					self.Log.Warn("[%s] %d %s"%("%s:%s"%self.client_address,self.RespHeading['Code'],RespMessage))
					self.close_connection = 3
				else:
					self.send_response(self.RespHeading['Code'],self.RespHeading['Message'])
					# Prepare / check payload length header
					if self.RespData is not None:
						RespLen = len(self.RespData)
						if 'Content-Length' in self.RespHeaders:
							if str(RespLen) != self.RespHeaders['Content-Length']:
								self.Log.Warn("Unmatched 'Content-Length' header and response content size (reported %s, actual %d)"%(self.RespHeaders['Content-Length'],RespLen))
						else:
							self.RespHeaders['Content-Length'] = str(RespLen)
						self.Log.Info("[%s] %d %s (%d headers, %d bytes content)"%("%s:%s"%self.client_address,self.RespHeading['Code'],RespMessage,len(self.RespHeaders),RespLen))
					else:
						if self.protocol_version == 'HTTP/1.1':
							self.RespHeaders['Content-Length'] = '0'
						self.Log.Info("[%s] %d %s (%d headers)"%("%s:%s"%self.client_address,self.RespHeading['Code'],RespMessage,len(self.RespHeaders)))
					# Send Headers if requested
					for key in self.RespHeaders:
						if len(key) > 0:
							self.send_header(key,self.RespHeaders[key])
					self.end_headers()
					# Send payload data if requested
					if self.RespData is not None:
						self.wfile.write(self.RespData)
				# Flush all sent content to network
				if not self.wfile.closed:
					self.wfile.flush()
			def _send_response(self,code,message=None):
				if self.RespHeading is not None:
					self.Log.Warn("Overwriting response heading (%s %d) -> (Normal %d)"%(('Normal','Error')[self.RespHeading['Error']],self.RespHeading['Code'],code))
				self.RespHeading = { 'Error': False, 'Code': code, 'Message': message }
			def _send_error(self,code,message=None):
				if self.RespHeading is not None:
					self.Log.Warn("Overwriting response heading (%s %d) -> (Error %d)"%(('Normal','Error')[self.RespHeading['Error']],self.RespHeading['Code'],code))
				self.RespHeading = { 'Error': True, 'Code': code, 'Message': message }
			def _send_header(self,key,message):
				if '' in self.RespHeaders:
					self.Log.Warn("Header already ended, ignoring assignment [%s] = '%s'"%(key,message))
				else:
					self.RespHeaders[key] = message
			def _end_headers(self):
				if '' in self.RespHeaders:
					self.Log.Warn("Header already ended")
				else:
					self.RespHeaders[''] = None
		def __init__(self,addr='',port=80,cusver=None,protocol='1.0',timeout=None,nagle=False,
					 sslcontext=None,nonsslfallback=False):
			self.Log = DebugLog.getLogger("HTTPServer")
			if cusver is not None:
				self.HTTPHandler.server_version = cusver[0]+'/'+cusver[1]
				self.HTTPHandler.sys_version = PlatformOps.OS_NAME+'/'+PlatformOps.OS_MAJORVER
			self.HTTPHandler.timeout = timeout
			self.HTTPHandler.protocol_version = 'HTTP/'+protocol
			self.HTTPHandler.disable_nagle_algorithm = not nagle
			BaseHTTPServer.HTTPServer.__init__(self,(addr,port),self.HTTPHandler)
			self.SSLContext = sslcontext
			self.AccpetNonSSL = nonsslfallback
			self.SockFD = self.socket.fileno()
			self.Poll.register(self.SockFD,select.POLLIN)
			self.ReqAck, self.ReqSignal = os.pipe()
			fcntl.fcntl(self.ReqAck, fcntl.F_SETFL, fcntl.fcntl(self.ReqAck, fcntl.F_GETFL) | os.O_NONBLOCK)
			self.Poll.register(self.ReqAck,select.POLLIN)
			self.ReqAckFile = os.fdopen(self.ReqAck)
		def handle_request(self, reqtimeout=60):
			timeout = self.socket.gettimeout()
			if timeout is None:
				timeout = reqtimeout
			elif reqtimeout is not None:
				timeout = min(timeout, reqtimeout)
			# Poll all sockets
			while True:
				pollStart = time.time()
				# Cleanup unsuccessful connections
				for SockFD, Req in self.PendingRequest.items():
					if Req.close_connection:
						del self.PendingRequest[SockFD]
						Req.teardown(False)
				for SockFD, Req in self.AcceptRequest.items():
					del self.AcceptRequest[SockFD]
					self.RequestTable[SockFD] = Req
					self.Poll.register(SockFD,select.POLLIN)
					self.Log.Info("[%s] Connection accepted (%d connected, %d pending)"%("%s:%s"%Req.client_address,len(self.RequestTable),len(self.PendingRequest)))
				try:
					RSocks = map(lambda entry: entry[0],self.Poll.poll(1000))
				except (OSError, select.error) as e:
					if e.args[0] != errno.EINTR:
						raise
				if self.ReqAck in RSocks:
					RSocks.remove(self.ReqAck)
					# Silence the service bell
					self.ReqAckFile.read()
				if len(RSocks) == 0:
					timeout -= time.time() - pollStart
					if timeout > 0:
						continue
				break
			# Serve connection request
			if self.SockFD in RSocks:
				RSocks.remove(self.SockFD)
				self._handle_request_noblock()
			else:
				self.handle_timeout()
			
			# Serve client requests
			ServeDone = []
			for SockFD in RSocks:
				Client = self.RequestTable[SockFD]
				Client.ServeRequest()
				if Client.close_connection:
					ServeDone.append(SockFD)
			# Cleanup finished request connections
			for SockFD in ServeDone:
				self.RequestTable[SockFD].teardown(True)
		def process_request(self,request,client_address):
			Client = self.RequestHandlerClass(request,client_address,self)
			self.Log.Info("Accepting connection from %s (%d connected, %d pending)"%("%s:%s"%client_address,len(self.RequestTable),len(self.PendingRequest)))
		def close_handler(self,handler):
			self.Log.Info("Shutdown connection from %s (%d connected, %d pending)"%("%s:%s"%handler.client_address,len(self.RequestTable),len(self.PendingRequest)))
			self.shutdown_request(handler.request)
		def implement_command(self,method,func):
			self.CommandHandlers[method] = func
			self.Log.Fine("Registered handler for command '%s'..."%method)

#=============================================================================
#----------------------------- Default Execution -----------------------------
#=============================================================================
try:
	__module_init()
except Exception, e:
	Log.LogExcept("Failed to initialize module '%s'"%__name__)
	raise Exception("Could not continue")
