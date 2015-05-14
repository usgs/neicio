#!/usr/bin/env python

#stdlib imports
import sys
from xml.dom import minidom
import urllib2

def readStation(stationfile):
    '''Read a ShakeMap station list file from disk or a url, return station coordinates and observed data.
    Input: 
     - stationfile - A string path to a file on disk or a URL (http://earthquake.usgs.gov/archive/product/shakemap/atlas19940117123055/atlas/1423011201411/download/stationlist.xml)

    Output:
     - Dictionary with keys:
       - lat Array of station latitudes
       - lat Array of station longitudes
       - pga Array of station observed PGA values
       - pgv Array of station observed PGV values
       - psa03 Array of station observed PSA 0.3 values
       - psa03 Array of station observed PSA 1.0 values
       - psa30 Array of station observed PSA 3.0 values
    '''
    if stationfile.startswith('http:'):
        fh = urllib2.urlopen(stationfile)
        data = fh.read()
        fh.close()
        root = minidom.parseString(data)
    else:
        root = minidom.parse(stationfile)
    stations = root.getElementsByTagName('station')
    compdict = {'lat':[],'lon':[],
                'pga':[],'pgv':[],
                'psa03':[],'psa10':[],
                'psa30':[], 'name':[]}
    for station in stations:
        lat = float(station.getAttribute('lat'))
        lon = float(station.getAttribute('lon'))
        pga = float(station.getElementsByTagName('comp')[0].getElementsByTagName('pga')[0].getAttribute('value'))
        pgv = float(station.getElementsByTagName('comp')[0].getElementsByTagName('pgv')[0].getAttribute('value'))
        psa03 = float(station.getElementsByTagName('comp')[0].getElementsByTagName('psa03')[0].getAttribute('value'))
        psa10 = float(station.getElementsByTagName('comp')[0].getElementsByTagName('psa10')[0].getAttribute('value'))
        psa30 = float(station.getElementsByTagName('comp')[0].getElementsByTagName('psa30')[0].getAttribute('value'))
        name = station.getElementsByTagName('comp')[0].getAttribute('name')
        compdict['lat'].append(lat)
        compdict['lon'].append(lon)
        compdict['pga'].append(pga)
        compdict['pgv'].append(pgv)
        compdict['psa03'].append(psa03)
        compdict['psa10'].append(psa10)
        compdict['psa30'].append(psa30)
        compdict['name'].append(name)
    root.unlink()
    return compdict

if __name__ == '__main__':
    compdict = readStation(sys.argv[1])
    assert(len(compdict['lat']) == len(compdict['pga']))
    assert(len(compdict['lat']) == len(compdict['pgv']))
    assert(len(compdict['lat']) == len(compdict['psa03']))
    assert(len(compdict['lat']) == len(compdict['psa10']))
    assert(len(compdict['lat']) == len(compdict['psa30']))
    assert(len(compdict['lat']) == len(compdict['name']))
