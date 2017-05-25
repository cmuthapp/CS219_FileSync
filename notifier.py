import os.path
from subprocess import call

import pyinotify

##A folder for creating all the v0 versions
syncfolder = "/tmp/syncfolder"
if not os.path.exists(syncfolder):
	#print "not exits"
	os.mkdir(syncfolder)
#else:
	#print "exists"

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_OPEN | pyinotify.IN_CLOSE_WRITE #| pyinotify.IN_MODIFY #| pyinotify.IN_CLOSE_NOWRITE   # watched events

class EventHandler(pyinotify.ProcessEvent):
   # i = 0
    def process_IN_OPEN(self, event):
    	if (os.path.isfile(event.pathname)):
        	print "file opened: ", event.pathname
        	newfile = event.name+"-v" #+ str(self.i)
    #    	self.i = self.i +1
        	syncfolder = "/tmp/syncfolder/"
        	if not os.path.isfile(syncfolder+newfile):				##creates copy only if version file is not there
        		print "hi" 
        		call(["cp", event.pathname, syncfolder+newfile])
    #    	print"\n ",newfile

#    def process_IN_CLOSE_NOWRITE(self, event):
#        print "file closed without changes: ", event.pathname
#copyfile(src, dst)
    def process_IN_CLOSE_WRITE(self, event):
    	if (os.path.isfile(event.pathname)):
        	print "file closed with changes: ", event.pathname
        	
        	syncfolder = "/tmp/syncfolder/"
        	oldfile = event.name+"-v"
        	####compute delta
        	call(["rm" ,syncfolder+oldfile]) ## deleting previous version


#    def process_IN_MODIFY(self, event):
#        print "file modified: ", event.pathname

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)
notifier.coalesce_events()
wdd = wm.add_watch('/home/cmuthapp/cs219/test/', mask, rec=True)

notifier.loop()