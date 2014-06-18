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
        xvalues = []
        for line in f.readlines():
            parts = line.split()
            if len(parts) == 1:
                xvalues.append(parts[0])
                continue
            lats.append(float(parts[0]))
            lons.append(float(parts[1]))
            zdata = [float(zd) for zd in parts[2:]]
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
        self.geodict['xmin'] = xmin
        self.geodict['xmax'] = xmax
        self.geodict['ymin'] = ymin
        self.geodict['ymax'] = ymax
        self.geodict['xdim'] = xdim
        self.geodict['ydim'] = ydim
        self.geodict['ncols'] = ncols
        self.geodict['nrows'] = nrows
        self.geodict['nbands'] = 1
        self.geodict['bandnames'] = xvalues
        idx = 0
        self.griddata = np.zeros((nrows,ncols,nz))
        for lat,lon in zip(lats,lons):
            row,col = self.getRowCol(lat,lon)
            self.griddata[row,col,:] = np.array(z[idx])
            idx += 1
                

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
