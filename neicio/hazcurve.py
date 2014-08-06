#!/usr/bin/env python

#stdlib imports
import os.path
import sys

#third party imports
import numpy as np
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
        line1 = f.readline().strip()
        line2 = f.readline().strip()
        self.period = float(f.readline().strip())
        #read in the band names
        xvalues = []
        for i in range(0,19):
            line = f.readline()
            xvalues.append(line.strip())

        #read in the data using numpy's very fast loadtxt function!
        self.griddata = np.loadtxt(f)
        f.close()
        
        lat = self.griddata[:,0]
        lon = self.griddata[:,1]
        self.griddata = self.griddata[:,2:]
        xmin = lon.min()
        xmax = lon.max()
        ymin = lat.min()
        ymax = lat.max()
        ulat = np.unique(lat)
        ulon = np.unique(lon)
        ydim = np.diff(ulat)[0]
        xdim = np.diff(ulon)[0]
        m = len(ulat)
        n = len(ulon)
        p = len(xvalues)

        #reshape the data so that it's oriented the way we need
        #first reshape by columns then rows then bands
        self.griddata = np.reshape(self.griddata,(m,n,p))

        self.geodict['xmin'] = xmin
        self.geodict['xmax'] = xmax
        self.geodict['ymin'] = ymin
        self.geodict['ymax'] = ymax
        self.geodict['xdim'] = xdim
        self.geodict['ydim'] = ydim
        self.geodict['ncols'] = n
        self.geodict['nrows'] = m
        self.geodict['bandnames'] = xvalues

if __name__ == '__main__':
    txtfile = sys.argv[1]
    grid = HazCurveGrid(txtfile)
    imax = grid.griddata[:,:,0].argmax()
    geodict = grid.getGeoDict()
    cx = geodict['ncols']/2
    cy = geodict['nrows']/2
    [lat,lon] = grid.getLatLon(cy,cx)
    zdata = grid.getValue(lat,lon)
    fig,axeslist = plt.subplots(nrows=1,ncols=2,figsize=(12,6))
    plt.sca(axeslist[0])
    plt.imshow(grid.griddata[:,:,0])
    plt.hold(True)
    plt.plot(cx,cy,color='pink',marker='x')
    plt.colorbar(shrink=0.55)
    plt.title('%.1f second Hazard Curve' % grid.period)
    plt.sca(axeslist[1])
    plt.semilogy(np.array(grid.geodict['bandnames']),zdata,'b')
    plt.xlabel('Frequency')
    plt.ylabel('Probability')
    plt.title('Hazard Curve at %.3f,%.3f (Period %.1f sec)' % (lat,lon,grid.period))
    plt.savefig('hazard_curve_%.1f.png' % grid.period)
