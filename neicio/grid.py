import numpy as np
from neicutil.interp import interp2
import sys

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

    def interpolateToGrid(self,geodict,method='linear'): #implement here
        """
        Given a geodict specifying another grid extent and resolution, resample current grid to match.
        
        @param geodict: geodict dictionary from another grid whose extents are inside the extent of this grid.
        @keyword method: Optional interpolation method - ['linear', 'nearest'].
        @raise GridError: If the Grid object upon which this function is being called is not completely 
                          contained by the grid to which this Grid is being resampled.
        @raise GridError: If the resulting interpolated grid shape does not match input geodict.

        This function modifies the internal griddata and geodict object variables.
        """
        #extract the geographic information about the image we're resampling
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

        gxi = np.arange(startx,endx,xdim,dtype=float64)
        gyi = np.arange(endy,starty,-ydim,dtype=float64)
        
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
        
        self.griddata = interp2(self.griddata,xi,yi,method=method)
                
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
            return self.griddata[row,col,0]
        else:
            return self.griddata[row,col]
