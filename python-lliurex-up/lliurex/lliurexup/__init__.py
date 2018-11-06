import xmlrpclib 
import os
import shutil
import subprocess
import socket
import distutils.dir_util
import urllib2
import time
import psutil
import struct, fcntl


class LliurexUpCore(object):
	"""docstring for LliurexUpCore"""
	def __init__(self):
		super(LliurexUpCore, self).__init__()
		self.flavourReference=["lliurex-meta-server","lliurex-meta-client", "lliurex-meta-desktop", "lliurex-meta-music", "lliurex-meta-pyme", "lliurex-meta-infantil"] 
		self.defaultMirror = 'llx16'
		self.defaultVersion = 'xenial'
		self.lockTokenPath="/var/run/lliurexUp.lock"
		self.processPath = '/var/run/lliurex-up'
		self.sourcesListPath='/etc/apt/'
		self.changelogsPath = os.path.join(self.processPath,'changelogs')
		self.processSourceslist = os.path.join(self.processPath,'sourceslist')
		self.origsourcesfile=os.path.join(self.sourcesListPath,"sources.list")
		self.origsourcesfileback=os.path.join(self.sourcesListPath,"lliurexup_sources.list")
		self.targetMetapackagePath=os.path.join(self.processPath,"targetMetapackage")
		self.previousflavourspath = os.path.join(self.processPath,'previousflavours')
		self.errorpostaction_token=os.path.join(self.processPath,'errorpostaction_token')
		self.errorfinalmetapackage_token=os.path.join(self.processPath,'errorfinalmetapackage_token')
		self.errorupgrade_token=os.path.join(self.processPath,'errorupgrade_token')
		self.finalupgrade_token=os.path.join(self.processPath,'finalupgrade_token')

		self.initActionsPath='/usr/share/lliurex-up/initActions'
		self.preActionsPath = '/usr/share/lliurex-up/preActions'
		self.postActionsPath = '/usr/share/lliurex-up/postActions'

	#def __init__	

	def startLliurexUp(self):

		self.createLockToken()
		self.retryN4d=True
		self.n4dStatus=True
		self.n4d = xmlrpclib.ServerProxy('https://localhost:9779')
		self.checkN4dStatus()
		self.haveLliurexMirror = False
		self.metapackageRef=[]
		self.previousFlavours = []

		
		self.getTargetMetapackage()
		self.flavours = []
		self.getPreviousFlavours()
		
		if self.n4dStatus:
			if len(self.n4d.get_methods('MirrorManager')) > 0:
				self.haveLliurexMirror = True
			
		self.retryN4d=True
		self.prepareEnvironment()

	#def startLliurexUp	

	def isLliurexUpLocked(self):

		'''
		 0: Lliurex-Up is not running
		 1: Lliurex-Up is running
		 2: Lliurex-Up is locked for previous failed process
		 ''' 

		if os.path.exists(self.lockTokenPath):
			f=open(self.lockTokenPath,'r')
			up_pid=f.readline().split('\n')[0]
			if up_pid !="":
				up_pid=int(up_pid)
				check_pid=psutil.pid_exists(up_pid)
				if check_pid:
					code=1
				else:
					code=2
			else:
				code=1
				
		else:
			code=0

		return code	

	#def isLliurexUpLocked		

	def isAptLocked(self):

		'''
		 0: Apt is not running
		 1: Apt is running
		 2: Apt is locked for previous failed process
		 ''' 

		f= open("/var/lib/apt/lists/lock", 'w')
		try:
			fcntl.lockf(f, fcntl.LOCK_EX|fcntl.LOCK_NB)
			code=0
		except IOError:
			apt_run=self.find_process("apt-get")
			if apt_run!=None:
				code =1
			else:
				code=2

		return code	


	#def isAptLocked
		
	def isDpkgLocked(self):

		'''
		 0: Dpkgis not running
		 1: Dpkg is running
		 2: Dpkg is locked for previous failed process
		 3: Apt is running

		 ''' 

		f= open("/var/lib/dpkg/lock", 'w')
		try:
			fcntl.lockf(f, fcntl.LOCK_EX|fcntl.LOCK_NB)
			code=0
		except IOError:
			dpkg_run=self.find_process("dpkg")
 			if dpkg_run!=None:
				code =1
			else:
				apt_run=self.find_process("apt-get")
				if apt_run!=None:
					code=3
				else:
					code=2	

		return code		
			

	#def isAptLocked			

	def unlockerCommand(self):


		return "/usr/sbin/dpkg-unlocker-cli unlock -u"

	#def unlockeCommand				


	def createLockToken(self):

		if not os.path.exists(self.lockTokenPath):
			f=open(self.lockTokenPath,'w')
			up_pid=os.getpid()
			f.write(str(up_pid))
			f.close()

	#def createLockToken		

	def getPreviousFlavours(self):
		
		if os.path.exists(self.previousflavourspath):
			aux = open(self.previousflavourspath,'r')
			lines = aux.readlines()
			for x in lines:
				self.previousFlavours.append(x.strip())
			aux.close()

	#def getPreviousFlavours		

	def checkN4dStatus(self):
	
		checkStatus=True
		cmd='systemctl status n4d.service 1>/dev/null'
		result=os.system(cmd)

		if result !=0:
			if self.retryN4d:
				self.retryN4d=False
				try: 
					cmd='systemctl restart n4d.service 1>/dev/null'
		 			restart=os.system(cmd)
		 			time.sleep(5)
		 			if restart ==0:
		 				self.checkN4dStatus()
		 			else:
		 				self.n4dStatus=False
		 						 				
				except Exception as e:
					self.n4dStatus=False
					
					
			else:
				self.n4dStatus=False
				
										
		else:		
			self.n4dStatus=True

	#def checkN4dStatus		
			
				
	def getTargetMetapackage(self):

		if os.path.exists(self.targetMetapackagePath):
			aux = open(self.targetMetapackagePath,'r')
			lines = aux.readlines()
			for x in lines:
				self.metapackageRef.append(x.strip())
			aux.close()		

	#def getTargetMetapackage
			
	def saveTargetMetapackage(self,targetMetapackage):

		aux=open(self.targetMetapackagePath,'w')
		x=targetMetapackage.split("-")[2]
		aux.write(x+"\n")
		x="edu"
		aux.write(x+"\n")
		aux.close()

	#def saveTargetMetapackage	

	def checkInitialFlavour(self,args=None):

		self.targetMetapackage=self.checkFlavour()
		if len(self.metapackageRef)==0:
			self.getTargetMetapackage()
	 	
	 	self.metapackageRef=sorted(self.metapackageRef)	
		 	 
		if len(self.previousFlavours)==0:
			self.getPreviousFlavours()
		

		self.writeDefaultSourceslist()
		self.writeDefaultSourceslistMirror()
		self.writeDefaultSourceslistAll()

		self.addSourcesListLliurex(args)

		return self.targetMetapackage

	#def checkInitialFlavour	
		
	def updateFlavoursList(self):
		
		#self.flavours = [ x.strip() for x in self.n4d.lliurex_version('','LliurexVersion','-v')[1].split(',') ]
		cmd='lliurex-version -v'
		p=subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE)
		result=p.communicate()
		self.flavours = [ x.strip() for x in result[0].split(',') ]

		if len(self.flavours) > 0:
			aux = open(self.previousflavourspath,'w')
			for x in self.flavours:
				aux.write(x+"\n")
			aux.close()

	#def updateFlavoursList		

	def writeDefaultSourceslist(self):

		f = open(os.path.join(self.processSourceslist,'default'),'w')
		f.write('deb http://lliurex.net/{version} {version} main restricted universe multiverse\n'.format(version=self.defaultVersion))
		f.write('deb http://lliurex.net/{version} {version}-updates main restricted universe multiverse\n'.format(version=self.defaultVersion))
		f.write('deb http://lliurex.net/{version} {version}-security main restricted universe multiverse\n'.format(version=self.defaultVersion))
		f.close()

	#def writeDefaultSourceslist	

	def writeDefaultSourceslistMirror(self):
		
		f = open(os.path.join(self.processSourceslist,'default_mirror'),'w')
		f.write('deb http://mirror/{version_mirror} {version} main restricted universe multiverse\n'.format(version_mirror=self.defaultMirror,version=self.defaultVersion))
		f.write('deb http://mirror/{version_mirror} {version}-updates main restricted universe multiverse\n'.format(version_mirror=self.defaultMirror,version=self.defaultVersion))
		f.write('deb http://mirror/{version_mirror} {version}-security main restricted universe multiverse\n'.format(version_mirror=self.defaultMirror,version=self.defaultVersion))
		f.close()	

	#def writeDefaultSourceslistMirror	


	def writeDefaultSourceslistAll(self):
		
		f = open(os.path.join(self.processSourceslist,'default_all'),'w')
		f.write('deb http://mirror/{version_mirror} {version} main restricted universe multiverse\n'.format(version_mirror=self.defaultMirror,version=self.defaultVersion))
		f.write('deb http://mirror/{version_mirror} {version}-updates main restricted universe multiverse\n'.format(version_mirror=self.defaultMirror,version=self.defaultVersion))
		f.write('deb http://mirror/{version_mirror} {version}-security main restricted universe multiverse\n'.format(version_mirror=self.defaultMirror,version=self.defaultVersion))
		f.write('deb http://lliurex.net/{version} {version} main restricted universe multiverse\n'.format(version=self.defaultVersion))
		f.write('deb http://lliurex.net/{version} {version}-updates main restricted universe multiverse\n'.format(version=self.defaultVersion))
		f.write('deb http://lliurex.net/{version} {version}-security main restricted universe multiverse\n'.format(version=self.defaultVersion))
		f.close()	

	#def writeDefaultSourceslistAll		

	def prepareEnvironment(self):
		'''
			This funcion delete all environment and rebuild environment

		'''
		self.cleanEnvironment()
		if not os.path.exists(self.processPath):
			os.mkdir(self.processPath)
		if not os.path.exists(self.processSourceslist):
			os.mkdir(self.processSourceslist)
		if not os.path.exists(self.changelogsPath):
			os.mkdir(self.changelogsPath)

		#self.writeDefaultSourceslist()
		#self.writeDefaultSourceslistMirror()

	#def prepareEnvironment	

	def addSourcesListLliurex(self,args=None):
		
		#sourcesrefmirror=os.path.join(self.processSourceslist, 'default_mirror')

		newsourcesfile=os.path.join(self.sourcesListPath,'sources.list')
		extrasources=[]
		client=False
		textsearch_mirror="/mirror/"+str(self.defaultMirror)
		textsearch_lliurex="/lliurex.net/"+str(self.defaultVersion)


		if self.targetMetapackage=="lliurex-meta-client" or "client" in self.previousFlavours or "client" in self.metapackageRef:
			client=True
			if args:
				sourcesref=os.path.join(self.processSourceslist, 'default_all')

			else:
				#textsearch="/mirror/"+str(self.defaultMirror)
				sourcesref=os.path.join(self.processSourceslist, 'default_mirror')

		else:
			#textsearch="/lliurex.net/"+str(self.defaultVersion)
			sourcesref=os.path.join(self.processSourceslist, 'default')	

		if os.path.exists(self.origsourcesfile):
			os.rename(self.origsourcesfile,self.origsourcesfileback)
			origsources=open(self.origsourcesfileback,'r')
			if not client:
				for line in origsources:
					if not textsearch_lliurex in line:
						extrasources.append(line.strip())
			else:
				for line in origsources:
					if args:
						if (not textsearch_lliurex in line) and (not textsearch_mirror in line):
							extrasources.append(line.strip())
					else:
						if not textsearch_mirror in line:
							extrasources.append(line.strip())		
												

			origsources.close()
				
			if os.path.exists(sourcesref):
				shutil.copy(sourcesref,self.origsourcesfile)
				if len(extrasources)>0:	
					newsourcesedit=open(newsourcesfile,'a')
					for line in extrasources:
						newsourcesedit.write(line+'\n')
					newsourcesedit.close()
			else:
				os.rename(self.origsourcesfileback,self.origsourcesfile)					
	
	#def addSourcesListLliurex 		

	def restoreOrigSourcesList(self):
		
		if os.path.exists(self.origsourcesfileback):
			os.rename(self.origsourcesfileback,self.origsourcesfile)

	#def restoreOrigSourcesList		

	def readSourcesList(self):
		
		count=0
		if os.path.exists(self.origsourcesfile):
			sources=open(self.origsourcesfile,'r')
			ref="/lliurex.net/"+str(self.defaultVersion)
			for line in sources:
				if ref in line:
					if not "#" in line:
						count=count+1
		return count	

	#def readSourcesList		

	def cleanEnvironment(self):
		
		if os.path.exists(self.processPath):
			shutil.rmtree(os.path.join(self.processPath))

		self.restoreOrigSourcesList()	

	#def cleanEnvironment	

	def cleanLliurexUpLock(self):

		if os.path.exists(self.lockTokenPath):
			os.remove(self.lockTokenPath)

	#def cleanLliurexUpLock		

	def updateCacheApt(self,options=""):
		
		command = "LANG=C LANGUAGE=en apt-get update {options}".format(options=options)
		subprocess.Popen(command,shell=True).communicate()

	#def updateCacheApt	


	def getPackageVersionAvailable(self,package,options=""):
		'''
			Args :
				package String
				options String

			return dictionary => result
			result : {'installed':String,'candidate':String}

			Options are Apt options 
		'''
		command = "LANG=C LANGUAGE=en apt-cache policy {package} {options}".format(package=package,options=options)
		p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE)
		installed = None
		candidate = None
		for line in iter(p.stdout.readline,""):
			stripedline = line.strip()
			if stripedline.startswith("Installed"):
				installed = stripedline.replace("Installed: ","")
			if stripedline.startswith("Candidate"):
				candidate = stripedline.replace("Candidate: ","")
		return {"installed":installed,"candidate":candidate}

	#def getPackageVersionAvailable	

	def isLliurexUpIsUpdated(self,args=None):
		'''
			return Boolean 
		'''
		sourceslistDefaultPath = os.path.join(self.processSourceslist,'default')

		if "client" in self.previousFlavours or "lliurex-meta-client"==self.targetMetapackage:
			if not args:
				sources=self.readSourcesList()
				if sources==0:
					sourceslistDefaultPath = os.path.join(self.processSourceslist,'default_mirror')


		options = ""
		if self.canConnectToLliurexNet():
			options = "-o Dir::Etc::sourcelist={sourceslistOnlyLliurex} -o Dir::Etc::sourceparts=/dev/null".format(sourceslistOnlyLliurex=sourceslistDefaultPath)

		self.updateCacheApt(options)
		result = self.getPackageVersionAvailable('lliurex-up',options)

		if result['installed'] != result['candidate']:
			return False
		return True

	#def isLliurexUpIsUpdated	

	def installLliurexUp(self,options=""):
		'''
			Args :
				options String
			return dictionary => result
			result : {'returncode':Int,'stdout':String,'stderr':String}

			options are Apt options
			

			This function install lliurex-up
		'''
		self.updateCacheApt(options)
		command = "LANG=C LANGUAGE=en DEBIAN_FRONTEND=noninteractive apt-get install --allow-downgrades --allow-remove-essential --allow-change-held-packages --yes lliurex-up {options}".format(options=options)
		p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE)
		poutput,perror = p.communicate()
		return {'returncode':p.returncode,'stdout':poutput,'stderrs':perror}

	#def installLliurexUp	

	def lliurexMirrorIsUpdated(self):
		'''
			return None | dictionary => result
			result : {'status':Boolean,'msg':String,'action':String}
			result.msg : message of status
			result.action : Action to launch
		'''
		if self.haveLliurexMirror and ('server' in self.flavours or 'lliurex-meta-server'==self.targetMetapackage):
			result = self.n4d.is_update_available('','MirrorManager',self.defaultMirror)
			return result
		return None

	#def lliurexMirrorIsUpdated	

	def lliurexMirrorIsRunning(self):
		'''
			return Boolean
		'''
		if self.haveLliurexMirror and ('server' in self.flavours or 'lliurex-meta-server'==self.targetMetapackage):
			result = self.n4d.is_alive('','MirrorManager')
			return result['status']
		return False

	#def lliurexMirrorIsRunning	

	def clientCheckingMirrorIsRunning(self):

		if self.targetMetapackage=="lliurex-meta-client" or "client" in self.previousFlavours or "client" in self.metapackageRef:
			
			try:
				client=xmlrpclib.ServerProxy('https://server:9779')
				result=client.is_alive('','MirrorManager')
				return {'ismirrorrunning':result['status'],'exception':False}
			
			except Exception as e:
				return {'ismirrorrunning':None,'exception':str(e)}	

		return {'ismirrorrunning':False,'exception':False}	

	#def clientCheckingMirrorIsRunning	

	def getPercentageLliurexMirror(self):
		'''
			return int | None
		'''
		if self.haveLliurexMirror and ('server' in self.flavours or 'lliurex-meta-server'==self.targetMetapackage):
			result = self.n4d.get_percentage('','MirrorManager',self.defaultMirror)
			if result['status']:
				return result['msg']
		return None

	#def getPercentageLliurexMirror	
	
	def checkFlavour(self):
		'''
			return None|String
			If metapackages has been uninstalled, this function return 
			package to must install. If return None, you are ok and don't need 
			install anything.
		'''
		self.updateFlavoursList()
		targetMetapackage = None
		if 'None' in self.flavours:
			# get last flavour
			#result = self.n4d.lliurex_version('','LliurexVersion','--history')
			cmd='lliurex-version --history'
			p=subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE)
			result=p.communicate()
			if result[0]:
				#history = [ x.strip().split('\t')[0].strip() for x in result[1].split('\n') ]
				history = [ x.strip().split('\t')[0].strip() for x in result[0].split('\n') ]
				history = [ x for x in history if not 'lliurex-meta-live' in x ]
				for x in reversed(history):
					if x.startswith('-'):
						targetMetapackage = x[2:]
						break

		if targetMetapackage !=None:
			self.saveTargetMetapackage(targetMetapackage)				
		return targetMetapackage

	#def checkFlavour	

	def canConnectToLliurexNet(self):
		'''
			return Boolean
		'''
		'''
		s =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		host = socket.gethostbyname('lliurex.net')
		result = s.connect_ex((host, 80))
		s.close()
		if result:
		 	return False
		return True
		'''
		try:
			req=urllib2.Request("http://lliurex.net/xenial")
			res=urllib2.urlopen(req)
			return True
		except:
			return False

	#def canConnectToLliurexNet		
				
	def getLliurexVersionLliurexNet(self):
		'''
			return dictionary => result
			result : {'installed':String,'candidate':String}
		'''
		sourceslistDefaultPath = os.path.join(self.processSourceslist,'default')
		options = ""
		if self.canConnectToLliurexNet():
			options = "-o Dir::Etc::sourcelist={sourceslistOnlyLliurex} -o Dir::Etc::sourceparts=/dev/null".format(sourceslistOnlyLliurex=sourceslistDefaultPath)
		self.updateCacheApt(options)
		return self.getPackageVersionAvailable('lliurex-version-timestamp',options)

	#def getLliurexVersionLliurexNet	
	
	def getLliurexVersionLocal(self):
		
		self.updateCacheApt('')
		return self.getPackageVersionAvailable('lliurex-version-timestamp','')		

	#def getLliurexVersionLocal

	def initActionsScript(self,arg):
		
		#return 'run-parts --arg="initActions" ' + self.initActionsPath
		return 'run-parts --arg=' +str(arg) + ' ' + self.initActionsPath

	#def initActionsScript

	def preActionsScript(self):
		
		return 'run-parts --arg="preActions" ' + self.preActionsPath

	#def preActionsScript

	def postActionsScript(self):
		
		return 'run-parts --arg="postActions" ' + self.postActionsPath

	'''	
	#def postActionsScript

	def requiresInstallFlavour(self):
		
		flavourToInstall=None
		
		if not 'None' in self.previuosFlavours:
			if self.previuosFlavours !=self.flavours:
				flavourToInstall=self.parseFlavourToInstall(self.previousFlavours)
										
		else:
			
			if self.metapackageRef != self.flavours:
				flavourToInstall=self.parseFlavourToInstall(self.metapackageRef)
							

		return flavourToInstall			 		

		
	def parseFlavourToInstall(self,flavours):
	
		parse_flavour=""

		for item in flavours:
			if item != "edu":
				parse_flavour=parse_flavour + " " + "lliurex-meta-" + item

		return parse_flavour
			
	#def parseFlavourToInstall
	'''

	def installInitialFlavour(self,flavourToInstall,options=""):
		'''
			Args :
				flavourToInstall String
				options String
			return dictionary => result
			result : {'returncode':Int,'stdout':String,'stderr':String}

			options are Apt options
			

			This function install lliurex-up
		'''
		self.updateCacheApt(options)
		command = "LANG=C LANGUAGE=en DEBIAN_FRONTEND=noninteractive apt-get install --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages " + flavourToInstall + "{options} ".format(options=options)
		p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE)
		poutput,perror = p.communicate()
		
		if p.returncode!=0:
			command = "LANG=C LANGUAGE=en DEBIAN_FRONTEND=noninteractive apt-get install -f --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages {options} ".format(options=options)
			p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
			poutput,perror = p.communicate()


		return {'returncode':p.returncode,'stdout':poutput,'stderrs':perror}	

	#def installInitialFlavour

	def getPackagesToUpdate(self):
		'''
			packageInfo definition
			{
				'PACKAGENAME' : {
						'install' : 'INSTALLEDVERSION',
						'candidate' : 'CANDIDATEVERSION',
						'icon' : 'ICONNAME',
						'changelog' : 'CHANGELOGTEXT'
				}
			}
		'''
		self.packageInfo = {}
		self.updateCacheApt("")
		psimulate = subprocess.Popen('LANG=C LANGUAGE=en apt-get dist-upgrade -sV',shell=True,stdout=subprocess.PIPE)
		rawoutputpsimulate = psimulate.stdout.readlines()
		rawpackagestoinstall = [ aux.strip() for aux in rawoutputpsimulate if aux.startswith('Inst') ]
		r = [ aux.replace('Inst ','') for aux in rawpackagestoinstall ]
		for allinfo in r :
			self.packageInfo[allinfo.split(' ')[0]] = {}
			self.packageInfo[allinfo.split(' ')[0]]['raw'] = ' '.join(allinfo.split(' ')[1:])

		for package in self.packageInfo:
			raw = self.packageInfo[package]['raw'].split(' ')
			if raw[0].startswith('['):
				self.packageInfo[package]['install'] = raw[0][1:-1]
				self.packageInfo[package]['candidate'] = raw[1][1:]
			elif raw[0].startswith('('):
				self.packageInfo[package]['install'] = None
				self.packageInfo[package]['candidate'] = raw[0][1:]
			self.packageInfo[package].pop('raw')
			#packageInfo[package]['changelog'] = os.path.join(self.changelogsPath,package)
			#os.system('LANG=C LANGUAGE=en apt-get changelog %s > %s%s'%(package,self.changelogsPath,package))
			#packageInfo[package]['icon'] = 
		return self.packageInfo

	#def getPackagesToUpdate
		
	def checkIncorrectFlavours(self):
		
		self.incorrect_flavours=[]
		count=0

		for item in self.packageInfo:
			if item in self.flavourReference:
				self.incorrect_flavours.append(item)


		if len(self.incorrect_flavours)>0:

			for item in self.incorrect_flavours:
				if self.targetMetapackage != None:
					if item != self.targetMetapackage:
						count=count+1
				else:
					meta=item.split("-")[2]
					if 'None' in self.previousFlavours:
						if not meta in self.metapackageRef:
							count=count+1
					else:		
						if not meta in self.previousFlavours:
							count=count+1

		if count>0:
			return True

		else:
			return False	

	#def checkIncorrectFlavours

	def distUpgradeProcess(self):
	
		return 'apt-get dist-upgrade --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages'

	#def distUpgradeProcess

	def checkErrorDistUpgrade(self):

		countPostaction=0
		countMetapackage=0
		error=False

		if os.path.exists(self.errorpostaction_token):
			aux = open(self.errorpostaction_token,'r')
			lines = aux.readlines()
			for x in lines:
				if 'E: ' in x:
					countPostaction=countPostaction+1
			aux.close()

		if countPostaction==0:

			if os.path.exists(self.errorfinalmetapackage_token):
				aux = open(self.errorfinalmetapackage_token,'r')
				lines = aux.readlines()
				for x in lines:
					if 'E: ' in x:
						countMetapackage=countMetapackage+1
				aux.close()
			if countMetapackage==0:
				
				cmd='dpkg -l | grep "^i[^i]" >' + self.errorupgrade_token
				os.system(cmd)
			
				if os.path.exists(self.errorupgrade_token):
					aux = open(self.errorupgrade_token,'r')
					lines = aux.readlines()
					aux.close()
				
					if len(lines)>0:
						error=True
						#log_msg="Dist-upgrade process ending with errors"
						#self.log(log_msg)
					else:
						j=0
						cmd='apt-get dist-upgrade -sV >' + self.finalupgrade_token
						os.system(cmd)
						if os.path.exists(self.finalupgrade_token):
							aux = open(self.finalupgrade_token,'r')
							lines = aux.readlines()
							aux.close()

							for x in lines:
								if 'Inst' in x:
									j=j+1

							if j>0:
								error=True	
			else:
				error=True					
		else:
			error=True

		return error	

	#def checkErrorDistUpgrade	

	'''	
	def checkFinalFlavour(self):
		
		flavourToInstall=None
		
		self.targetMetapackage=self.checkFlavour()
		if self.targetMetapackage!=None:
			#flavourToInstall=self.requiresInstallFlavour()
		#else:
			flavourToInstall=self.targetMetapackage 	

		return flavourToInstall	
	'''		


	def installFinalFlavour(self,flavourToInstall):

		return 'apt-get install ' + flavourToInstall + ' --yes  --allow-downgrades --allow-remove-essential --allow-change-held-packages'		
      	
	#def installFinalFlavour

	def get_process_list(self):
		
		self.process_list=[]
		
		p=subprocess.Popen(["ps","aux"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		output=p.communicate()[0]
		lst=output.split("\n")
		lst.pop(0)
		
		for item in lst:
			processed_line=item.split(" ")
			tmp_list=[]
			
			if len(processed_line) >= 10:
				for object in processed_line:
					if object!="":
						tmp_list.append(object)
				processed_line=tmp_list
				
				process={}
				process["user"]=processed_line[0]
				process["pid"]=processed_line[1]
				process["cpu"]=processed_line[2]
				process["mem"]=processed_line[3]
				process["vsz"]=processed_line[4]
				process["rss"]=processed_line[5]
				process["tty"]=processed_line[6]
				process["stat"]=processed_line[7]
				process["start"]=processed_line[8]
				process["time"]=processed_line[9]
				cmd=""
				for line in processed_line[10:]:
					if cmd!="":
						cmd+=" "
					cmd+=line
					
				process["command"]=cmd.split(" ")[0]
				self.process_list.append(process)

	#def get_process_list			

	def find_process(self,filter):
		
		self.get_process_list()
		ret_list=[]
		for process in self.process_list:
			if filter in process["command"]:
				ret_list.append(process)
				
				
		if len(ret_list)>0:
			return ret_list
		else:
			return None

	#def find_process		
				

#def LliurexUpCore
if __name__ == '__main__':
	x = LliurexUpCore()