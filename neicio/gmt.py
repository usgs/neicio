#!/usr/bin/env python

#stdlib imports
import struct
import sys

#third party imports
import numpy
from scipy.io import netcdf
import matplotlib.pyplot as plt

#local imports
from grid import Grid

class GMTGrid(Grid):
    def __init__(self,grdfile=None,fmt='f',bandname=None,bounds=None):
        """
        Read binary "native" GMT grid files or COARDS-compliant netcdf GMT grid files.
        @keyword grdfile: Name of input grid file.
        @keyword fmt: Format type - only required for native files. Valid options are:
                      - 'i' (16 bit signed integer)
                      - 'l' (32 bit signed integer)
                      - 'f' (32 bit float)
                      - 'd' (64 bit float)
        @keyword bandname: Short name of data set ("elevation","mmi", etc.)
        @keyword bounds: Tuple containing (xmin,xmax,ymin,ymax).  Native files not supported yet.
        """
        self.geodict = {}
        self.griddata = None
        if grdfile is None:
            return

        #netcdf or native?
        ftype = self.getFileType(grdfile)
        self.ftype = ftype
        self.gridfile = grdfile
        if ftype == 'netcdf':
            self.load(bounds=bounds)
            return
        
        #we're dealing with a binary "native" GMT grid file
        f = open(grdfile,'rb')
        f.seek(0,0)
        self.geodict = {}
        self.geodict['ncols'] = struct.unpack('I',f.read(4))[0]
        self.geodict['nrows'] = struct.unpack('I',f.read(4))[0]
        offset = struct.unpack('I',f.read(4))[0]
        self.geodict['xmin'] = struct.unpack('d',f.read(8))[0]
        self.geodict['xmax'] = struct.unpack('d',f.read(8))[0]
        self.geodict['ymin'] = struct.unpack('d',f.read(8))[0]
        self.geodict['ymax'] = struct.unpack('d',f.read(8))[0]
        zmin = struct.unpack('d',f.read(8))[0]
        zmax = struct.unpack('d',f.read(8))[0]
        self.geodict['xdim'] = struct.unpack('d',f.read(8))[0]
        self.geodict['ydim'] = struct.unpack('d',f.read(8))[0]
        zscale = struct.unpack('d',f.read(8))[0]
        zoffset = struct.unpack('d',f.read(8))[0]
        xunits = f.read(80).strip()
        yunits = f.read(80).strip()
        zunits = f.read(80).strip()
        title = f.read(80).strip()
        command = f.read(320).strip()
        remark = f.read(160).strip()
        #nota bene - the extent specified in a GMT grid is for the edges of the
        #grid, regardless of whether you've specified grid or pixel
        #registration.
        self.geodict['xmin'] = self.geodict['xmin'] + self.geodict['xdim']/2.0
        self.geodict['xmax'] = self.geodict['xmax'] - self.geodict['xdim']/2.0
        self.geodict['ymin'] = self.geodict['ymin'] + self.geodict['ydim']/2.0
        self.geodict['ymax'] = self.geodict['ymax'] - self.geodict['ydim']/2.0
        if bandname is not None:
            self.geodict['bandnames'] = [bandname]
        else:
            self.geodict['bandnames'] = ['']
        
        sfmt = '%i%s' % (self.geodict['ncols']*self.geodict['nrows'],fmt)
        dwidths = {'i':2,'l':4,'f':4,'d':8}
        dwidth = dwidths[fmt]
        dbytes = f.read(self.geodict['ncols']*self.geodict['nrows']*dwidth)
        data = struct.unpack(sfmt,dbytes)
        self.griddata = numpy.array(data).reshape(self.geodict['nrows'],-1)
        self.griddata = (self.griddata * zscale) + zoffset
        f.close()     
        self.Attributes = {}

    def getAttributes(self):
        """
        Return the internal dictionary of attributes.  At the time of this writing, 
        this can be whatever dictionary the user wants.
        """
        return self.Attributes

    def getFileType(self,grdfile):
        #TODO:check the file size against the supposed format - won't be able to 
        #tell the difference between floats and 32 bit integers though.  should 
        #probably also put that in the function documentation.
        f = open(grdfile,'rb')
        f.seek(8,0)
        offset = struct.unpack('I',f.read(4))[0]
        if offset == 0 or offset == 1:
            ftype = 'binary'
        else:
            ftype = 'netcdf'
        return ftype
        
    def load(self,bounds=None):
        if self.ftype == 'netcdf':
            cdf = netcdf.netcdf_file(self.gridfile)
            xvarname = None
            if 'x' in cdf.variables.keys():
                xvarname = 'x'
                yvarname = 'y'
            else:
                xvarname = 'lon'
                yvarname = 'lat'
            if xvarname is not None: #at least two forms of COARDS-compliant netcdf files...
                xvar = cdf.variables[xvarname].data.copy()
                yvar = cdf.variables[yvarname].data.copy()

                #do some QA on the x and y data
                dx = numpy.diff(xvar)
                dy = numpy.diff(yvar)

                isXConsistent = numpy.abs(1 - numpy.max(dx)/numpy.min(dx)) < 0.01
                isYConsistent = numpy.abs(1 - numpy.max(dx)/numpy.min(dx)) < 0.01
                if not isXConsistent or not isYConsistent:
                    raise Exception,'X or Y cell dimensions are not consistent!'

                #assign x/y resolution
                self.geodict['xdim'] = numpy.mean(dx)
                self.geodict['ydim'] = numpy.mean(dy)

                if bounds is not None:
                    xmin,xmax,ymin,ymax = bounds
                    cdfarray = BinCDFArray(cdf,len(yvar.data),len(xvar.data))
                    if xmin > xmax:
                        #cut user's request into two regions - one from the minimum to the
                        #meridian, then another from the meridian to the maximum.
                        (region1,region2) = self.__createSections((xmin,xmax,ymin,ymax))

                        (iulx1,iuly1,ilrx1,ilry1) = region1
                        (iulx2,iuly2,ilrx2,ilry2) = region2
                        outcols1 = long(ilrx1-iulx1+1)
                        outcols2 = long(ilrx2-iulx2+1)
                        outcols = long(outcols1+outcols2)
                        outrows = long(ilry1-iuly1+1)

                        section1 = cdfarray[iuly1:ilry1+1,iulx1:ilrx1+1]
                        section2 = cdfarray[iuly2:ilry2+1,iulx2:ilrx2+1]
                        self.griddata = numpy.concatenate((section1,section2),axis=1)
                        xmin = (ulx + iulx1*xdim)
                        ymax = uly - iuly1*ydim
                        xmax = ulx + ilrx2*xdim
                        ymin = bymax - outrows*ydim
                        
                    else:
                        ixmin = numpy.abs(xvar-xmin).argmin()
                        ixmax = numpy.abs(xvar-xmax).argmin()
                        iymin = numpy.abs(yvar-ymin).argmin()
                        iymax = numpy.abs(yvar-ymax).argmin()
                    self.geodict['xmin'] = xvar[ixmin].copy()
                    self.geodict['xmax'] = xvar[ixmax].copy()
                    self.geodict['ymin'] = yvar[iymin].copy()
                    self.geodict['ymax'] = yvar[iymax].copy()
                    zvar = cdf.variables['z'][iymin:iymax,ixmin:ixmax]
                    zvar = zvar.copy()
                    self.griddata = numpy.flipud(zvar)
                    m,n = self.griddata.shape
                    self.geodict['nrows'] = m
                    self.geodict['ncols'] = n
                else:
                    self.geodict['nrows'] = cdf.dimensions[yvarname]
                    self.geodict['ncols'] = cdf.dimensions[xvarname]
                    self.geodict['xmin'] = xvar.min().copy()
                    self.geodict['xmax'] = xvar.max().copy()
                    self.geodict['ymin'] = yvar.min().copy()
                    self.geodict['ymax'] = yvar.max().copy()
                    zdata = cdf.variables['z'].data.copy()
                    self.griddata = numpy.flipud(zdata)
            else: #the other kind of COARDS netcdf
                dxmin = cdf.variables['x_range'].data[0]
                dxmax = cdf.variables['x_range'].data[1]
                dymin = cdf.variables['y_range'].data[0]
                dymax = cdf.variables['y_range'].data[1]
                ncols,nrows = cdf.variables['dimension'].data
                xdim,ydim = cdf.variables['spacing'].data
                self.geodict['xdim'] = xdim
                self.geodict['ydim'] = ydim
                if bounds is None:
                    self.geodict['xmin'] = dxmin
                    self.geodict['xmax'] = dxmax
                    self.geodict['ymin'] = dymin
                    self.geodict['ymax'] = dymax
                    self.geodict['nrows'] = nrows
                    self.geodict['ncols'] = ncols
                    self.griddata = numpy.reshape(numpy.flipud(cdf.variables['z'].data.copy()),(nrows,ncols))
                else:
                    xmin,xmax,ymin,ymax = bounds
                    xvar = numpy.arange(xmin,xmax+xdim,xdim)
                    yvar = numpy.arange(ymin,ymax+ydim,ydim)
                    ixmin = numpy.abs(xvar-xmin).argmin()
                    ixmax = numpy.abs(xvar-xmax).argmin()
                    iymin = numpy.abs(yvar-ymin).argmin()
                    iymax = numpy.abs(yvar-ymax).argmin()
                    self.geodict['xmin'] = xvar[ixmin]
                    self.geodict['xmax'] = xvar[ixmax]
                    self.geodict['ymin'] = yvar[iymin]
                    self.geodict['ymax'] = yvar[iymax]
                    #we're reading in the whole array here just to subset it - not very efficient use of memory
                    self.griddata = numpy.reshape(numpy.flipud(cdf.variables['z'].data.copy()),nrows,ncols)
                    self.griddata = self.griddata[iymin:iymax,ixmin:ixmax]
                    m,n = self.griddata.shape
                    self.geodict['nrows'] = m
                    self.geodict['ncols'] = n

            self.geodict['bandnames'] = ['Unknown']
            cdf.close()
        else:
            raise NotImplementedError,'Only COARDS-compliant netcdf files are supported at this time!'            
        return

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

    def setDimArray(self,nelements,dmin,dmax,ddim):
        data = numpy.arange(dmin,dmax+ddim,ddim)
        tmax = dmax+ddim
        nrounds = 0 # we can get stuck in an endless loop here...
        while len(data) != nelements and nrounds < 4:
            if len(data) > nelements:
                tmax -= ddim
            if len(data) < nelements:
                tmax += ddim
            data = numpy.arange(dmin,tmax,ddim)
            nrounds += 1
        if len(data) == nelements:
            return (data,ddim)
        ddim = (dmax-dmin)/nelements
        data = numpy.arange(dmin,dmax,ddim)
        if len(data) > nelements:
            data = data[0:-1]
        if len(data) < nelements:
            data = numpy.append(data,data[-1]+ddim)
        return (data,ddim)
            
    def save(self,filename,fmt='netcdf'):
        nrows,ncols = self.griddata.shape
        xmin = self.geodict['xmin'] - self.geodict['xdim']/2.0
        ymax = self.geodict['ymax'] + self.geodict['ydim']/2.0
        xmax = self.geodict['xmax'] + self.geodict['xdim']/2.0
        ymin = self.geodict['ymin'] - self.geodict['ydim']/2.0
        
        if fmt != 'binary':
            cdf = netcdf.netcdf_file(filename,'w')
            cdf.node_offset = 1
            cdf.Conventions = 'COARDS, CF-1.5'
            cdf.createDimension('x',self.geodict['ncols'])
            cdf.createDimension('y',self.geodict['nrows'])
            x = cdf.createVariable('x',numpy.dtype('double'),['x'])
            y = cdf.createVariable('y',numpy.dtype('double'),['y'])
            z = cdf.createVariable('z',self.griddata.dtype,['y','x'])
            x.actual_range = numpy.array([xmin,xmax])
            y.actual_range = numpy.array([ymin,ymax])
            zmin = numpy.nanmin(self.griddata)
            zmax = numpy.nanmax(self.griddata)
            z.actual_range = numpy.array([zmin,zmax])
            x.long_name = 'x'
            y.long_name = 'y'
            z.long_name = 'z'
            xdim = self.geodict['xdim']
            ydim = self.geodict['ydim']
            xdata,xdim = self.setDimArray(ncols,xmin,xmax,xdim)
            ydata,ydim = self.setDimArray(nrows,ymin,ymax,ydim)
            
            x[:] = xdata
            y[:] = ydata
            z[:] = numpy.flipud(self.griddata)
            cdf.flush()
            cdf.close()
            return
        if not len(self.geodict):
            raise Exception,'This grid contains no data!'
        zmin = numpy.nanmin(self.griddata)
        zmax = numpy.nanmax(self.griddata)
        f = open(filename,'wb')
        f.write(struct.pack('I',self.geodict['ncols']))
        f.write(struct.pack('I',self.geodict['nrows']))
        f.write(struct.pack('I',1)) #node offset
        f.write(struct.pack('d',xmin))
        f.write(struct.pack('d',xmax))
        f.write(struct.pack('d',ymin))
        f.write(struct.pack('d',ymax))
        f.write(struct.pack('d',zmin))
        f.write(struct.pack('d',zmax))
        f.write(struct.pack('d',self.geodict['xdim']))
        f.write(struct.pack('d',self.geodict['ydim']))
        f.write(struct.pack('d',1)) #z scale factor
        f.write(struct.pack('d',0)) #z offset
        hunits = 'Decimal degrees'
        vunits = 'Unknown'
        title = 'None'
        cmd = 'Generated by a custom Python class'
        remark = 'None'
        hpad = [0 for i in range(0,80-len(hunits))]
        vpad = [0 for i in range(0,80-len(vunits))]
        tpad = [0 for i in range(0,80-len(title))]
        cpad = [0 for i in range(0,320-len(cmd))]
        rpad = [0 for i in range(0,160-len(remark))]
        hfmt = '%ib' % (80-len(hunits))
        vfmt = '%ib' % (80-len(vunits))
        tfmt = '%ib' % (80-len(title))
        cfmt = '%ib' % (320-len(cmd))
        rfmt = '%ib' % (160-len(remark))
        f.write(hunits) #xunits
        f.write(struct.pack(hfmt,*hpad))
        f.write(hunits) #yunits
        f.write(struct.pack(hfmt,*hpad))
        f.write(vunits)
        f.write(struct.pack(vfmt,*vpad))
        f.write(title)
        f.write(struct.pack(tfmt,*tpad))
        f.write(cmd)
        f.write(struct.pack(cfmt,*cpad))
        f.write(remark)
        f.write(struct.pack(rfmt,*rpad))
        dwidths = {'i':2,'l':4,'f':4,'d':8}
        dwidth = dwidths[self.griddata.dtype.kind]
        nrows,ncols = self.griddata.shape
        sfmt = '%i%s' % (nrows*ncols,self.griddata.dtype.kind)
        f.write(struct.pack(sfmt,*self.griddata.transpose().flatten()))
        f.close()
        return

