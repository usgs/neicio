#!/usr/bin/env python

#stdlib
import sys

#third party
import numpy as np
from scipy import interpolate

class GridError(Exception):
    "used to indicate an error in Grid"
    def __str__(self):
        return repr(self.args[0])

class Grid:
    """
    Abstract Grid object.  This should be extended by other subclasses that handle loading and/or saving of 
    grid data in particular file formats.
    """
    griddata = None
    """
    @ivar: The numpy 2 or 3D array which contains the Grid data. 
    """
    geodict = {}
    """
    @ivar: Geo-referencing data takes the form of a dictionary, with the following keys:
          - nrows - Number of rows of internal numpy array.
          - ncols - Number of columns of internal numpy array.
          - nbands - Number of 'bands' (z dimension) of internal numpy array.
          - bandnames - list of band names.
          - xmin - Longitude of center of upper left hand corner pixel.
          - xmax - Longitude of center of upper right hand corner pixel.
          - ymin - Latitude of center of upper left hand corner pixel.
          - ymax - Latitude of center of upper right hand corner pixel.
          - xdim - Resolution of a grid cell in the X direction (in decimal degrees).
          - ydim - Resolution of a grid cell in the Y direction (in decimal degrees).
          - time - Python datetime of the creation date of the data.
    """
    
    #all Grids are pixel registered - that is, the lat/lon specified is for the center of the cell,
    #not the upper left hand corner (for example).
        
    def __init__(self):
        """Does nothing (implemented by subclasses)"""
        pass

    def load(self,filename):
        """Does nothing (can be implemented by subclasses.)"""
        pass

    def save(self,filename):
        """Does nothing (can be implemented by subclasses.)"""
        pass

    def loadFromGrid(self,grid):
        """
        Instantiate a grid from another grid.
        @param grid: Any subclass of the Grid object.
        """
        self.geodict = grid.geodict.copy()
        self.griddata = grid.griddata.copy()

    def binToGrid(self,geodict):
        """
        Given a geodict specifying another (coarser) grid extent and resolution, DOWNSAMPLE current grid to match.
        
        @param geodict: geodict dictionary from another grid whose extents are inside the extent of this grid.
        @raise GridError: If the Grid object upon which this function is being called is not completely 
                          contained by the grid to which this Grid is being resampled.
        @raise GridError: If the resulting interpolated grid shape does not match input geodict.

        This function modifies the internal griddata and geodict object variables.
        """
        xi,yi = self._getInterpCoords(geodict)
        nrows = len(yi)
        ncols = len(xi)
        #what are the width and height of the destination cells in source cell coordinates
        #for example, if source cell width is 1.5 meters, and destination cell width is 
        #4.5 meters, then 1 destination cell = 3 source cells
        coarsex = geodict['xdim']/self.geodict['xdim']
        coarsey = geodict['ydim']/self.geodict['ydim']
        newgriddata = np.zeros((nrows,ncols))
        for i in range(0,nrows):
            top = int(np.ceil(yi[i]-coarsey/2.0))
            bottom = int(np.floor(yi[i]+coarsey/2.0))
            #assign y weights to each row we are sampling
            ny = (bottom-top)+1
            yw = np.ones(ny)
            #figure out the weight of the topmost base cell
            coarsetop = yi[i] - coarsey/2.0
            basetop = top - 0.5
            coarsebottom = yi[i] + coarsey/2.0
            basebottom = top + 0.5
            if coarsebottom > basebottom:
                yw[0] = (basebottom-coarsetop)/(basebottom-basetop)
            else:
                yw[0] = (coarsebottom-coarsetop)/(basebottom-basetop)
            #figure out the weight of the bottommost base cell
            basetop = bottom - 0.5
            basebottom = bottom + 0.5
            if basetop > coarsetop:
                yw[-1] = (coarsebottom-basetop)/(basebottom-basetop)
            else:
                yw[-1] = (coarsebottom-coarsetop)/(basebottom-basetop)
            
            for j in range(0,ncols):
                left = int(np.ceil(xi[j]-coarsex/2.0))
                right = int(np.floor(xi[j]+coarsex/2.0))
                nx = (right-left)+1
                zcell = self.griddata[top:bottom+1,left:right+1] #data we'll be sampling from
                #assign weights to each base grid cell from which we are sampling
                xw = np.ones(nx) #array of x weights
                #figure out the weight of the leftmost base cell
                coarseleft = xi[j] - coarsex/2.0
                baseleft = left - 0.5
                coarseright = xi[j] + coarsex/2.0
                baseright = left + 0.5
                if coarseright > baseright:
                    xw[0] = (baseright-coarseleft)/(baseright-baseleft)
                else:
                    xw[0] = (coarseright-coarseleft)/(baseright-baseleft)
                #figure out the weight of the rightmost base cell
                baseleft = right - 0.5
                baseright = right + 0.5
                if baseleft > coarseleft:
                    xw[-1] = (coarseright-baseleft)/(baseright-baseleft)
                else:
                    xw[-1] = (coarseright-coarseleft)/(baseright-baseleft)
                xweights = np.tile(xw,(ny,1))
                yweights = np.tile(yw.reshape(ny,1),(1,nx))
                weights = xweights*yweights
                newgriddata[i,j] = np.nanmean(zcell*weights)
            
        self.griddata = newgriddata.copy()
        self.geodict = geodict.copy()
                

    def _getInterpCoords(self,geodict):
        #get the cell coordinates of the grid we want to interpolate to
        dims = self.griddata.shape
        nrows1 = dims[0]
        ncols1 = dims[1]
        ulx1 = self.geodict['xmin']
        uly1 = self.geodict['ymax']
        xdim1 = self.geodict['xdim']
        ydim1 = self.geodict['ydim']
        
        #extract the geographic information about the grid we're sampling to
        nrows = geodict['nrows']
        ncols = geodict['ncols']
        ulx = geodict['xmin']
        uly = geodict['ymax']
        xdim = geodict['xdim']
        ydim = geodict['ydim']

        #make sure that base grid is completely contained within the grid to be
        #resampled
        lry = geodict['ymin']
        lrx = geodict['xmax']
        lry1 = self.geodict['ymin']
        lrx1 = self.geodict['xmax']

        if (lry < lry1 or lrx > lrx1):
            raise GridError, 'Error:  Base grid is not completely contained by resampling grid.'
        
        #establish the geographic coordinates of the centers of our pixels...
        #all geostruct grids are what GMT calls "pixel-registered", that is
        #the upper left hand corner position is the geographic position of the 
        #center of the cell, not the upper-left corner of it.
        starty = lry
        endx = lrx
        endy = uly
        startx = ulx

        #we need to handle the meridian crossing here...
        if startx > endx:
            endx += 360
            ulx1 += 360

        gxi = np.arange(startx,endx,xdim,dtype=np.float64)
        gyi = np.arange(endy,starty,-ydim,dtype=np.float64)
        
        #we may wind up with an array that is one shorter than we need...
        #in this case, append the last value.
        if len(gxi) < ncols:
            gxi = np.concatenate((gxi,[endx]))
        if len(gxi) > ncols:
            gxi = gxi[0:-1]
        if len(gyi) < nrows:
            gyi = np.concatenate((gyi,[starty]))
        if len(gyi) > nrows:
            gyi = gyi[0:-1]

        xi = (gxi - ulx1)/xdim1
        yi = (uly1 - gyi)/ydim1

        return (xi,yi)
        
    def interpolateToGrid(self,geodict,method='linear'): #implement here
        """
        Given a geodict specifying another grid extent and resolution, resample current grid to match.
        
        @param geodict: geodict dictionary from another grid whose extents are inside the extent of this grid.
        @keyword method: Optional interpolation method - ['linear', 'cubic','quintic','nearest']
        @raise GridError: If the Grid object upon which this function is being called is not completely 
                          contained by the grid to which this Grid is being resampled.
        @raise GridError: If the resulting interpolated grid shape does not match input geodict.

        This function modifies the internal griddata and geodict object variables.
        """
        xi,yi = self._getInterpCoords(geodict)

        #now using scipy interpolate functions
        baserows,basecols = self.geodict['nrows'],self.geodict['ncols']
        basex = np.arange(0,basecols) #base grid PIXEL coordinates
        basey = np.arange(0,baserows)
        if method in ['linear','cubic','quintic']:
            f = interpolate.interp2d(basex,basey,self.griddata)
            self.griddata = f(xi,yi)
        else:
            x,y = np.meshgrid(basex,basey)
            f = interpolate.NearestNDInterpolator(zip(x.flatten(),y.flatten()),self.griddata.flatten())
            newrows = geodict['nrows']
            newcols = geodict['ncols']
            xi = np.tile(xi,(newrows,1))
            yi = np.tile(yi.reshape(newrows,1),(1,newcols))
            self.griddata = f(zip(xi.flatten(),yi.flatten()))
            self.griddata = self.griddata.reshape(xi.shape)
                                                  
            
        nrows,ncols = geodict['nrows'],geodict['ncols']
        dims = self.griddata.shape
        nrows_new = dims[0]
        ncols_new = dims[1]
        if nrows_new != nrows or ncols_new != ncols:
            msg = "Interpolation failed!  Results (%i,%i) don't match (%i,%i)!" % (nrows_new,ncols_new,nrows,ncols)
            raise GridError, msg
        #now the extents and resolution of the two grids should be identical...
        self.geodict['nrows'] = geodict['nrows']
        self.geodict['ncols'] = geodict['ncols']
        self.geodict['xmin'] = geodict['xmin']
        self.geodict['xmax'] = geodict['xmax']
        self.geodict['ymin'] = geodict['ymin']
        self.geodict['ymax'] = geodict['ymax']
        self.geodict['xdim'] = geodict['xdim']
        self.geodict['ydim'] = geodict['ydim']
        return

    def getData(self):
        """
        Return internal numpy data array.
        @return: Return 2 or 3D internal numpy data array.
        """
        return self.griddata

    def getRange(self):
        """Return a tuple (xmin,xmax,ymin,ymax) containing the extent of the data in this grid.
        @return: Tuple (xmin,xmax,ymin,ymax) containing the extent of the data in this grid.
        """
        (nrows,ncols) = (self.geodict['nrows'],self.geodict['ncols'])
        xmin = self.geodict['xmin']
        xmax = self.geodict['xmax']
        ymax = self.geodict['ymax']
        ymin = self.geodict['ymin']
        return (xmin,xmax,ymin,ymax)

    def getGeoDict(self):
        """
        Return grid geo-referencing data (instance geodict object).
        
        @return: Geo-referencing data takes the form of a dictionary, with the following keys:
          - nrows - Number of rows of internal numpy array.
          - ncols - Number of columns of internal numpy array.
          - nbands - Number of 'bands' (z dimension) of internal numpy array.
          - bandnames - list of band names.
          - xmin - Longitude of center of upper left hand corner pixel.
          - xmax - Longitude of center of upper right hand corner pixel.
          - ymin - Latitude of center of upper left hand corner pixel.
          - ymax - Latitude of center of upper right hand corner pixel.
          - xdim - Resolution of a grid cell in the X direction (in decimal degrees).
          - ydim - Resolution of a grid cell in the Y direction (in decimal degrees).
          - time - Python datetime of the creation date of the data.
        """
        return self.geodict

    def getLatLon(self,row,col):
        """Return geographic coordinates (lat/lon decimal degrees) for given data row and column.
        @param row: Row dimension index into internal data array.
        @param col: Column dimension index into internal data array.
        @return: Tuple of latitude and longitude.
        """
        ulx = self.geodict['xmin']
        uly = self.geodict['ymax']
        xdim = self.geodict['xdim']
        ydim = self.geodict['ydim']
        lon = ulx + col*xdim
        lat = uly - row*ydim
        return (lat,lon)

    def getRowCol(self,lat,lon):
        """Return data row and column from given geographic coordinates (lat/lon decimal degrees).
        @param lat: Input latitude.
        @param lon: Input longitude.
        @return: Tuple of row and column.
        """
        ulx = self.geodict['xmin']
        uly = self.geodict['ymax']
        xdim = self.geodict['xdim']
        ydim = self.geodict['ydim']
        col = np.floor((lon-ulx)/xdim)
        row = np.floor((uly-lat)/ydim)
        return (row,col)

    def getValue(self,lat,lon): #return nearest neighbor value
        """Return numpy array at given latitude and longitude (using nearest neighbor).
        @param lat: Latitude (in decimal degrees) of desired data value.
        @param lon: Longitude (in decimal degrees) of desired data value.
        @return: Value at input latitude,longitude position.
        """
        ulx = self.geodict['xmin']
        uly = self.geodict['ymax']
        xdim = self.geodict['xdim']
        ydim = self.geodict['ydim']
        dims = self.griddata.shape
        nrows = dims[0]
        ncols = dims[1]
        #check to see if we're in a scenario where the grid crosses the meridian
        if self.geodict['xmax'] < ulx and lon < ulx:
            lon += 360

        col = np.round(((lon - ulx)/xdim)).astype(int)
        row = np.round(((uly - lat)/ydim)).astype(int)
        if (row < 0).any() or (row > nrows-1).any() or (col < 0).any() or (col > ncols-1).any():
            msg = 'One of more of your lat/lon values is outside Grid boundaries: %s' % (str(self.getRange()))
            raise GridError, msg
        if len(dims) == 3:
            return self.griddata[row,col,:]
        else:
            return self.griddata[row,col]

