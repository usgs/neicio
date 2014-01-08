#!/usr/bin/python
from numpy import *
import xml.dom.minidom as minidom
from xml.parsers.expat import ExpatError
from grid import Grid
import re
import sys
import datetime
from time import strptime

class ShakeGridError(Exception):
    "used to indicate an error in ShakeGrid"
    def __str__(self):
        return repr(self.args[0])

class ShakeGrid(Grid):
    """
    ShakeGrid encapsulates ShakeMap objects and allows access to data and metadata, 
    as well as parent Grid object methods.
    example:
    smgrid = ShakeGrid()
    smgrid.load('grid.xml')
    griddata = smgrid.getData()
    """
    
    AttributesDict = {}
    
    def __init__(self,shakefilename,variable='MMI'):
        """Load shakemap grid data from file.
        @param shakefilename: Path to valid ShakeMap XML file OR file-like object.
        @keyword variable: ShakeMap "z" variable to import into Grid.  At the time of this writing, the possible variables include:
                           - PGA
                           - PGV
                           - MMI (Modified Mercalli Intensity)
                           - SVEL
        @raise ShakeGridError: If input variable is not found in XML file.
        
        Populates the instance griddata, geodict, and AttributesDict objects.
        """
        self.griddata = []
        self.geodict = {}
        self.AttributesDict = {}
        #self.load(shakefilename,variable)
        #handle when input is a file-like object and not just a file name
        if not hasattr(shakefilename,'read'):
            shakefile = open(shakefilename,'r')
        else:
            shakefile = shakefilename    
        self.__loadShakeHeader(shakefile)
        
        smdict = self.AttributesDict
        gridfields = smdict['grid_field']
        didx = 0
        dunits = None

        for field in gridfields:
            if field['name'] == variable:
                didx = field['index'] - 1
                dunits = field['units']
                break
        if not didx or not dunits:
            raise ShakeGridError, "variable %s not found in %s" % (variable,shakefilename)
        
        #fill in relevant values in geodict dictionary
        self.__populateGeoDict(variable)
        
        #read in grid values
        self.__loadGridData(shakefile,didx)

        #close file object
        shakefile.close()
        
        

    #beyond the implementation hassles here of getting all the required metadata to 
    #save a grid in the ShakeMap XML format, there's a question of whether this method
    #should be implemented at all - the ShakeMap program is the primary generator of this
    #type of data, and it is potentially dangerous to be creating data that could be injected into
    #the universe without the validity of the ShakeMap software behind it.
    def save(self):
        """Raises ShakeGridError.
        @raise ShakeGridError: Always.
        """
        raise ShakeGridError, "save() method not implemented for ShakeGrid"

    def __loadShakeHeader(self,shakefile):
        """Load the "header" portion of the shakemap XML grid file.
        @param shakefile: Valid ShakeMap XML file.
        
        Populates the instance AttributesDict variable.
        """
        tline = shakefile.readline() 
        datamatch = re.compile('grid_data')
        xmltext = ''
        tlineold = ''
        while not datamatch.search(tline) and tline != tlineold:
            tlineold = tline
            xmltext = xmltext+tline
            tline = shakefile.readline()
            
        xmltext = xmltext+'</shakemap_grid>'
        smdict = self.__getShakeAttributes(xmltext)
        self.AttributesDict = smdict
        
    def __loadGridData(self,shakefile,didx):
        """Load the data portion of the XML grid file from the column specified by didx.
        @param shakefile: Valid ShakeMap XML file.
        @param didx: Valid int index of desired ShakeMap variable.

        Populates the instance griddata variable.
        """
        #allocate space for our mmi grid
        ulx = self.geodict['xmin']
        uly = self.geodict['ymax']
        xdim = self.geodict['xdim']
        ydim = self.geodict['ydim']
        nrows = self.geodict['nrows']
        ncols = self.geodict['ncols']
        nbands = 1
        self.griddata = zeros((nrows,ncols),'Float32')
        
        datamatch = re.compile('/grid_data')
        #read in the grid data
        tline = shakefile.readline()
        dmin = 99999
        dmax = -99999
        while not datamatch.search(tline):
            fields = tline.split()
            lon = float(fields[0])
            try:
                lat = float(fields[1])
            except ValueError:
                pass
            var = float(fields[didx])
            if var > dmax:
                dmax = var
            if var < dmin:
                dmin = var
            col = round(((lon - ulx)/xdim))
            if col > ncols-1 and ulx < 0 and lon > 0:
                col = round(((lon - (ulx+360))/xdim))
            row = round(((uly - lat)/ydim))
            if col < 0:
                col = 0
            if col > ncols-1:
                col = ncols-1
            if row < 0:
                row = 0
            if row > nrows-1:
                row = nrows-1
            self.griddata[row,col] = var
                
            tline = shakefile.readline()
        
    def __populateGeoDict(self,variable):
        """Populate the internal geo-referencing dictionary with the correct values.
        @param variable: ShakeMap z variable (see constructor)

        Populates the instance geodict variable.
        """
        smdict = self.AttributesDict
        self.geodict['xdim'] = smdict['grid_specification']['nominal_lon_spacing']
        self.geodict['ydim'] = smdict['grid_specification']['nominal_lat_spacing']
        self.geodict['nrows'] = smdict['grid_specification']['nlat']
        self.geodict['ncols'] = smdict['grid_specification']['nlon']
        self.geodict['xmin'] = smdict['grid_specification']['lon_min']
        self.geodict['xmax'] = self.geodict['xmin'] + ((self.geodict['ncols']-1)*self.geodict['xdim'])
        self.geodict['ymax'] = smdict['grid_specification']['lat_max']
        self.geodict['ymin'] = self.geodict['ymax'] - ((self.geodict['nrows']-1)*self.geodict['ydim'])
        #self.geodict['xmax'] = smdict['grid_specification']['lon_max']
        #self.geodict['ymin'] = smdict['grid_specification']['lat_min']
        
        
                
        #we want all grid geodicts to have a time associated with them
        #grab the time from the event tag 
        self.geodict['time'] = smdict['event']['event_timestamp']
        #make the bandnames list 
        self.geodict['bandnames'] = [variable]

    def getAttributes(self):
        """
        Dictionary representation of ShakeMap file XML "header".
        @return: Dictionary representation of ShakeMap file XML "header":
                 - shakemap_grid - Dictionary of following attributes:
                                 - event_id - The event ID, as allocated by NEIC.
                                 - shakemap_id - The event ID of the shakemap (usu. same as event_id). 
                                 - shakemap_version - The version of the shakemap grid.
                                 - code_version - The version of the shakemap code that produced this grid.
                                 - process_timestamp - The time that the shakemap was created (UTC).
                                 - shakemap_originator -  The originating network ('us','nc','sc',etc.) for the earthquake.
                                 - map_status - usually 'RELEASED'.  (Other options??)
                                 - shakemap_event_type - Type of event, either 'ACTUAL' or 'SCENARIO'.
                 - event-  Dictionary of the following attributes:
                         - magnitude - The magnitude of the event.
                         - depth - The depth (in kilometers) of the event.
                         - lat - The latitude of the epicenter.
                         - lon - The longitude of the epicenter.
                         - event_timestamp - The time that the event occurred (UTC).
                         - event_description - The FE+ region in which the event occurred.
                 - grid_specification- Dictionary of the following attributes:
                                     - lon_min - Longitude of center of left-most column of pixels.
                                     - lat_min - Longitude of center of bottom-most row of pixels.
                                     - lon_max - Longitude of center of right-most column of pixels.
                                     - lat_max - Longitude of center of top-most row of pixels.
                                     - nominal_lon_spacing - Nominal (usually not correct) dimension of grid in X direction.
                                     - nominal_lat_spacing - Nominal (usually not correct) dimension of grid in Y direction.
                                     - nlon - Number of columns in grid.
                                     - nlat - Number of rows in grid.
                 - grid_field - List of dictionaries grid fields (excluding latitude and longitude).  Keys are:
                              - index - Index of column of data (1 offset)
                              - name - Name of grid field (MMI, PGA, etc.)
                              - units - Physical units of measurement.
        """
        return self.AttributesDict

    def getMaxBorderMMI(self):
        top = self.griddata[0,:].max()
        left = self.griddata[:,0].max()
        right = self.griddata[:,-1].max()
        bottom = self.griddata[-1,:].max()
        return max(top,left,right,bottom)

    def __getShakeAttributes(self,xmltext):
        """
        Private function to return dictionary of the shakemap elements.  See getAttributes()
        """
        try:
            dom3 = minidom.parseString(xmltext)
        except ExpatError, msg:
            raise ShakeGridError,msg
        smdict = {}
        
        #get shakemap_grid attributes
        smgridElement = dom3.getElementsByTagName('shakemap_grid')[0] #shakemap grid element
        smdict['shakemap_grid'] = self.__getGridDict(smgridElement)
        
        #get event attributes
        eventElement = dom3.getElementsByTagName('event')[0]
        smdict['event'] = self.__getEventDict(eventElement)
        
        #grid_specification element
        gridspecElement = dom3.getElementsByTagName('grid_specification')[0]
        smdict['grid_specification'] = self.__getGridSpecDict(gridspecElement)

        #grid_field list
        gridfieldsList = dom3.getElementsByTagName('grid_field')
        smdict['grid_field'] = self.__getGridFieldsList(gridfieldsList)
        return smdict

    def __getGridFieldsList(self,gridfieldslist):
        grid_fields = []
        for i in range(0,len(gridfieldslist)):
            gridFieldElement = gridfieldslist[i]
            gridfield = {}
            gridfield['index'] = int(gridFieldElement.getAttribute('index'))
            gridfield['name'] = str(gridFieldElement.getAttribute('name'))
            gridfield['units'] = str(gridFieldElement.getAttribute('units'))
            grid_fields.append(gridfield)
        return grid_fields

    def __getGridDict(self,smgridElement):
        shakemap_grid = {}
        shakemap_grid['event_id'] = str(smgridElement.getAttribute('event_id'))
        shakemap_grid['shakemap_id'] = str(smgridElement.getAttribute('shakemap_id'))
        shakemap_grid['shakemap_version'] = str(smgridElement.getAttribute('shakemap_version'))
        shakemap_grid['code_version'] = str(smgridElement.getAttribute('code_version'))
        shakemap_grid['process_timestamp'] = self.__getDateTime(smgridElement.getAttribute('process_timestamp'))
        shakemap_grid['shakemap_originator'] = str(smgridElement.getAttribute('shakemap_originator').lower())
        shakemap_grid['map_status'] = str(smgridElement.getAttribute('map_status'))
        shakemap_grid['shakemap_event_type'] = str(smgridElement.getAttribute('shakemap_event_type'))
        return shakemap_grid

    def __getGridSpecDict(self,gridspecElement):
        grid_specification = {}
        grid_specification['lon_min'] = float(gridspecElement.getAttribute('lon_min'))
        grid_specification['lon_max'] = float(gridspecElement.getAttribute('lon_max'))
        grid_specification['lat_min'] = float(gridspecElement.getAttribute('lat_min'))
        grid_specification['lat_max'] = float(gridspecElement.getAttribute('lat_max'))
        grid_specification['nominal_lon_spacing'] = float(gridspecElement.getAttribute('nominal_lon_spacing'))
        grid_specification['nominal_lat_spacing'] = float(gridspecElement.getAttribute('nominal_lat_spacing'))
        grid_specification['nlat'] = int(float(gridspecElement.getAttribute('nlat')))
        grid_specification['nlon'] = int(float(gridspecElement.getAttribute('nlon')))
        
        #fix for shakemaps that go from (for example) 179 to 181.  
        #If we have that situation, let's adjust both values to be negative instead.
        if grid_specification['lon_max'] > 180:
            grid_specification['lon_max'] -= 360
            grid_specification['lon_min'] -= 360

        return grid_specification

    def __getEventDict(self,eventElement):
        event = {}
        event['magnitude'] = float(eventElement.getAttribute('magnitude'))
        event['depth'] = float(eventElement.getAttribute('depth'))
        event['lat'] = float(eventElement.getAttribute('lat'))
        event['lon'] = float(eventElement.getAttribute('lon'))
        event['event_timestamp'] = self.__getDateTime(eventElement.getAttribute('event_timestamp'))
        event['event_description'] = str(eventElement.getAttribute('event_description'))
        return event

    #we need to process two different kinds of timestamps...
    #2006-09-25T16:07:03Z
    #2006-09-25T22:03:48GMT
    #2006-09-25T22:03:48UTC
    def __getDateTime(self,timestr):
        """Convert string timestamps to Python datetime objects"""
        #strip off the trailing text portion...
        timestr = timestr[0:19]
        vdate = datetime.datetime(*strptime(timestr,"%Y-%m-%dT%H:%M:%S")[0:6])
        return vdate
        