class BinCDFArray(object):
    def __init__(self,array,nrows,ncols):
        self.array = array
        self.nrows = nrows
        self.ncols = ncols

    def __getitem__(self,*args):
        """Allows slicing of CDF data array in the same way as a numpy array."""
        if len(args) == 1 and isinstance(args[0][0],int):
            #user has passed in a tuple of row,col - they only want one value
            row = args[0][0]
            col = args[0][1]
            nrows = self.nrows
            ncols = self.ncols
            if row < 0 or row > nrows-1:
                raise Exception,"Row index out of bounds"
            if col < 0 or col > ncols-1:
                raise Exception,"Row index out of bounds"
            idx = ncols * row + col
            offset = 0
            return self.array[idx]

        if len(args) == 1 and isinstance(args[0][0],slice): #they want a non-scalar subset of the data
            nrows = self.nrows
            ncols = self.ncols
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
                raise Exception,"Row index out of bounds"
            if rowend < 0 or rowend > nrows:
                raise Exception,"Row index out of bounds"
            if colstart < 0 or colstart > ncols-1:
                raise Exception,"Col index out of bounds"
            if colend < 0 or colend > ncols:
                raise Exception,"Col index out of bounds"

            colcount = (colend-colstart)
            rowcount = (rowend-rowstart)
            outrows = numpy.ceil(rowcount/rowstep)
            outcols = numpy.ceil(colcount/colstep)
            data = numpy.zeros([outrows,outcols],dtype=self.dtype)
            outrow = 0
            for row in range(int(rowstart),int(rowend),int(rowstep)):
                #just go to the beginning of the row, we're going to read in the whole line
                idx = ncols*row 
                offset = self.dwidth*idx #beginning of row
                line = self.array[idx:idx+ncols]
                data[outrow,:] = line[colstart:colend:colstep]
                outrow = outrow+1
        else:
            raise Exception, "Unsupported __getitem__ input %s" % (str(key))
        return(data)

def test():
    pass
    
    
if __name__ == '__main__':
    filename = sys.argv[1]
    subset = False
    bounds = None
    if len(sys.argv) > 2:
        subset = True
        xmin = float(sys.argv[2])
        xmax = float(sys.argv[3])
        ymin = float(sys.argv[4])
        ymax = float(sys.argv[5])
        bounds = (xmin,xmax,ymin,ymax)
    gmtgrid = GMTGrid(filename,bounds=bounds)
    plt.imshow(gmtgrid.griddata,vmin=0,vmax=800)
    plt.colorbar()
    plt.savefig('output.png')
                     
        
    
    
        
