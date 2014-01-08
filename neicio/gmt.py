#!/usr/bin/env python

#stdlib imports
import struct
import sys

#third party imports
import numpy
from scipy.io import netcdf

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
        
        if ftype == 'netcdf':
            self.load(grdfile,ftype,bounds=bounds)
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
        
    def load(self,grdfile,ftype,bounds=None):
        if ftype == 'netcdf':
            cdf = netcdf.netcdf_file(grdfile)
            xvar = cdf.variables['x'].data
            yvar = cdf.variables['y'].data

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
                ixmin = numpy.abs(xvar-xmin).argmin()
                ixmax = numpy.abs(xvar-xmax).argmin()
                iymin = numpy.abs(yvar-ymin).argmin()
                iymax = numpy.abs(yvar-ymax).argmin()
                self.geodict['xmin'] = xvar[ixmin]
                self.geodict['xmax'] = xvar[ixmax]
                self.geodict['ymin'] = yvar[iymin]
                self.geodict['ymax'] = yvar[iymax]
                zvar = cdf.variables['z'].data
                self.griddata = numpy.flipud(zvar[iymin:iymax,ixmin:ixmax])
                m,n = self.griddata.shape
                self.geodict['nrows'] = m
                self.geodict['ncols'] = n
            else:
                self.geodict['nrows'] = cdf.dimensions['y']
                self.geodict['ncols'] = cdf.dimensions['x']
                self.geodict['xmin'] = cdf.variables['x'].data.min()
                self.geodict['xmax'] = cdf.variables['x'].data.max()
                self.geodict['ymin'] = cdf.variables['y'].data.min()
                self.geodict['ymax'] = cdf.variables['y'].data.max()
                zdata = cdf.variables['z'].data
                self.griddata = numpy.flipud(numpy.copy(zdata))

            self.geodict['bandnames'] = ['Unknown']
            cdf.close()
        else:
            raise NotImplementedError,'Only COARDS-compliant netcdf files are supported at this time!'            
        return
        

    def save(self,filename,fmt='netcdf'):
        nrows,ncols = self.griddata.shape
        xmin = self.geodict['xmin'] - self.geodict['xdim']/2.0
        ymax = self.geodict['ymax'] + self.geodict['ydim']/2.0
        xmax = self.geodict['xmax'] + self.geodict['xdim']/2.0
        ymin = self.geodict['ymin'] - self.geodict['ydim']/2.0
        
        if fmt != 'binary':
            cdf = netcdf.netcdf_file(filename,'w')
            cdf.createDimension('x',self.geodict['ncols'])
            cdf.createDimension('y',self.geodict['nrows'])
            x = cdf.createVariable('x',numpy.dtype('double'),['x'])
            y = cdf.createVariable('y',numpy.dtype('double'),['y'])
            z = cdf.createVariable('z',self.griddata.dtype,['y','x'])
            xdim = self.geodict['xdim']
            ydim = self.geodict['ydim']
            xdata = numpy.arange(xmin,xmax+xdim,xdim)
            ydata = numpy.arange(ymin,ymax+ydim,ydim)
            txmax = xmax+xdim
            tymax = ymax+ydim
            while len(xdata) != ncols:
                if len(xdata) > ncols:
                    txmax -= xdim
                if len(xdata) < ncols:
                    txmax += xdim
                xdata = numpy.arange(xmin,txmax,xdim)
            while len(ydata) != nrows:
                if len(ydata) > nrows:
                    tymax -= ydim
                if len(ydata) < nrows:
                    tymax += ydim
                ydata = numpy.arange(ymin,tymax,ydim)
            
            x[:] = xdata
            y[:] = ydata
            z[:] = self.griddata
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
        
if __name__ == '__main__':
    pass
    
        
