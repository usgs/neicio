#!/usr/bin/python

import numpy
import re
import sys
import os.path
from grid import Grid,GridError
from numpy import array
from binfile import BinFile
from pylab import isnan

class EsriGridError(Exception):
    "used to indicate an error in EsriGrid"
    def __str__(self):
        return repr(self.args[0])

class EsriGrid(Grid):
    """
    Create Grid object from any kind of ESRI grid file - simple header, or header + world file.
    """
    LARGEST_DEG_RANGE = 15
    GRIDLINE = 0
    ZSCALE = 1
    ZOFFSET = 0
    NODATAVALUE = 0
    gridfilename = None

    def __init__(self,gridfilename):
        """
        Create Grid object from any kind of ESRI grid file - simple header, or header + world file.

        @param gridfilename: Valid path to base ESRI grid file (with extension).
        """
        self.geodict = {}
        self.griddata = []
        self.gridfilename = gridfilename

    def getHeader(self):
        """
        Return metadata from the various header and/or world files that may accompany the Grid file.

        @return: A dictionary containing the following fields:
          - ulxmap  The longitude of the center of the upper left hand corner pixel.
          - ulymap  The latitude of the center of the upper left hand corner pixel.
          - nrows   The number of rows of data.
          - ncols   The number of columns of data.
          - xdim    The longitude resolution of a pixel in decimal degrees.
          - ydim    The latitude resolution of a pixel in decimal degrees.
          - byteorder The byte-order of the data file ('l' for little-endian, or 'b' for big-endian).
          - precision The precision of the data - one of [numpy.int8,numpy.int16,numpy.int32,numpy.int64,numpy.float32]
          - nodata    The value (if any) that represents missing data.  Defaults to None.
          - layout    String containing 'bil', 'bsq', or 'bip'.  Defaults to 'bil' if not specified by header files.
          - skip      Bytes to skip when reading the file.
        """
        return self.__loadHeader(self.gridfilename)

    def load(self,bounds=None):
        """
        Load data from grid file using specified bounds.
        
        @param bounds: Optional tuple containing desired geographic boundaries of data to be read in
                       from input file.  (xmin,xmax,ymin,ymax)
        @raise EsriGridError: When corresponding .hdr file cannot be found.
        @raise EsriGridError: When unsupported integer type is encountered (must be 8,16,32,64 bits)
        @raise EsriGridError: When any of a list of required header fields is missing after processing
                              the header and/or world files.
        @raise EsriGridError: When geo-positional information cannot be found in header file AND no 
                              corresponding world file cannot be found.
        
        """
        
        hdrstruct = self.__loadHeader(self.gridfilename)
        
        self.__populateGeoDict(hdrstruct)

        LARGEST_DEG_RANGE = 15
        if hdrstruct['precision'] == numpy.int8:
            DATA_WIDTH = 1
        if hdrstruct['precision'] == numpy.int16:
            DATA_WIDTH = 2
        if hdrstruct['precision'] == numpy.int32:
            DATA_WIDTH = 4
        if hdrstruct['precision'] == numpy.float32:
            DATA_WIDTH = 4
        if hdrstruct['precision'] == numpy.int64:
            DATA_WIDTH = 8
        
        gdict = self.geodict
        
        #load the data
        if bounds:
            (bxmin,bxmax,bymin,bymax) = bounds
        else:
            (bxmin,bxmax,bymin,bymax) = (gdict['xmin'],gdict['xmax'],gdict['ymin'],gdict['ymax'])

        urx = gdict['xmax']
        ury = gdict['ymax']
        lrx = urx
        lry = gdict['ymin']
        ulx = gdict['xmin']
        uly = ury
        llx = ulx
        lly = lry

        ncols = gdict['ncols']
        nrows = gdict['nrows']
        xdim = gdict['xdim']
        ydim = gdict['ydim']

        if bymin < lly:
            bymin = lly

        if bymax > uly:
            bymax = uly
							
        if bymin >= bymax:
            raise GridError, "Latitude minimum (%f) is greater than latitude maximum (%f)" % (bymin,bymax)
        
        #check to see if the longitude bounds from shakemap went past -180
        xminLeftOfMeridian = False
        xmaxLeftOfMeridian = False
        if bxmin < -180:
            xminLeftOfMeridian = True
            bxmin = bxmin+360
            
        if bxmax < -180:
            xmaxLeftOfMeridian = True
            bxmax = bxmax+360

        
        #open the binary file for reading
        nrows = hdrstruct['nrows']
        ncols = hdrstruct['ncols']
        dtype = hdrstruct['precision']
        skip = hdrstruct['skip']
        popfile = BinFile(self.gridfilename,int(nrows),int(ncols),dtype,skip)
        
        #handle meridian crossing bounds
        if bxmin > bxmax:
            if bxmax - (bxmin-360) > self.LARGEST_DEG_RANGE:
                raise GridError, "Longitude range exceeds %f." % (self.LARGEST_DEG_RANGE)
            
            #cut user's request into two regions - one from the minimum to the
            #meridian, then another from the meridian to the maximum.
            (region1,region2) = self.__createSections((bxmin,bxmax,bymin,bymax))
            (iulx1,iuly1,ilrx1,ilry1) = region1
            (iulx2,iuly2,ilrx2,ilry2) = region2
            outcols1 = long(ilrx1-iulx1+1)
            outcols2 = long(ilrx2-iulx2+1)
            outcols = long(outcols1+outcols2)
            outrows = long(ilry1-iuly1+1)
            
            section1 = popfile[iuly1:ilry1+1,iulx1:ilrx1+1]
            section2 = popfile[iuly2:ilry2+1,iulx2:ilrx2+1]
            self.griddata = numpy.concatenate((section1,section2),axis=1)
            bxmin = (ulx + iulx1*xdim)
            bymax = uly - iuly1*ydim
            bxmax = ulx + ilrx2*xdim
            bymin = bymax - outrows*ydim
        else:
            #figure out the pixel space locations of the user's desired
            #ul and lr corners
            if bxmin < llx:
                bxmin = llx
                 
            if bxmax > llx+(ncols*xdim):
                bxmax = llx+(ncols*xdim)
                 
            if bymax > lly+(nrows*ydim):
                bymax = lly+(nrows*ydim)
                 
            if bymin < lly:
                bymin = lly
            
            iulx = numpy.ceil((bxmin - ulx)/xdim)
            iuly = numpy.ceil((uly - bymax)/ydim)
            ilrx = numpy.floor((bxmax - ulx)/xdim)
            ilry = numpy.floor((uly - bymin)/ydim)

            if ilry >= nrows-1:
                ilry = ilry - 1
            if ilrx >= ncols-1:
                ilrx = ilrx-1
                
            # print iulx,iuly,ilrx,ilry
            #             print nrows,ncols

            outcols = long(ilrx-iulx+1)
            outrows = long(ilry-iuly+1)
            
            self.griddata = popfile[iuly:ilry+1,iulx:ilrx+1]
            outrows,outcols = self.griddata.shape
            #calculate the actual new corner pixel positions
            bxmin = ulx + iulx*xdim
            bymax = uly - iuly*ydim
            bymin = bymax - (outrows-1)*ydim
            bxmax = bxmin + (outcols-1)*xdim

        #if the data read in has a different endian-ness, swap it...
        if hdrstruct['byteorder'] != self.__getLocalEndian():
            self.griddata.byteswap()
        
        if hdrstruct['nodata'] is not None:
            inan,jnan = (self.griddata == hdrstruct['nodata']).nonzero()
            self.griddata[inan,jnan] = numpy.NaN

        #repopulate the geodict with correct values
        self.geodict['ncols'] = outcols
        self.geodict['nrows'] = outrows
        if xminLeftOfMeridian:
            bxmin = bxmin - 360
        if xmaxLeftOfMeridian:
            bxmax = bxmax - 360
        self.geodict['xmin'] = bxmin
        self.geodict['xmax'] = bxmax
        self.geodict['ymin'] = bymin
        self.geodict['ymax'] = bymax
        self.geodict['xdim'] = xdim
        self.geodict['ydim'] = ydim
        self.geodict['bandnames'] = ['Population Count']
        

    def __createSections(self,bounds):
        (bxmin,bxmax,bymin,bymax) = bounds
        ulx = self.geodict['xmin']
        uly = self.geodict['ymax']
        xdim = self.geodict['xdim']
        ydim = self.geodict['ydim']
        ncols = self.geodict['ncols']
        nrows = self.geodict['nrows']
        #section 1
        iulx1 = int(numpy.floor((bxmin - ulx)/xdim))
        iuly1 = int(numpy.ceil((uly - bymax)/ydim))
        ilrx1 = int(ncols-1)
        ilry1 = int(numpy.floor((uly - bymin)/ydim))
        #section 2
        iulx2 = 0
        iuly2 = int(numpy.ceil((uly - bymax)/ydim))
        ilrx2 = int(numpy.ceil((bxmax - ulx)/xdim))
        ilry2 = int(numpy.floor((uly - bymin)/ydim))
        
        region1 = (iulx1,iuly1,ilrx1,ilry1)
        region2 = (iulx2,iuly2,ilrx2,ilry2)
        return(region1,region2)

    def __replaceNaN(self,array,nodata):
        i = numpy.where(array == nodata)
        if i:
            array[i] = numpy.NaN #change this to replace with actual NaN value...
        return array
    

    def __loadHeader(self,basefile):
        hdrstruct = {}
        (path,ext) = os.path.splitext(basefile)
        hdrfilename = path+'.hdr'
        if (not os.path.isfile(hdrfilename)):
            raise EsriGridError, 'Could not find header file '+hdrfilename
        hdrfile = open(hdrfilename)
        for line in hdrfile.readlines():
            (key,value) = line.split()
            key = key.lower()
            try:
                value = float(value)
            except:
                value = value.lower()
            hdrstruct[key] = value
        hdrfile.close()

        if 'byteorder' in hdrstruct.keys():
            if hdrstruct['byteorder'] == 'i' or hdrstruct['byteorder'] == 'lsbfirst':
                hdrstruct['byteorder'] = 'l'
            if hdrstruct['byteorder'] == 'm' or hdrstruct['byteorder'] == 'msbfirst':
                hdrstruct['byteorder'] = 'b'
        else:
            hdrstruct['byteorder'] = self.__getLocalEndian()
        
        #if we're given xllcorner or xllcenter
        if ('xllcorner' in hdrstruct.keys() or 'xllcenter' in hdrstruct.keys()) and \
                ('cellsize' in hdrstruct.keys()):
            if 'xllcorner' in hdrstruct.keys():
                hdrstruct['ulxmap'] = hdrstruct['xllcorner'] + hdrstruct['cellsize']/2
                hdrstruct['ulymap'] = (hdrstruct['yllcorner'] + hdrstruct['cellsize']/2) \
                    + ((hdrstruct['nrows']-1)*hdrstruct['cellsize'])
            else:
                hdrstruct['ulxmap'] = hdrstruct['xllcenter']
                hdrstruct['ulymap'] = hdrstruct['yllcenter'] + ((hdrstruct['nrows']-1)*hdrstruct['cellsize'])
            hdrstruct['xdim'] = hdrstruct['cellsize']
            hdrstruct['ydim'] = hdrstruct['cellsize']
        #sometimes the files don't contain georeferencing information.  In those
        #cases, look for a file with a suffix ending with 'w', and parse that as
        #an ESRI world file.  If that file can't be found, bail out with an error
        loc_fields = ['ulxmap','xllcorner','xllcenter']
        hasGeo = False
        for field in loc_fields:
            if field in hdrstruct.keys():
                hasGeo = True
                break
        if not hasGeo:
            worldinfo = self.__readWorldFile(basefile)
            hdrstruct['xdim'] = worldinfo[0]
            hdrstruct['ydim'] = abs(worldinfo[3])
            hdrstruct['ulxmap'] = worldinfo[4]
            hdrstruct['ulymap'] = worldinfo[5]
        
        #some header files have nodata values, the others don't
        if 'nodata_value' in hdrstruct.keys():
            hdrstruct['nodata'] = hdrstruct['nodata_value']
        elif 'nodata' in hdrstruct.keys():
            hdrstruct['nodata'] = hdrstruct['nodata']
        else:
            hdrstruct['nodata'] = None

        #one kind has "layout"
        if 'layout' not in hdrstruct.keys():
            hdrstruct['layout'] = 'bil'

        #one version has "nbits", indicating integer data type
        isInt = ('pixeltype' in hdrstruct.keys() and hdrstruct['pixeltype'].lower().find('int') > -1) or 'pixeltype' not in hdrstruct.keys()
        if 'nbits' in hdrstruct.keys() and isInt:
            if hdrstruct['nbits'] == 8: hdrstruct['precision'] = numpy.int8
            elif hdrstruct['nbits'] == 16: hdrstruct['precision'] = numpy.int16
            elif hdrstruct['nbits'] == 32: hdrstruct['precision'] = numpy.int32
            elif hdrstruct['nbits'] == 64: hdrstruct['precision'] = numpy.int64
            else:
                raise EsriGridError, 'Unsupported integer type with %i bits.' % (hdrstruct['nbits'])
        else:
            hdrstruct['precision'] = numpy.float32
        
        #check for bytes to skip at beginning of the file...
        if 'skip' not in hdrstruct.keys():
            hdrstruct['skip'] = 0
        
        required_fields = set(['ulxmap','ulymap','nrows','ncols',
                           'xdim','ydim','byteorder','precision',
                           'nodata','layout','skip'])
        if len(set(hdrstruct.keys()) & required_fields) != len(required_fields):
            missing = list(set(hdrstruct.keys()) - required_fields)
            print 'Our keys: '+str(hdrstruct.keys())
            print 'Required keys: '+str(required_fields)
            raise EsriGridError, 'Missing following required fields after parsing headers:%s' % (str(missing))
        
        extras = set(hdrstruct.keys()) - required_fields
        for ex in extras:
            del hdrstruct[ex]
        return hdrstruct
        
    def __readWorldFile(self,gridfilename):
        #try to find the world file...look for base(gridfilename).*w...
        popfile = os.path.basename(gridfilename)
        path = os.path.dirname(gridfilename)
        (popbase,popext) = os.path.splitext(popfile)
        allfiles = os.listdir(path)
        worldfile = ''
        for file in allfiles:
            (filebase,fileext) = os.path.splitext(file)
            if filebase == popbase and fileext.endswith('w'):
                worldfile = os.path.join(path,file)
                break
        
        if not worldfile:
            raise EsriGridError, 'Could not find world file for '+gridfilename

        #world file format:
        #row 0: xdim
        #row 1: xrot
        #row 2: yrot
        #row 3: -ydim
        #row 4: ulxmap
        #row 5: ulymap
        f = open(worldfile,'rt')
        worlddata = []
        for line in f.readlines():
            worlddata.append(float(line.strip()))
        f.close()
        return worlddata
        
    def __getLocalEndian(self):
        if ord(array([1],dtype=numpy.int16).tostring()[0]): #check this on a big-endian machine!
            endian = 'l' #little-endian
        else:
            endian = 'b' #big-endian
        return endian

    def __populateGeoDict(self,hdrstruct):
        self.geodict['xmin'] = hdrstruct['ulxmap']
        self.geodict['ymax'] = hdrstruct['ulymap']
        self.geodict['xdim'] = hdrstruct['xdim']
        self.geodict['ydim'] = hdrstruct['ydim']
        self.geodict['xmax'] = hdrstruct['ulxmap'] + (hdrstruct['ncols']-1)*hdrstruct['xdim']
        self.geodict['ymin'] = hdrstruct['ulymap'] - (hdrstruct['nrows']-1)*hdrstruct['ydim']
        self.geodict['ncols'] = hdrstruct['ncols']
        self.geodict['nrows'] = hdrstruct['nrows']
        self.geodict['nbands'] = 1 #ESRI formats do not support multi-band data (I think!)
        self.geodict['time'] = None
        self.geodict['bandnames'] = ['Unknown']
        return

        
