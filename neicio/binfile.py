#!/usr/bin/python

#stdlib
import os.path
import sys

#third party
import numpy

class BinFileError(Exception):
    "used to indicate an error in BinFile"
    def __str__(self):
        return repr(self.args[0])


class BinFile:
    """
    Read-only representation of any rectangular binary grid file.  [] indexing into file in the same way
    as a numpy array.
    """
    skip = 0
    fobj = None
    dwidth = 0
    dtype = None
    mode = None
    Modes = {'readonly':'rb','readwrite':'r+b'}
    def __init__(self,filename,nrows,ncols,dtype,skip=0,mode='readonly'):
        """
        Instantiate a BinFile object given a filename and information about the file.
        
        @param filename: String filename of rectangular grid binary file to be read.
        @param nrows: Number of rows of data in rectangular grid file.
        @param ncols: Number of columns of data in rectangular grid file.
        @param dtype: Data type of binary file, one of :
          - numpy.uint8
          - numpy.int8
          - numpy.uint16
          - numpy.int16
          - numpy.int32
          - numpy.uint32
          - numpy.float32
          - numpy.float64
        @keyword skip: Number of header bytes to skip.
        @keyword mode: Mode to use to open the file.  Defaults to read-only.  Use "r+b" for read/write
        @raise BinFileError: If filename is not found.
        """
        if not os.path.isfile(filename):
            raise BinFileError, "File %s could not be found" % (filename)
        self.mode = mode
        if mode not in self.Modes.keys():
            raise BinFileError, "mode keyword must be one of %s" % (str(self.Modes.keys()))
        fmode = self.Modes[mode]
        self.fobj = open(filename,fmode) #this gets closed in the destructor...
        if dtype == numpy.uint8 or dtype == numpy.int8:
            self.dwidth = 1
        if dtype == numpy.uint16 or dtype == numpy.int16:
            self.dwidth = 2
        if dtype == numpy.uint32 or dtype == numpy.int32 or dtype == numpy.float32:
            self.dwidth = 4
        if dtype == numpy.float64:
            self.dwidth = 8
        self.skip = skip
        self.dtype = dtype
        self.shape = (nrows,ncols)

    def __del__(self):
        """Destructor - closes binary file."""
        self.fobj.close()

    def __setitem__(self,*args):
        """Allows modification of grid file in the same way as a numpy array.
        
        Usage: 
        bin = BinFile('binfile.flt',4,4,numpy.float32)
        #set the upper left element
        bin[0,0] = 4.1
        #set the lower right hand element
        bin[3,3] = 3.7
        #set one of the center elements
        bin[2,2] = 2.1
        #set the 4 elements in the upper left hand corner
        bin[0:2,0:2] = numpy.random.rand(2,2)
        #set a slice of every other element in rows and columns
        bin[0:4:2,0:4:2] = ??
        """
        if self.mode == 'readonly':
            raise BinFileError,"Asking to write to a file opened as read-only"
        if len(args) == 2 and isinstance(args[0][0],int):
            #user has passed in a tuple of row,col and a scalar value (or numpy array)
            row = args[0][0]
            col = args[0][1]
            nrows = self.shape[0]
            ncols = self.shape[1]
            if row < 0 or row > nrows-1:
                raise BinFileError,"Row index out of bounds"
            if col < 0 or col > ncols-1:
                raise BinFileError,"Row index out of bounds"
            data = args[1]
            if isinstance(data,float):
                data = numpy.array(data,dtype=self.dtype)
            elif isinstance(data,numpy.ndarray):
                if len(data.shape) > 0:
                    raise BinFileError,"Data to insert must be a scalar"
                if not data.dtype == self.dtype:
                    raise BinFileError,"Input data type %s does not match file data type %s" % (data.dtype,self.dtype)
            else:
                raise BinFileError,"Data to insert must be a scalar Python float or ndarray scalar"
            idx = ncols * row + col
            offset = self.skip + self.dwidth*idx
            self.fobj.seek(offset,0)
            data.tofile(self.fobj)
        else:
            raise BinFileError,"Only scalar inserts are supported"
        
    def __getitem__(self,*args):
        """Allows slicing of grid file in the same way as a numpy array.
        
        Usage: 
        bin = BinFile('binfile.flt',4,4,numpy.float32)
        #get the upper left element
        bin[0,0]
        #get the lower right hand element
        bin[3,3]
        #get one of the center elements
        bin[2,2]
        #get the 4 elements in the upper left hand corner
        bin[0:2,0:2]
        #get a slice of every other element in rows and columns
        bin[0:4:2,0:4:2]
        """
        if len(args) == 1 and isinstance(args[0][0],int):
            #user has passed in a tuple of row,col
            row = args[0][0]
            col = args[0][1]
            nrows = self.shape[0]
            ncols = self.shape[1]
            if row < 0 or row > nrows-1:
                raise BinFileError,"Row index out of bounds"
            if col < 0 or col > ncols-1:
                raise BinFileError,"Row index out of bounds"
            idx = ncols * row + col
            offset = self.skip + self.dwidth*idx
            self.fobj.seek(offset,0)
            return(numpy.fromfile(self.fobj,dtype=self.dtype,count=1))
        if len(args) == 1 and isinstance(args[0][0],slice):
            nrows = self.shape[0]
            ncols = self.shape[1]
            #calculate offset to first data element
            key1 = args[0][0]
            key2 = args[0][1]
            rowstart = key1.start
            rowend = key1.stop
            rowstep = key1.step
            colstart = key2.start
            colend = key2.stop
            colstep = key2.step
            
            if rowstep is None:
                rowstep = 1
            if colstep is None:
                colstep = 1

            #error checking
            if rowstart < 0 or rowstart > nrows-1:
                raise BinFileError,"Row index out of bounds"
            if rowend < 0 or rowend > nrows:
                raise BinFileError,"Row index out of bounds"
            if colstart < 0 or colstart > ncols-1:
                raise BinFileError,"Col index out of bounds"
            if colend < 0 or colend > ncols:
                raise BinFileError,"Col index out of bounds"

            self.fobj.seek(self.skip,0)
            colcount = (colend-colstart)
            rowcount = (rowend-rowstart)
            outrows = numpy.ceil(rowcount/rowstep)
            outcols = numpy.ceil(colcount/colstep)
            data = numpy.zeros([outrows,outcols])
            outrow = 0
            for row in range(int(rowstart),int(rowend),int(rowstep)):
                #just go to the beginning of the row, we're going to read in the whole line
                idx = ncols*row 
                offset = self.dwidth*idx #beginning of row
                self.fobj.seek(offset,0)
                line = numpy.fromfile(self.fobj,dtype=self.dtype,count=ncols)
                data[outrow,:] = line[colstart:colend:colstep]
                outrow = outrow+1
        else:
            raise BinFileError, "Unsupported __getitem__ input %s" % (str(key))
        return(data)

if __name__ == '__main__':
    dfile = sys.argv[1]
    nrows = int(sys.argv[2])
    ncols = int(sys.argv[3])
    dtype = numpy.dtype(sys.argv[4])
    bfile = BinFile(dfile,nrows,ncols,dtype)
    data = bfile[0,0]
    print 'The first value in the file is %f' % data
    try:
        #this should raise an exception
        bfile[0,0] = 4.1
    except Exception,msg:
        print 'Error: %s' % msg
    del bfile
    bfile = BinFile(dfile,nrows,ncols,dtype,mode='readwrite')
    data = bfile[0,0]
    print 'The first value in the file is %f' % data
    #this should NOT raise an exception
    bfile[0,0] = 4.1
    print 'The first value in the file is %f' % bfile[0,0]
    del bfile
        
            