def testBin():
    grid = Grid()
    grid.griddata = np.arange(1,31).reshape(5,6)
    grid.geodict = {'xmin':0.5,
                    'xmax':5.5,
                    'ymin':0.5,
                    'ymax':4.5,
                    'xdim':1.0,
                    'ydim':1.0,
                    'nrows':5,
                    'ncols':6}
    otherdict = {'xmin':1.75,
                 'xmax':4.75,
                 'ymin':0.75,
                 'ymax':3.75,
                 'xdim':1.5,
                 'ydim':1.5,
                 'nrows':3,
                 'ncols':3}
    grid.binToGrid(otherdict)
    answer = np.array([[  3.5625,   4.3125,   5.25  ],
                       [  9.1875,   9.9375,  10.875 ],
                       [ 13.6875,  14.4375,  15.375 ]])
    assert(np.equal(grid.griddata,answer).all())

def testInterp():
    grid = Grid()
    initialdata = np.arange(1,17).reshape(4,4)
    initialdict = {'xmin':0.5,
                   'xmax':3.5,
                   'ymin':0.5,
                   'ymax':3.5,
                   'xdim':1.0,
                   'ydim':1.0,
                   'nrows':4,
                   'ncols':4}
    grid.griddata = initialdata.copy()
    grid.geodict = initialdict.copy()
    otherdict = {'xmin':1.0,
                 'xmax':3.0,
                 'ymin':1.0,
                 'ymax':3.0,
                 'xdim':1.0,
                 'ydim':1.0,
                 'nrows':3,
                 'ncols':3}
    answers = {}
    answers['linear'] = np.array([[  3.5,   4.5,   5.5],
                                  [  7.5,   8.5,   9.5],
                                  [ 11.5,  12.5,  13.5]])
    answers['cubic'] = np.array([[  3.5,   4.5,   5.5],
                                 [  7.5,   8.5,   9.5],
                                 [ 11.5,  12.5,  13.5]])
    answers['quintic'] = np.array([[  3.5,   4.5,   5.5],
                                   [  7.5,   8.5,   9.5],
                                   [ 11.5,  12.5,  13.5]])
    answers['nearest'] = np.array([[ 1,  7,  8],
                                   [ 5,  7,  8],
                                   [14, 11, 11]])
    for method in ['linear','cubic','quintic','nearest']:
        grid.interpolateToGrid(otherdict,method=method)
        assert(np.equal(grid.griddata,answers[method]).all())
        grid.griddata = initialdata.copy()
        grid.geodict = initialdict.copy()
        
if __name__ == '__main__':
    testBin()
    testInterp()

    

    
