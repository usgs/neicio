#!/usr/bin/env python

#stdlib imports
from ftplib import FTP
import os.path

#local
from sender import Sender,SenderError

# TODO 
# - Add delete method
# - Add CopySender,SecureCopySender subclasses 
# - Write documentation, clean tests
    
class FTPSender(Sender):
    def send(self):
        if 'host' not in self.properties.keys():
            raise NameError('"host" keyword must be supplied to send via FTP')
        if 'directory' not in self.properties.keys():
            raise NameError('"directory" keyword must be supplied to send via FTP')
        host = self.properties['host']
        folder = self.properties['directory']
        try:
            dirparts = folder.strip().split('/')
            ftp = FTP(host)
            if self.properties.has_key('user'):
                user = self.properties['user']
            else:
                user = ''
            if self.properties.has_key('password'):
                password = self.properties['password']
            else:
                password = ''
            if user == '':
                ftp.login()
            else:
                ftp.login(user,password)
            for d in dirparts:
                if d == '':
                    continue
                try:
                    ftp.cwd(d)
                except ftplib.error_perm,msg:
                    raise SenderError('Could not login to host "%s" and navigate to directory "%s"' % (host,folder))
            #ftp.cwd(self.properties['directory'])
            nfiles = 0
            if self.filesToSend is not None:
                for f in self.filesToSend:
                    self.__sendfile(f,ftp)
                    nfiles += 1
            if self.directoryToSend is not None:
                for path, subdirs, files in os.walk(self.directoryToSend):
                    ftp.mkd(path)
                    for f in files:
                        self.__sendfile(f,ftp)
                        nfiles += 1
            ftp.quit()
            return nfiles
                    
        except Exception,obj:
            raise SenderError('Could not send to %s.  Error "%s"' % (host,str(obj)))

    def __sendfile(self,filename,ftp):
        fbase,fpath = os.path.split(filename)
        cmd = "STOR " + fpath #we don't tell the ftp server about the local path to the file
        ftp.storbinary(cmd,open(filename,"rb"),1024) #actually send the file
                              

