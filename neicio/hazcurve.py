#!/usr/bin/env python

#stdlib imports
import os.path
import sys

#third party imports
import numpy as np
from neicutil.matutil import sub2ind
from matplotlib import pyplot as plt

#local imports
from grid import Grid

class HazCurveGrid(Grid):
    def __init__(self,probtextfile):
        fpath,ffile = os.path.split(probtextfile)
        ffile,fext = os.path.splitext(ffile)
        lats = []
        lons = []
        z = []
        f = open(probtextfile,'rt')
        line1 = f.readline()
        line2 = f.readline()
        for line in readlines():
            parts = line.split()
            lons.append(float(parts[0]))
            lats.append(float(parts[1]))
            zdata = [float(z) for z in parts[2:]]
            z.append(zdata)
        f.close()
        nz = len(zdata)
        lats = np.array(lats)
        lons = np.array(lons)
        ulat = np.unique(lats)
        ulon = np.unique(lons)
        xdim = ulon[1] - ulon[0]
        ydim = ulat[1] - ulat[0]
        xmin = lons.min()
        xmax = lons.max()
        ymin = lats.min()
        ymax = lats.max()
        ncols = np.int32(np.floor(((xmax+xdim)-xmin)/xdim))
        nrows = np.int32(np.floor(((ymax+ydim)-ymin)/ydim))
        zdata = np.reshape(np.array(z),nrows,ncols,nz)
        self.geodict['xmin'] = xmin
        self.geodict['xmax'] = xmax
        self.geodict['ymin'] = ymin
        self.geodict['ymax'] = ymax
        self.geodict['xdim'] = xdim
        self.geodict['ydim'] = ydim
        self.geodict['nbands'] = 1
        self.geodict['bandnames'] = [ffile]
        rows,cols = self.getRowCol(lats,lons)
        index = np.int32(sub2ind((ncols,nrows),(cols,rows)))
        self.griddata[index] = zdata
        self.griddata = np.reshape(self.griddata,(nrows,ncols))
        
        

if __name__ == '__main__':
    txtfile = sys.argv[1]
    grid = HazCurveGrid(txtfile)
    fig = plt.figure(figsize=(10,6))
    plt.imshow(grid.griddata)
    plt.colorbar(shrink=0.55)
    plt.title(grid.geodict['bandnames'][0])
    plt.savefig('%s.png' % grid.geodict['bandnames'][0])
