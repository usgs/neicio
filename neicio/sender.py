#!/usr/bin/env python

#stdlib imports
import os.path
import tempfile

# TODO 
# - Add delete method
# - Add CopySender,SecureCopySender subclasses 
# - Write documentation, cleaner tests
# - Class factory function in this module somewhere?

class SenderError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Sender(object):
    '''Base class for concrete subclasses that wrap around different methods of transmitting files.
    '''
    def __init__(self,properties=None,filesToSend=None,directoryToSend=None):
        self.properties = properties
        if filesToSend is not None:
            if not isinstance(filesToSend,list):
                raise SenderError('Input filesToSend must be a list')
            for f in filesToSend:
                if not os.path.isfile(f):
                    raise SenderError('Input file %s could not be found' % f)
        if directoryToSend is not None:
            if not os.path.isdir(directoryToSend):
                raise SenderError('Input directory %s could not be found' % directoryToSend)
        self.filesToSend = filesToSend
        self.directoryToSend = directoryToSend

    def addProperty(self,key,value):
        self.properties[key] = value

    #this is implemented in the subclasses
    def send(self):
        pass

    #this is implemented in the subclasses
    def delete(self):
        pass

