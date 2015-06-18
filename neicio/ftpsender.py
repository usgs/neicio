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
    def setup(self):
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
        except Exception,obj:
            raise SenderError('Could not send to %s.  Error "%s"' % (host,str(obj)))
        return ftp

    def delete(self):
        ftp = self.setup()
        nfiles = 0
        host = self.properties['host']
        folder = self.properties['directory']
        if self.filesToSend is not None:
            for f in self.filesToSend:
                fbase,fpath = os.path.split(f)
                ftp.delete(fpath)
                nfiles += 1
        if self.directoryToSend is not None:
            root,thisfolder = os.path.split(self.directoryToSend) #root is the top level local directory
            for path, subdirs, files in os.walk(self.directoryToSend):
                mpath = path.replace(root,'').lstrip(os.sep) #mpath is the relative path on the ftp server
                allfiles = ftp.nlst()
                if mpath not in allfiles:
                    print 'Could not find directory %s on ftp server.' % mpath
                    continue
                ftpfolder = os.path.join(folder,mpath) #full path to the folder on ftp server
                ftp.cwd(ftpfolder)
                for f in files:
                    #f is the file name within the current folder
                    ftp.delete(f)
                    nfiles += 1
                ftp.cwd(folder) #go back to the root 
                ftp.rmd(ftpfolder)
        ftp.quit()
        return nfiles
    
    def send(self):
        if 'host' not in self.properties.keys():
            raise NameError('"host" keyword must be supplied to send via FTP')
        if 'directory' not in self.properties.keys():
            raise NameError('"directory" keyword must be supplied to send via FTP')
        try:
            host = self.properties['host']
            folder = self.properties['directory']
            ftp = self.setup()
            #ftp.cwd(self.properties['directory'])
            nfiles = 0
            if self.filesToSend is not None:
                for f in self.filesToSend:
                    self.__sendfile(f,ftp)
                    nfiles += 1
            if self.directoryToSend is not None:
                root,thisfolder = os.path.split(self.directoryToSend) #root is the top level local directory
                for path, subdirs, files in os.walk(self.directoryToSend):
                    mpath = path.replace(root,'').lstrip(os.sep) #mpath is the relative path on the ftp server
                    allfiles = ftp.nlst()
                    if mpath not in allfiles:
                        ftp.mkd(mpath)
                    ftpfolder = os.path.join(folder,mpath) #full path to the folder on ftp server
                    ftp.cwd(ftpfolder)
                    for f in files:
                        #f is the file name within the current folder
                        fpath = os.path.join(path,f) #the full path to the local file
                        self.__sendfile(fpath,ftp)
                        nfiles += 1
                    ftp.cwd(folder) #go back to the root 
            ftp.quit()
            return nfiles
                    
        except Exception,obj:
            raise SenderError('Could not send to %s.  Error "%s"' % (host,str(obj)))

    def __sendfile(self,filename,ftp):
        fbase,fpath = os.path.split(filename)
        cmd = "STOR " + fpath #we don't tell the ftp server about the local path to the file
        ftp.storbinary(cmd,open(filename,"rb"),1024) #actually send the file
                              

