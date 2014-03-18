Introduction
------------

neicio is one of three Python packages containing code modules extracted from the 
PAGER (http://earthquake.usgs.gov/earthquakes/pager/) software.  This package  
contains functions and classes designed to make it easier to read in files in various spatial formats
(ESRI BIL, GMT NetCDF, ShakeMap grid.xml), read shapefiles, read/write fixed-width formats, and a 
convenient wrapper around the Python functions for making system calls.  

Installation and Dependencies
-----------------------------

This package depends on:
 * numpy, the fundamental package for scientific computing with Python. <a href="http://www.numpy.org/">http://www.numpy.org/</a>  
 * matplotlib, a Python 2D plotting library which produces publication quality figures. <a href="<a href="http://matplotlib.org/index.html">http://matplotlib.org/index.html</a>
 * scipy, a Python library which provides many user-friendly and efficient numerical routines such as routines for numerical integration and optimization. <a href="<a href="http://www.scipy.org/scipylib/index.html">http://www.scipy.org/scipylib/index.html</a>
 * basemap, a library for plotting 2D data on <em>maps</em> in Python.  <a href="<a href="http://matplotlib.org/basemap/">http://matplotlib.org/basemap/</a>

The best way to install numpy,matplotlib,and scipy is to use one of the Python distributions described here:

<a href="http://www.scipy.org/install.html">http://www.scipy.org/install.html</a>

Anaconda and Enthought distributions have been successfully tested with neicio.

Most of those distributions should include <em>pip</em>, a command line tool for installing and 
managing Python packages.  You will use pip to install the other dependencies and libcomcat itself.  
 
You may need to open a new terminal window to ensure that the newly installed versions of python and pip
are in your path.

To install basemap:

pip install basemap

To install neicio:

pip install git+git://github.com/usgs/neicio.git

Uninstalling and Updating
-------------------------

To uninstall:

pip uninstall neicio

To update:

pip install -U git+git://github.com/usgs/neicio.git



