#!/usr/bin/env python

#stdlib imports
import re
import math

class FixedFormatError(Exception):
    """used for noting errors with FixedFormatWriter and Reader"""

def readFixedFormatString(speclist,line):
    """
    Read a fixed format string given the line specification and a fixed-width formatted string.
    @parameter speclist: List of tuples, where each tuple contains:
                         - a sub-tuple containing the start/stop positions of the value in the line (1 offset). 
                         - A FORTRAN format string
    @parameter line:    A fixed-width formatted string.
    @return: List of values read from line according to speclist.
    @raise FixedFormatError: When input string doesn't match speclist.

    NB: This function assumes that blank spaces at positions where the spec says there should be floats or ints
    should be interpreted as NaN values.
    """
    vlist = []
    ftrans = {'a':'s','i':'i','f':'f'}
    numberpattern = r'[-+]?[0-9]*\.?[0-9]+'
    for spec in speclist:
        smin = spec[0][0]-1
        smax = spec[0][1]
        if smax > len(line):
            raise FixedFormatError,'Spec exceeds length of input string'
        ffmt = spec[1]
        valuestr = line[smin:smax]
        if ffmt.find('f') > -1:
            if valuestr.strip() == '':
                value = float('nan')
            else:
                try:
                    value = float(line[smin:smax])
                except:
                    raise FixedFormatError,'String segment "%s" does not match format "%s"' % (valuestr,ffmt)
        elif ffmt.find('i') > -1:
            if valuestr.strip() == '':
                value = float('nan')
            else:
                try:
                    value = int(line[smin:smax])
                except:
                    raise FixedFormatError,'String segment "%s" does not match format "%s"' % (valuestr,ffmt)
        else: #this is a string
            value = valuestr.strip()
        vlist.append(value)
    return vlist
    
def getFixedFormatString(speclist,vlist):
    """
    Create a fixed format string given the line specification and a list of values.
    @parameter speclist: List of tuples, where each tuple contains:
                         - a sub-tuple containing the start/stop positions of the value in the line (1 offset). 
                         - A FORTRAN format string
                         - (optional) boolean value indicating whether there should be leading zeros.
    @parameter vlist:    A list of values, which must match the format strings given in speclist,
                         with the following exception: A NaN value where the spec says float or int
                         is OK.  Spaces will be inserted for the NaN value.
    @return: Formatted string (no newline at the end).

    NB: This function assumes that any NaN values at positions where the speclist says there
    should be floats or ints are OK, and should be written out as spaces.
    """
    if len(speclist) != len(vlist):
        raise FixedFormatError,'speclist length != vlist length' 
    width = 0
    widths = []
    ftrans = {'a':'s','i':'i','f':'f'}
    numberpattern = r'[-+]?[0-9]*\.?[0-9]+'
    formatstr = ''
    formatlist = []
    offset = 1
    for i in range(0,len(speclist)):
        spec = speclist[i]
        v = vlist[i]
        #if there are spaces between the last offset and the beginning of this one,
        #add them to the format string for the line
        specrange = spec[0]
        smin = specrange[0]
        smax = specrange[1]
        #check for optional boolean indicating whether numerical values should be left-filled with zeros
        zerolead = False
        if len(spec) >= 3:
            zerolead = True
        
        specwidth = (smax-smin)+1
        spaces = ' '*(smin-offset)
        formatstr += spaces
        fmt = spec[1]
        match = re.search(numberpattern,fmt)
        numstr = fmt[match.start():match.end()]
        match = re.search('[a-z]',fmt)
        strstr = fmt[match.start():match.end()]
        if numstr.find('.') > -1:
            width = int(numstr.split('.')[0])
        else:
            width = int(numstr)
        if width != specwidth:
            fmtstring = 'Cannot reconcile format string "%s" with range (%i,%i)'
            raise FixedFormatError,fmtstring % (fmt,smin,smax)
        widths.append(width)
        isfloat = isinstance(v,float)
        if isfloat and math.isnan(v):
            isnumber = fmt.find('i') > -1 or fmt.find('f') > -1
            if isnumber:
                fmt = '%' + str(width) + 's'
                vlist[i] = ' '
            else:
                raise FixedFormatError,'String types do not support NaN values.'
        else:
            if zerolead:
                fmt = '%0' + numstr + ftrans[strstr]
            else:
                fmt = '%' + numstr + ftrans[strstr]
        formatlist.append(fmt)
        formatstr += fmt
        offset = smax+1
    try:
        string = formatstr % tuple(vlist)
        return string
    except:
        raise FixedFormatError,'Could not make a string from "%s" and "%s"' % (formatstr,','.join(vlist))

    
if __name__ == '__main__':
    speclist = [((2,2),'a1'),
                ((3,3),'a1'),
                ((17,19),'a3'),
                ((21,25),'a5'),
                ((30,32),'a3'),
                ((37,39),'a3'),
                ((44,46),'a3'),
                ((51,53),'a3'),
                ((58,60),'a3'),
                ((65,67),'a3'),
                ((69,72),'a4'),
                ((74,77),'a4'),
                ((79,86),'a8'),
                ((87,87),'a1')]
    
    vlist = ['(','#','eM0','eCLVD','eRR','eTT','ePP','eRT','eTP','ePR','NCO1','NCO2','Duration',')']
    vstr = getFixedFormatString(speclist,vlist)
    print vstr

    vlistout = readFixedFormatString(speclist,vstr)
    print vlistout
    
    vlist = ['fred',float('nan'),5]
    speclist = [((1,4),'a4'),
                ((6,10),'f5.3'),
                ((12,14),'i3',True)]
    vstr = getFixedFormatString(speclist,vlist)
    print vstr
    vlistout = readFixedFormatString(speclist,vstr)
    print vlistout
            
    
    

            
