#!/usr/bin/env python

#stdlib imports
import os.path
import tempfile

#third party
from neicio.cmdoutput import getCommandOutput

#local
from sender import Sender,SenderError

# TODO 
# - Add delete method
# - Add CopySender,SecureCopySender subclasses 
# - Write documentation, cleaner tests

class PDLSender(Sender):
    required_properties = ['jarfile','source','type','keyfile','configfile','code']
    def send(self):
        #is it possible to send a directory and a file in the same command?
        #let's assume it isn't
        if self.filesToSend is not None and self.directoryToSend is not None:
            raise SenderError('For PDL, you must choose files OR a directory to send, not both')
        for prop in self.required_properties:
            if prop not in self.properties.keys():
                raise SenderError('"%s" property must be supplied to send via PDL')
        jarfile = self.properties['jarfile']
        source = self.properties['source']
        ptype = self.properties['type']
        keyfile = self.properties['keyfile']
        configfile = self.properties['configfile']
        code = self.properties['code']
        if not os.path.isfile(jarfile):
            raise SenderError('Could not find Java jar file "%s".' % jarfile)
        if not os.path.isfile(configfile):
            raise SenderError('Could not find PDL config file "%s".' % configfile)
        if not os.path.isfile(keyfile):
            raise SenderError('Could not find PDL private key file "%s".' % keyfile)
        #build pdl command line from properties
        javabin = self.findjava()
        if javabin is None:
            raise SenderError('Could not find Java binary on system path.')
        basecmd = '%s -jar %s --send --source=%s --type=%s --privateKey=%s --configFile=%s --code=%s ' % (javabin,jarfile,source,ptype,keyfile,configfile,code)
        nuggets = []
        for key,value in self.properties.iteritems():
            if key in self.required_properties:
                continue
            if isinstance(value,int):
                vstr = '%i' % value
            elif isinstance(value,float):
                vstr = '%f' % value
            else:
                vstr = value
            nuggets.append('--%s=%s' % (key,vstr))
        cmd = basecmd + ' '.join(nuggets) + ' '
        nfiles = 0
        #pdl can be used to send information without sending any files
        if self.directoryToSend is None and self.filesToSend is None:
            #this is ok - PDL products can be defined completely on the command line
            retcode,stdout,stderr = getCommandOutput(cmd)
            if not retcode:
                raise SenderError('Could not send directory "%s" due to error "%s"' % (self.directoryToSend,stdout+stderr))
        if self.directoryToSend is not None:
            cmd = cmd + '--directory=%s ' % self.directoryToSend
            retcode,stdout,stderr = getCommandOutput(cmd)
            if not retcode:
                raise SenderError('Could not send directory "%s" due to error "%s"' % (self.directoryToSend,stdout+stderr))
            nfiles += len(os.walk(self.directoryToSend).next()[2])
        elif self.filesToSend is not None:
            for f in self.filesToSend:
                cmd = cmd + '--file=%s ' % f
                retcode,stdout,stderr = getCommandOutput(cmd)
                if not retcode:
                    raise SenderError('PDL command: "%s"\nCould not send file "%s" due to error "%s"' % (cmd,f,stdout+stderr))
                nfiles += 1
        return nfiles
        
    def findjava(self):
        javabin = None
        for p in os.environ['PATH'].split(':'):
            jbin = os.path.join(p,'java')
            if os.path.isfile(jbin):
                javabin = jbin
                break
        return javabin

                              

