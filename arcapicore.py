"""
#-------------------------------------------------------------------------------
# Name:        arcapi.arcapi
# Purpose:     Core module for convenient API for arcpy
#
# Authors:     Filip Kral, Caleb Mackey
#
# Created:     01/02/2014
# Licence:     LGPL v3
#-------------------------------------------------------------------------------
# The core module of the arcapi package.
#
# All this content gets imported when you import the arcapi package.
# See arcapi __init__.py for more notes.
#
#-------------------------------------------------------------------------------
"""

import os
import sys
import time

try:
    # Python 2.x
    from urllib import urlencode
    from httplib import HTTPConnection, HTTPSConnection
    from urlparse import urlparse
    from urllib2 import Request
    from urllib2 import urlopen
except ImportError:
    # Python 3.x
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from http.client import HTTPConnection, HTTPSConnection

import json
from contextlib import closing
import datetime

try:
    import arcpy
except ImportError:
    from ArcpyMockup import ArcpyMockup
    arcpy = ArcpyMockup()


__version__ = '0.3.0'
"""Version number of arcapi"""


def names(x, filterer = None):
    """Return list of column names of a table.

    Required:
    x -- input table or table view

    Optional:
    filterer -- function, only fields where filterer returns True are listed

    Example:
    >>> names('c:/foo/bar.shp', lambda f: f.name.startswith('eggs'))
    """
    flds = arcpy.ListFields(x)
    if filterer is None: filterer = lambda a: True
    return [f.name for f in flds if filterer(f)]


def types(x, filterer = None):
    """Return list of column types of a table.

    Required:
    x -- input table or table view

    Optional:
    filterer -- function, only fields where filterer returns True are listed

    Example:
    >>> types('c:/foo/bar.shp', lambda f: f.name.startswith('eggs'))
    """
    flds = arcpy.ListFields(x)
    if filterer is None: filterer = lambda a: True
    return [f.type for f in flds if filterer(f)]


def nrow(x):
    """Return number of rows in a table as integer.

    Required:
    x -- input table or table view

    Example:
    >>> nrow('c:/foo/bar.shp')
    """
    return int(arcpy.GetCount_management(x).getOutput(0))


def values(tbl, col, w='', o=None):
    """Return a list of all values in column col in table tbl.

    If col is a single column, returns a list of values, otherwise returns
    a list of tuples of values where each tuple is one row.

    Columns included in the o parameter must be included in the col parameter!

    Required:
    tbl -- input table or table view
    col -- input column name(s) as string or a list; valid options are:
        col='colA'
        col=['colA']
        col=['colA', 'colB', 'colC']
        col='colA,colB,colC'
        col='colA;colB;colC'

    Optional:
    w -- where clause
    o -- order by clause like '"OBJECTID" ASC, "Shape_Area" DESC',
        default is None, which means order by object id if exists

    Example:
    >>> values('c:/foo/bar.shp', 'Shape_Length')
    >>> values('c:/foo/bar.shp', 'SHAPE@XY')
    >>> values('c:/foo/bar.shp', 'SHAPE@XY;Shape_Length', 'Shape_Length ASC')
    >>> # columns in 'o' must be in 'col', otherwise RuntimeError is raised:
    >>> values('c:/foo/bar.shp', 'SHAPE@XY', 'Shape_Length DESC') # Error!
    """

    # unpack column names
    if isinstance(col, (list, tuple)):
        cols = col
    else:
        col = str(col)
        separ = ';' if ';' in col else ','
        cols = [c.strip() for c in col.split(separ)]

    # indicate whether one or more than one columns were specified
    multicols = False
    if len(cols) > 1:
        multicols = True

    # construct order by clause
    if o is not None:
        o = 'ORDER BY ' + str(o)
    else:
        pass

    # retrieve values with search cursor
    ret = []
    with arcpy.da.SearchCursor(tbl, cols, where_clause = w, sql_clause=(None, o)) as sc:
        for row in sc:
            if multicols:
                ret.append(row)
            else:
                ret.append(row[0])

    return ret


def frequency(x):
    """Return a dict of counts of each value in iterable x.

    Values in x must be hashable in order to work as dictionary keys.

    Required:
    x -- input iterable object like list or tuple

    Example:
    >>> frequency([1,1,2,3,4,4,4]) # {1: 2, 2: 1, 3: 1, 4: 3}
    >>> frequency(values('c:/foo/bar.shp', 'STATE'))
    """
    x.sort()
    fq = {}
    for i in x:
        if i in fq: #has_key deprecated in 3.x
            fq[i] += 1
        else:
            fq[i] = 1
    return fq


def distinct(tbl, col, w=''):
    """Return a list of distinct values in column col in table tbl.

    Required:
    tbl -- input table or table view
    col -- input column name as string

    Optional:
    w -- where clause

    Example:
    >>> distinct('c:/foo/bar.shp', "CATEGORY")
    >>> distinct('c:/foo/bar.shp', "SHAPE@XY")
    """
    return list(set(values(tbl, col, w)))


def print_tuples(x, delim=" ", tbl=None, geoms=None, fillchar=" ",  padding=1, verbose=True, returnit = False):
    """Print and/or return list of tuples formatted as a table.


    Intended for quick printing of lists of tuples in the terminal.
    Returns None or the formatted table depending on value of returnit.


    Required:
    x -- input list of tuples to print (can be tuple of tuples, list of lists).


    Optional:
    delim -- delimiter to use between columns
    tbl -- table or list of arcpy.Field objects to take column headings from (default is None)
    geoms -- if None (default), print geometries 'as is', else as str(geom).
        Works only is valid tbl is specified.
    filchar -- string to be used to pad values
    padding -- how many extra fillchars to use in cells
    verbose -- suppress printing when False, default is True
    returnit -- if True, return the formatted table, else return None (default)
    """
    lpadding, rpadding = padding, padding
    fch = fillchar
    # find column widths
    gi = None
    if tbl is None:
        nms = ["V" + str(a) for a in range(len(x[0]))]
        tps = ["LONG" if str(ti).isdigit() else "TEXT" for ti in x[0]]
        geoms = None
    else:
        nms,tps = [],[]
        i = 0
        if isinstance(tbl, list) or isinstance(tbl, tuple):
            fields = tbl
        else:
            fields = arcpy.ListFields(tbl)
        for f in fields:
            nms.append(f.name)
            tps.append(f.type)
            if f.type.lower() == "geometry" and geoms is not None:
                gi = i # index of geometry column
            i += 1
    nmirange = range(len(nms))
    toLeft = []
    leftTypes = ("STRING", "TEXT") # field types to be left justified
    for nmi in range(len(nms)):
        if tps[nmi].upper() in leftTypes:
            toLeft.append(nmi)
    widths = []
    for nmi in range(len(nms)):
        widths.append(len(str(nms[nmi])))
    for tpl in x:
        for nmi in range(len(nms)):
            if geoms is not None and nmi == gi:
                clen = len(str(geoms))
            else:
                clen = len(str(tpl[nmi]))
            if clen > widths[nmi]:
                widths[nmi] = clen


    sbuilder = []
    frmtd = []
    for nmi in range(len(nms)):
        pad = widths[nmi] + lpadding + rpadding
        frmtd.append(str(nms[nmi]).center(pad, fch))


    hdr = delim.join(frmtd)

    if verbose:
        print(hdr) # print header

    sbuilder.append(hdr)
    for r in x:
        frmtd = []
        for nmi in range(len(nms)):
            if nmi in toLeft:
                if geoms is not None and nmi == gi:
                    pad = widths[nmi] + rpadding
                    padfull = pad + lpadding
                    valf = str(geoms).ljust(pad, fch).rjust(padfull, fch)
                else:
                    pad = widths[nmi] + rpadding
                    padfull = pad + lpadding
                    valf = str(r[nmi]).ljust(pad, fch).rjust(padfull, fch)
            else:
                if geoms is not None and nmi == gi:
                    pad = widths[nmi] + lpadding
                    padfull = pad + rpadding
                    valf = str(geoms).rjust(pad, fch).ljust(padfull, fch)
                else:
                    pad = widths[nmi] + lpadding
                    padfull = pad + rpadding
                    valf = str(r[nmi]).rjust(pad, fch).ljust(padfull, fch)
            frmtd.append(valf)
        rw = delim.join(frmtd)


        if verbose:
            print(rw) # print row
        sbuilder.append(rw)


    ret = "\n".join(sbuilder) if returnit else None
    return ret


def head(tbl, n=10, t=True, delimiter="; ", geoms=None, cols=["*"], w="", verbose=True):
    """Return top rows of table tbl.


    Returns a list where the first element is a list of tuples representing
    first n rows of table tbl, second element is a dictionary like:
    {i: {"name":f.name, "values":[1,2,3,4 ...]}} for each field index i.


    Optional:
    n -- number of rows to read, default is 10
    t -- if True (default), columns are printed as rows, otherwise as columns
    delimiter -- string to be used to separate values (if t is True)
    geoms -- if None (default), print geometries 'as is', else as str(geom).
    cols -- list of columns to include, include all by default, case insensitive
    w, where clause to limit selection from tbl
    verbose -- suppress printing if False, default is True


    Example:
    >>> tmp = head('c:/foo/bar.shp', 5, True, "|", " ")
    """
    allcols = ['*', ['*'], ('*'), [], ()]
    colslower = [c.lower() for c in cols]
    flds = arcpy.ListFields(arcpy.Describe(tbl).catalogPath)
    if cols not in allcols:
        flds = [f for f in flds if f.name.lower() in colslower]
    fs = {}
    nflds = len(flds)
    fieldnames = []
    for i in range(nflds):
        f = flds[i]
        if cols in allcols or f.name in cols:
            fieldnames.append(f.name)
            fs.update({i: {"name":f.name, "values":[]}})
    i = 0
    hd = []
    with arcpy.da.SearchCursor(tbl, fieldnames, where_clause = w) as sc:
        for row in sc:
            i += 1
            if i > n: break
            hd.append(row)
            for j in range(nflds):
                fs[j]["values"].append(row[j])


    if t:
        labels = []
        values = []
        for fld in range(nflds):
            f = fs[fld]
            fl = flds[fld]
            labels.append(str(fl.name) + " (" + str(fl.type) +  "," + str(fl.length) + ")")
            if fl.type.lower() == 'geometry' and (geoms is not None):
                values.append(delimiter.join(map(str, len(f["values"]) * [geoms])))
            else:
                values.append(delimiter.join(map(str, f["values"])))
        longestLabel = max(map(len, labels))
        for l,v in zip(labels, values):
            toprint = l.ljust(longestLabel, ".") +  ": " + v
            arcpy.AddMessage(toprint)
            if verbose:
                print(toprint)
    else:
        if verbose:
            print_tuples(hd, delim=delimiter, tbl=flds, geoms=geoms, returnit=False)
    return [hd, fs]

def chart(x, out_file='c:/temp/chart.jpg', texts={}, template=None, resolution=95, openit=True):
    """Create and open a map (JPG) showing x and return path to the figure path.

    Required:
    x -- input feature class, raster dataset, or a layer

    Optional:
    out_file -- path to output jpeg file, default is 'c:/temp/chart.jpg'
    texts -- dict of strings to include in text elements on the map (by name)
    template -- path to the .mxd to be used, default None points to mxd with
        a single text element called "txt"
    resolution -- output resolution in DPI (dots per inch)
    openit -- if True (default), exported jpg is opened in a webbrowser

    Example:
    >>> chart('c:/foo/bar.shp')
    >>> chart('c:/foo/bar.shp', texts = {'txt': 'A Map'}, resolution = 300)
    """
    todel = []
    import re
    if template is None: template = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'chart.mxd')
    if not re.findall(".mxd", template, flags=re.IGNORECASE): template += ".mxd"
    if not re.findall(".jpe?g", out_file, flags=re.IGNORECASE): out_file += ".jpg"

    mxd = arcpy.mapping.MapDocument(template)
    if not arcpy.Exists(x):
        x = arcpy.CopyFeatures_management(x, arcpy.CreateScratchName('tmp', workspace = 'in_memory')).getOutput(0)
        todel = [x]
    dtype = arcpy.Describe(x).dataType
    df = arcpy.mapping.ListDataFrames(mxd)[0]

    lr = "chart" + tstamp(tf = "%H%M%S")
    if arcpy.Exists(lr) and arcpy.Describe(lr).dataType in ('FeatureLayer', 'RasterLayer'):
        arcpy.Delete_management(lr)
    if "raster" in dtype.lower():
        arcpy.MakeRasterLayer_management(x, lr)
    else:
        arcpy.MakeFeatureLayer_management(x, lr)

    lyr = arcpy.mapping.Layer(lr)
    arcpy.mapping.AddLayer(df, lyr)

    # try to update text elements if any requested:
    for tel in texts.iterkeys():
        try:
            texel = arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", tel)[0]
            texel.text = str(texts[tel])
        except Exception as e:
            arcpy.AddMessage("Error when updating text element " + str(tel) + ": "+ str(e))
    arcpy.RefreshActiveView()
    arcpy.mapping.ExportToJPEG(mxd, out_file, resolution=resolution)

    # cleanup
    arcpy.Delete_management(lr)
    del mxd
    if todel: arcpy.Delete_management(todel[0])

    # open the chart in a browser if requested
    if openit:
        import webbrowser
        webbrowser.open_new_tab(out_file)

    return arcpy.Describe(out_file).catalogPath


def plot(x, y=None, out_file="c:/temp/plot.png", main="Arcapi Plot", xlab="X", ylab="Y", pch="+", color="r", openit=True):
    """
    Create and display a plot (PNG) showing x (and y).

    Uses matplotlib.pyplot.scatter.

    Required:
    x -- values to plot on x axis

    Optional:
    y -- values to plot on y axis or None (default), then x will be plotted
        on y axis, using index for x axis.
    out_file -- path to output file, default is 'c:/temp/plot.png'
    main -- title of the plot
    xlab -- label for x axis
    ylab -- label for y axis
    pch
    color -- color of points:
        'r': red (default), 'b': blue, 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).
    pch -- character for matplotlib plot marks, default is '+', can also be:
        +: plus sign, .: dot, o: circle, *: star, p: pentagon, s:square, x: X,
        D: diamond, h: hexagon, ^: triangle
    openit -- if True (default), exported figure is opened in a webbrowser

    Example:
    >>> x = range(20)
    >>> plot(x)
    >>> plot(x, out_file='c:/temp/pic.png')
    >>> y = list(range(50,70))
    >>> plot(x, y, 'c:/temp/pic.png', 'Main', 'X [m]', 'Y [m]', 'o', 'k')
    """
    import re
    if not re.findall(".png", out_file, flags=re.IGNORECASE): out_file += ".png"

    if y is None:
        y = x
        len(x)
        x = range(len(y))
    lx = len(x)
    ly = len(y)
    if lx != ly:
        raise ArcapiError('x and y have different length, %s and %s' % (lx, ly))

    from matplotlib import pyplot as plt
    plt.scatter(x, y, c=color, marker=pch)
    plt.title(str(main))
    plt.xlabel(str(xlab))
    plt.ylabel(str(ylab))
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)
    return


def hist(x, out_file='c:/temp/hist.png', openit=True, **args):
    """
    Create and display a plot (PNG) showing histogram of x and return computed
    histogram of values, breaks, and patches.

    Uses matplotlib.pyplot.hist, for details see help(matplotlib.pyplot.hist).
    Draws an empty plot if x is empty.

    Required:
    x -- Input data (not empty!); histogram is computed over the flattened array.

    Optional:
    bins -- int or sequence of scalars defining the number of equal-width bins.
        or the bin edges including the rightmost edge. Default is 10.
    range -- (float, float), the lower and upper range of the bins,
        default is (min(x), max(x))
    normed -- counts normalized to form a probability density if True, default False
    weights -- array_like array of weights for each element of x.
    cumulative -- cumulative counts from left are calculated if True, default False
    histtype -- 'bar'(default)|'barstacked'|'step'|'stepfilled'
    align -- 'left'|'mid'(default)|'right' to align bars to bin edges.
    orientation -- 'horizontal'(default)|'vertical'
    rwidth -- relative width [0.0 to 1.0] of the bars, default is None (automatic)
    log -- if True, empty bins are filtered out and log scale set; default False
    color -- scalar or array-like, the colors of the bar faces:
        'r': red (default), 'b': blue, 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).
        Can also be full color and style specification.
    label -- label for legend if x has multiple datasets
    out_file -- path to output file, default is 'c:/temp/hist.png'
    main -- string, histogram main title
    xlab -- string, label for the ordinate (independent) axis
    openit -- if True (default), exported figure is opened in a webbrowser

    Example:
    >>> x = numpy.random.randn(10000)
    >>> hist(x)
    >>> hist(x, bins=20, color='r', main='A Title", xlab='Example')
    """
    import matplotlib.pyplot as plt

    # sort out parameters
    extras =  ('main', 'xlab', 'ylab')
    pars = {}
    for k in args:
        if k not in extras:
            pars.update({k: args[k]})

    h = plt.hist(x, **pars)

    plt.title(str(args.get('main', 'Histogram')))
    xlab = str(args.get('xlab', 'Value'))
    ylab = 'Count'
    if args.get('Density', False):
        ylab = 'Density'

    if args.get('orientation', 'horizontal') == 'vertical':
        lab = xlab
        xlab = ylab
        ylab = lab

    plt.xlabel(str(xlab))
    plt.ylabel(str(ylab))
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)
    return h


def bars(x, out_file='c:/temp/hist.png', openit=True, **args):
    """
    Create and display a plot (PNG) showing barchart of x.

    Uses matplotlib.plt.bar, draws an empty plot if x is empty.
    Parameter width is always 1.0.

    Use matplotlib colors for coloring;
        'r': red, 'b': blue (default), 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).

    Required:
    x -- Input data. list-like of bar heights.

    Optional:
    color -- scalar or array-like, the colors of the bar faces
    edgecolor -- scalar or array-like, the colors of the bar edges
    linewidth -- scalar or array-like, default: None width of bar edge(s).
        If None, use default linewidth; If 0, don't draw edges.
    xerr -- scalar or array-like, use to generate errorbar(s) if not None (default)
    yerr -- scalar or array-like, use to generate errorbar(s) if not None (default)
    ecolor -- scalar or array-like, use as color of errorbar(s) if not None (default)
    capsize -- integer, length of error bar caps in points, default: 3
    orientation -- 'vertical'(default)|'horizontal', orientation of the bars
    log -- boolean, set the axis to be log scale if True, default is False
    # other
    out_file -- path to output file, default is 'c:/temp/hist.png'
    labels -- list-like of labels for each bar to display on x axis
    main -- string, histogram main title
    xlab -- string, label for the ordinate (independent) axis
    openit -- if True (default), exported figure is opened in a webbrowser

    Example:
    >>> x = [1,2,3,4,5]
    >>> lb = ['A','B','C','D','E']
    >>> bars(x)
    >>> bars(x, labels=lb, color='r', main='A Title', orientation='vertical')
    """
    import matplotlib.pyplot as plt
    import numpy

    width = 1.0
    # unpack arguments
    bpars = ['width', 'color', 'edgecolor', 'linewidth', 'xerr', 'yerr',
    'ecolor', 'capsize','error_kw', 'orientation', 'log']
    barpars = dict([(i, args.get(i, None)) for i in args if i in bpars])
    barpars['align'] = 'center'
    center = range(len(x))
    labels = args.get('labels', center)
    barpars['width'] = width
    orientation = barpars.get('orientation', 'vertical')

    fig, ax = plt.subplots()
    fig.canvas.draw()

    # the orientation parameter seems to have no effect on pyplot.bar, therefore
    # it is handled by calling barh instead of bar if orientation is horizontal
    if orientation == 'horizontal':
        a = barpars.pop('width', None)
        a = barpars.pop('orientation', None)
        plt.barh(center, x, **barpars)
    else:
        plt.bar(center, x, **barpars)

    xlab = str(args.get('xlab', 'Item'))
    ylab = str(args.get('ylab', 'Value'))
    if orientation == 'horizontal':
        lab = xlab
        xlab = ylab
        ylab = lab
        ax.set_yticks(center)
        ax.set_yticklabels(labels)
    else:
        ax.set_xticks(center)
        ax.set_xticklabels(labels)

    ax.set_xlabel(xlab)
    ax.set_ylabel(str(ylab))
    ax.set_title(str(args.get('main', 'Barplot')))
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)

    return


def pie(x, y=None, **kwargs):
    """
    Create and display a plot (PNG) showing pie chart of x.

    Uses matplotlib.pyplot.pie, draws an empty plot if x is empty.
    The fractional area of each wedge is given by x/sum(x).  If sum(x) <= 1,
    then the values of x will be used as the fractional area directly.

    Use matplotlib colors for coloring;
        'r': red, 'b': blue, 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).

    Required:
    x -- Input data. list-like of bar heights.

    Optional keyword arguments (see matplotlib.pyplot.pie for further details):
    y -- Groupping data - list of factor values, len(x) == len(y),
       values of x will be groupped by y and before the pie chart is plotted.
       If y is specified, labels will include the relevant y value.
    out_file -- output file, default is 'c:/temp/hist.png'
    color -- scalar or array-like, the colors of the bar faces
    labels -- list-like of labels for each wedge, or None for default labels
    explode -- scalar or array like for offsetting wedges, default None (0.0)
    main -- string, main title of the plot
    openit -- Open exported figure in a webbrowser? True(default)|False.
    autopct -- None, format string or function for labelling wedges.
    pctdistance -- scalar or array like for fine tuning placment of text
    labeldistance -- labels will be drawn this far from the pie (default is 1.1)
    shadow -- Shadow beneath the pie? False(default)|True.
    mainbox -- bbox properties of the main title, ignored if main is None
    tight -- Apply tight layout? True(default)|False

    Example:
    >>> x = [1,2,3,4,5]
    >>> lb = ['A','B','C','D','E']
    >>> pie(x)
    >>> pie(x, labels=lb, main='A Title')
    >>> pie([1,2,3,4,5,6,7], y=[1,1,2,2,3,3,3], autopct='%1.1f%%')
    >>> pie([1,2,3,4,5,6], y=[(1,'a'),(1,'a'),2,2,'b','b'], autopct='%1.1f%%')
    """
    import matplotlib.pyplot as plt

    # unpack arguments
    #y = kwargs.get('y', None) # more convenient to get as a named argument
    out_file =kwargs.get('out_file', 'c:/temp/hist.png')
    openit = kwargs.get('openit', True)
    #
    explode = kwargs.get('explode', None)
    labels = kwargs.get('labels', None)
    colors = kwargs.get('colors', ('b', 'g', 'r', 'c', 'm', 'y', 'k', 'w'))
    autopct = kwargs.get('autopct', None)
    pctdistance = kwargs.get('pctdistance', 0.6)
    labeldistance = kwargs.get('labeldistance', 1.1)
    shadow = kwargs.get('shadow', False)
    startangle = kwargs.get('startangle', 90)
    #
    main = kwargs.get('main', None)
    mainbox = kwargs.get('mainbox', None)
    legend = kwargs.get('legend', True)
    legloc = kwargs.get('legloc', 'best')
    tight = kwargs.get('tight', True)

    # handle the cases when y parameter is supplied
    # i.e. summarize x by y, construct labels etc.
    n = len(x)
    if y is not None:
        if n != len(y):
            raise ArcapiError("Lenghts of x and y must match, %s != %s" %
                (n, len(y))
            )

        freqs = {}
        for xi,yi in zip(x,y):
            if yi in freqs:
                freqs[yi] += xi
            else:
                freqs[yi] = xi

        x,y = [],[]
        for k in freqs:
            x.append(freqs.get(k))
            y.append(k)
        labels = y

    # expand explode, labels, colors, etc. to the right length
    n = len(x)
    if explode is not None:
        if isinstance(explode, list) or isinstance(explode, tuple):
            if len(explode) != n:
                explode = ( explode * n )[0:n]
        else:
            explode = [explode] * n
    if labels is not None:
        if isinstance(labels, list) or isinstance(labels, tuple):
            if len(labels) != n:
                labels = ( labels * n )[0:n]
        else:
            labels = [labels] * n
    if colors is not None:
        if isinstance(colors, list) or isinstance(colors, tuple):
            if len(colors) != n:
                colors = ( colors * n )[0:n]
        else:
            colors = [colors] * n

    plt.figure(1)
    plt.subplot(1,1,1)
    pieresult = plt.pie(
        x,
        explode=explode,
        labels=labels,
        colors=colors,
        autopct=autopct,
        pctdistance=pctdistance,
        shadow=shadow,
        labeldistance=labeldistance
    )
    patches = pieresult[0]
    texts = pieresult[1]

    # add title
    if main is not None:
        plt.title(main, bbox=mainbox)

    # add legend
    if legend:
        if labels is None:
            labels = map(str, x)
            plt.legend(patches, labels, loc=legloc)

    # make output square and tight
    plt.axis('equal')
    if tight:
        plt.tight_layout()

    # save and display
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)

    return


def rename_col(tbl, col, newcol, alias = ''):
    """Rename column in table tbl and return the new name of the column.

    This function first adds column newcol, re-calculates values of col into it,
    and deletes column col.
    Uses arcpy.ValidateFieldName to adjust newcol if not valid.
    Raises ArcapiError if col is not found or if newcol already exists.

    Required:
    tbl -- table with the column to rename
    col -- name of the column to rename
    newcol -- new name of the column

    Optional:
    alias -- field alias for newcol, default is '' to use newcol for alias too
    """
    if col != newcol:
        d = arcpy.Describe(tbl)
        dcp = d.catalogPath
        flds = arcpy.ListFields(tbl)
        fnames = [f.name.lower() for f in flds]
        newcol = arcpy.ValidateFieldName(newcol, tbl) #os.path.dirname(dcp))
        if col.lower() not in fnames:
            raise ArcapiError("Field %s not found in %s." % (col, dcp))
        if newcol.lower() in fnames:
            raise ArcapiError("Field %s already exists in %s" % (newcol, dcp))
        oldF = [f for f in flds if f.name.lower() == col.lower()][0]
        if alias == "": alias = newcol
        arcpy.AddField_management(tbl, newcol, oldF.type, oldF.precision, oldF.scale, oldF.length, alias, oldF.isNullable, oldF.required, oldF.domain)
        arcpy.CalculateField_management(tbl, newcol, "!" + col + "!", "PYTHON_9.3")
        arcpy.DeleteField_management(tbl, col)
    return newcol


def tlist_to_table(x, out_tbl, cols, nullNumber=None, nullText=None):
    """Save a list of tuples as table out_tbl and return catalog path to it.

    Required:
    x -- list of tuples (no nesting!), can be list of lists or tuple of tuples
    out_tbl -- path to the output table
    cols -- list of tuples defining columns of x. Can be defined as:
        [('colname1', 'type1'), ('colname2', 'type2'), ...]
        ['colname1:type1:lgt1', 'colname2:type2', ('colname3', 'type3')]
        [('colname1', 'type1'), 'colname2:type2:lgt2, ...]
        where types are case insensitive members of:
        ('SHORT', 'SMALLINTEGER', 'LONG', 'INTEGER', 'TEXT', 'STRING', 'DOUBLE',
        'FLOAT')
        Each column definition can have third element for length of the field,
        e.g.: ('ATextColumn', 'TEXT', 250).
        To leave out length, simply leave it out or set to '#'

    Optional:
    nullNumber -- a value to replace null (None) values in numeric columns, default is None and does no replacement
    nullText -- a value to replace null (None) values in text columns, default is None and does no replacement

    Example:
    >>> x = [(...),(...),(...),(...),(...), ...]
    >>> ot = 'c:/temp/foo.dbf'
    >>> tlist_to_table(x, ot, [('IDO', 'SHORT'), ('NAME', 'TEXT', 200)]
    >>> tlist_to_table(x, ot, ['IDO:SHORT', 'NAME:TEXT:200']
    """
    # decode column names, types, and lengths
    cols = [tuple(c.split(":")) if type(c) not in (tuple, list) else c for c in cols]
    # remember what indexes to replace if values are null
    replaceNumbers, replacesText = [], []
    for i in range(len(cols)):
        if cols[i][1].upper() in ('TEXT', 'STRING'):
            replacesText.append(i)
        else:
            replaceNumbers.append(i)

    doReplaceNumber = False if nullNumber is None else True
    doReplaceText = False if nullText is None else True
    doReplace = doReplaceNumber or doReplaceText

    dname = os.path.dirname(out_tbl)
    if dname in('', u''): dname = arcpy.env.workspace
    r = arcpy.CreateTable_management(dname, os.path.basename(out_tbl))
    out_tbl = r.getOutput(0)
    # add the specified fields
    for f in cols:
        fname = f[0]
        ftype = f[1].upper()
        flength = '#'
        if len(f) > 2:
            flength = int(f[2]) if str(f[2]).isdigit() else '#'
        arcpy.AddField_management(out_tbl, fname, ftype, '#', '#', flength)
    # rewrite all tuples
    fields = [c[0] for c in cols]

    with arcpy.da.InsertCursor(out_tbl, fields) as ic:
        for rw in x:
            if doReplace:
                rw = list(rw)
                if i in replaceNumbers:
                    if rw[i] is None:
                        rw[i] = nullNumber
                if i in replacesText:
                    if rw[i] is None:
                        rw[i] = nullText
                rw = tuple(rw)
            ic.insertRow(rw)
    return out_tbl


def docu(x, n = None):
    """Print x.__doc__ string of the argument line by line using Python's print.

    Similar to builtin help() but allows to limit number of rows printed.

    Optional:
    n -- print only n first rows (or everything if n > number of rows or None)
    """
    dc = x.__doc__
    dc = dc.split("\n")
    nrows = len(dc)
    n = nrows if n is None else n
    n = min(n, nrows)
    j = 0
    for i in dc:
        print(i)
        j += 1
        if j == n: break
    return


def meta(datasource, mode="PREPEND", **args):
    """Read/write metadata of ArcGIS Feature Class, Raster Dataset, Table, etc.

    Returns a dictionary of all accessible (if readonly) or all editted entries.

    *** This function may irreversibly alter metadata, see details below! ***

    The following entries (XML elements) can be read or updated:
    Title ("dataIdInfo/idCitation/resTitle")
    Purpose ("dataIdInfo/idPurp")
    Abstract ("dataIdInfo/idAbs")

    This function exports metadata of the datasource to XML file using template
    'Metadata/Stylesheets/gpTools/exact copy of.xslt' from ArcGIS installation
    directory. Then it loads the exported XML file into memory using Pythons
    xml.etree.ElementTree, modifies supported elements, writes a new XML file,
    and imports this new XML file as metadata to the datasource.
    If the content of exported metada does not contain element dataInfo,
    it is assumend the metadata is not up to date with current ArcGIS version
    and UpgradeMetadata_conversion(datasource, 'ESRIISO_TO_ARCGIS') is applied!
    Try whether this function is appropriate for your work flows on dummy data.

    Required:
    datasource -- path to the data source to update metadata for
    mode -- {PREPEND|APPEND|OVERWRITE}, indicates whether new entries will be
        prepended or appended to existing entries, or whether new entries will
        overwrite existing entries. Case insensitive.
    **args, keyword arguments of type string indicating what entries to update:
        title, string to use in Title
        purpose, string to use in Purpose
        abstract, string to use in Abstract
        If no keyword argument is specifed, metadata are read only, not edited.

    Example:
    >>> fc = 'c:/foo/bar.shp'
    >>> meta(fc) # reads existing entries
    >>> meta(fc, 'OVERWRITE', title="Bar") # updates title
    >>> meta(fc, 'append', purpose='example', abstract='Column Spam means eggs')
    """
    import xml.etree.ElementTree as ET
    xslt = None # metadata template, could be exposed as a parameter
    sf = arcpy.env.scratchFolder
    tmpmetadatafile = arcpy.CreateScratchName('tmpmetadatafile', workspace=sf)

    # checks
    if xslt is None:
        template = 'Metadata/Stylesheets/gpTools/exact copy of.xslt'
        arcdir = arcpy.GetInstallInfo()['InstallDir']
        xslt = os.path.join(arcdir, template)
    if not os.path.isfile(xslt):
        raise ArcapiError("Cannot find xslt file " + str(xslt))
    mode = mode.upper()

    lut_name_by_node = {
        'dataIdInfo/idCitation/resTitle': 'title',
        'dataIdInfo/idPurp': 'purpose',
        'dataIdInfo/idAbs': 'abstract'
    }

    # work
    r = arcpy.XSLTransform_conversion(datasource, xslt, tmpmetadatafile)
    tmpmetadatafile = r.getOutput(0)
    with file(tmpmetadatafile, "r") as f:
        mf = f.read()
    tree = ET.fromstring(mf)

    # check if read-only access requested (no entries supplied)
    readonly = True if len(args) == 0 else False
    reader = {}
    if readonly:
        args = {'title':'', 'purpose':'', 'abstract': ''}
    else:
        # Update the metadata version if it is not up to date
        if tree.find('dataIdInfo') is None:
            arcpy.conversion.UpgradeMetadata(datasource, 'ESRIISO_TO_ARCGIS')
            os.remove(tmpmetadatafile)
            r = arcpy.XSLTransform_conversion(datasource, xslt, tmpmetadatafile)
            tmpmetadatafile = r.getOutput(0)
            with file(tmpmetadatafile, "r") as f:
                mf = f.read()
            tree = ET.fromstring(mf)

    # get what user wants to update
    entries = {}
    if args.get('title', None) is not None:
        entries.update({'dataIdInfo/idCitation/resTitle': args.get('title')})
    if args.get('purpose', None) is not None:
        entries.update({'dataIdInfo/idPurp': args.get('purpose')})
    if args.get('abstract', None) is not None:
        entries.update({'dataIdInfo/idAbs': args.get('abstract')})

    # update entries
    for p,t in entries.iteritems():
        el = tree.find(p)
        if el is None:
            if not readonly:
                wm = "Element %s not found, creating it from scratch." % str(p)
                arcpy.AddWarning(wm)
                pparent = "/".join(p.split("/")[:-1])
                parent = tree.find(pparent)
                if parent is None:
                    em = "Could not find parent %s as parent of %s in %s " % \
                        (pparent, p, str(datasource))
                    raise ArcapiError(em)
                subel = ET.SubElement(parent, p.split("/")[-1])
                subel.text = str(t)
                el = subel
                del subel
        else:
            if not readonly:
                pre, mid, post = ('', '', '')
                if mode != "OVERWRITE":
                    # remember existing content if not overwrite
                    mid = '' if el.text is None else el.text
                    joiner = '&lt;br/&gt;'
                else:
                    mid = str('' if t is None else t)
                    joiner = ''
                if mode == 'APPEND': post = str('' if t is None else t)
                if mode == 'PREPEND': pre = str('' if t is None else t)
                el.text = joiner.join((pre, mid, post))
        reader.update({lut_name_by_node[p]: getattr(el, 'text', None)})

    # write a new xml file to be imported
    mf = ET.tostring(tree)
    with file(tmpmetadatafile, "w") as f:
        f.write(mf)

    # import new xml file as metadata
    r = arcpy.MetadataImporter_conversion(tmpmetadatafile, datasource)
    msg("Updated metadata for " +  str(datasource))

    # try to clean up
    try: os.remove(tmpmetadatafile)
    except: pass

    return reader


def msg(x, timef='%Y-%m-%d %H:%M:%S', verbose=True, log=None, level='message'):
    """Print (and optionally log) a message using print and arcpy.AddMessage.

    In python console, arcpy.AddMessage does not work but print does.
    A message like 'P:2014-02-16 20:44:35: foo' is printed.
    In geoprocessing windows, print does not work but arcpy.AddMessage does,
    A message like 'T:2014-02-16 20:44:35: foo' is printed.
    In Windows command line, both messages are printed.

    arcpy.AddWarning is used if level is 'warning'
    arcpy.AddError is used if level is 'error', sys.exit() is called then.

    If log file does not exist, it is created, otherwise message is appended.

    Required:
    x -- content of the message

    Optional:
    timef -- time format, default is "%Y-%m-%d %H:%M:%S" (YYYY-MM-DD HH:MM:SS)
    verbose -- if True (default) print the message to the console
    log -- file to append the message to, the default is None (i.e. no appending)
    level -- one of 'message'|'warning'|'error' or 0|1|2 respectively

    Example:
    >>> msg('foo') # P:2014-02-16 20:44:35: foo
    >>> msg('foo', '%H%M%S') # P:204503: foo
    >>> msg('foo', '%H%M%S', True, 'c:/temp/log.txt') # P:204531: foo
    """
    x = str(x)
    level = str(level).lower()
    doexit = False
    tstamp = time.strftime(timef, time.localtime())
    if verbose:
        m = tstamp + ": " + x
        if level in ('message', '0'):
            print("P:" + m)
            arcpy.AddMessage("T:" + m)
        elif level in ('warning', '1'):
            print("W:" + m)
            arcpy.AddWarning("T:" + m)
        elif level in ('error', '2'):
            print("E:" + m)
            arcpy.AddError("T:" + m)
            doexit = True
        else:
            em = "Level %s not in 'message'|'warning'|'error'|0|1|2." % (level)
            raise ArcapiError(em)

    if log not in ("", None):
        with open(log, "a") as fl:
            fl.write("P:" + tstamp + ": " + x + "\n")

    if doexit:
        try: sys.exit()
        except: pass


def list_environments(x=[], printit=False):
    """Return a list of 2-tuples of all arcgis environments.

    Optional:
    x -- list of names of environment settings, default is empty list, i.e. all
    printit -- if True, a readable representation of the dictionary is printed using Python's print function.

    Example:
    >>> tmp = list_environments(['snapRaster', 'extent'], 1)
    >>> tmp = list_environments([], 1)
    """
    envs = [en for en in dir(arcpy.env) if not en.startswith("_") and en not in ('items', 'keys', 'iteritems', 'iterkeys', 'values')]
    if len(x) > 0:
        x = [i.lower() for i in x]
        envs = [en for en in envs if en.lower() in x]
    ret = []
    for en in envs:
        env = getattr(arcpy.env, en)
        if printit:
            print(str(str(en) + " ").ljust(30, ".") + ": " + str(env))
        ret.append((en, env))
    return ret


def oidF(table):
    """Return name of the object ID field in table table"""
    return arcpy.Describe(table).OIDFieldName


def shpF(fc):
    """Return name of the Shape (Geometry) field in feature class fc"""
    return arcpy.Describe(fc).ShapeFieldName


def tstamp(p = "", tf="%Y%m%d%H%M%S", d="_", m=False, s=()):
    """Returns time stamped string.

    Return string like p + time in tf + d + s[0] + d + s[1] + d + ... s[n]
    If m is True, it will print a message too.

    Optional:
    p -- prefix
    tf -- fime format, default is "%Y%m%d%H%M%S" (i.e. YYYYMMDDHHMMSS)
    d -- delimiter between elements of s
    s -- tuple or list of postfixes

    Example:
    >>> ap.tstamp() # '20140216184029'
    >>> ap.tstamp("lr") # 'lr20140216184045'
    >>> ap.tstamp("lr", "%H%M%S") # 'lr184045'
    >>> ap.tstamp("lr", "%H%M%S") # 'lr184045'
    >>> ap.tstamp("lr", "%H%M%S", s=('run',1)) # 'lr184527_run_1'
    """
    bits = str(d).join(map(str, s))
    if bits: bits = d + bits
    stamp = str(p) + time.strftime(tf, time.localtime()) + bits
    if m: msg(stamp, "")
    return stamp


def dlt(x):
    """arcpy.Delete_management(x) if arcpy.Exists(x).

    Return False if x does not exist, True if x exists and was deleted.
    """
    deletted = False
    if arcpy.Exists(x):
        arcpy.Delete_management(x)
        deletted = True
    return deletted


def cleanup(x, verbose=False, **args):
    """Delete items in x and return number of items that could not be deleted.

    This function uses the dlt function, which in turn uses
    arcpy. Exists and arcpy.management.Delete. The deletion is wrapped in a try
    statement so failed deletions are skipped silently.

    Required:
    x -- iterable of items to delete

    Optional:
    verbose -- suppress messages if False (default), otherwise print messages
    **args -- keyword arguments 'timef' and 'log' for function 'msg'

    Example:
    >>> cleanup(['c:/foo/bar.shp', 'lyr', 'c:/foo/eggs.tif'])
    """
    cnt = 0
    for i in x:
        try:
            deleted = dlt(i)
        except:
            deleted = False
        if deleted:
            m = "Cleanup deleted " + str(i)
        else:
            m = "Cleanup could not delete " + str(i)
        msg(m, args.get('timef', '%Y-%m-%d %H:%M:%S'), verbose, args.get('log', None))
    return cnt


def to_points(tbl, out_fc, xcol, ycol, sr, zcol='#', w=''):
    """Convert table to point feature class, return path to the feature class.

    Required:
    tbl -- input table or table view
    out_fc -- path to output feature class
    xcol -- name of a column in tbl that stores x coordinates
    ycol -- name of a column in tbl that stores y coordinates
    sr -- spatial reference for out_fc
        sr can be either arcpy.SpatialReference object or a well known id as int

    Optional:
    zcol -- name of a column in tbl that stores y coordinates, default is '#'
    w -- where clause to limit the rows of tbl considered, default is ''

    Example:
    >>> t = 'c:/foo/bar.shp'
    >>> o = 'c:/foo/bar_pts.shp'
    >>> table_to_points(t, o, "XC", "YC", 4326, zcol='#', w='"FID" < 10')
    >>> table_to_points(t, o, "XC", "YC", arcpy.SpatialReference(27700))
    >>> table_to_points(t, o, "XC", "YC", arcpy.describe(tbl).spatialReference)
    """
    lrnm = tstamp('lr', '%m%d%H%M%S', '')
    if type(sr) != arcpy.SpatialReference:
        sr = arcpy.SpatialReference(sr)
    lr = arcpy.MakeXYEventLayer_management(tbl, xcol, ycol, lrnm, sr, zcol).getOutput(0)
    if str(w) not in ('', '*'):
        arcpy.SelectLayerByAttribute_management(lr, "NEW_SELECTION", w)
    out_fc = arcpy.CopyFeatures_management(lr, out_fc).getOutput(0)
    dlt(lr)
    return (arcpy.Describe(out_fc).catalogPath)


def update_col_from_dict(x, y, xcol, xidcol=None, xw='', na=None):
    """Update column in a table with values from a dictionary.

    Return number of updated records.

    Required:
    x -- table to update
    y -- dictionary with new values
    xcol -- name of the column of x to update

    Optional:
    xidcol -- column of x to be used as keys to look up values in y,
        default is None, which means to use object id field.
    xw -- where clause to select rows to update from x
    na -- value to be used instead of new value for non-matching records,
        default is None, use (1,1) to leave original value if match is not found

    Example:
    >>> fc = 'c:/foo/bar.shp'
    >>> d = {1: 'EN', 2:'ST', 3:'WL', 4:'NI'}
    >>> update_col_from_dict(fc, d, 'country_code')
    >>> update_col_from_dict(fc, d, 'country_num', 'country_code', na='Other')
    """
    if xidcol is None:
        xidcol = arcpy.Describe(x).OIDFieldName

    # indicate whether to leave nonmatching values unchenged or set to na
    identity = False if na != (1,1) else True

    if xcol == xidcol:
        selfupdate = True
        cols = [xidcol]
    else:
        selfupdate = False
        cols = [xidcol, xcol]

    cnt = 0
    with arcpy.da.UpdateCursor(x, cols, where_clause = xw) as uc:
        for row in uc:
            ido = row[0]

            if identity:

                # branch that leaves unmatched records unchanged
                if ido in y:
                    newval = y[ido]
                    if selfupdate:
                        row[0] = newval
                    else:
                        row[1] = newval
                    uc.updateRow(row)
                    cnt += 1
                else:
                    pass

            else:
                # branch that sets unmatched records to na
                newval = y.get(ido, na)
                if selfupdate:
                    row[0] = newval
                else:
                    row[1] = newval
                uc.updateRow(row)
                cnt += 1

    return cnt


def to_scratch(name, enforce=False):
    """Return path to a dataset called name in scratch workspace.

    LIMITATION: Reliable for geodatabases only! Does not handle extensions.

    Returns os.path.join(arcpy.env.scratchWorkspace, name).
    If scratchWorkspace is None, it tries workspace, then scratchGDB.

    This function 'to_scratch' has also an alias 'tos'!

    Required:
    name -- basename of the output dataset

    Optional:
    enforce -- if True, arcpy.CreateScratchName is used to ensure name does not
        exist in scratch workspace, otherwise returns basename equal to name.

    Example:
    >>> to_scratch('foo', 0) # '.../scratch.gdb/foo'
    >>> to_scratch('foo', 1) # '.../scratch.gdb/foo0'
    >>> to_scratch('foo.shp', 0) # '.../scratch.gdb/foo_shp'
    >>> to_scratch('foo.shp', 1) # '.../scratch.gdb/foo_shp0'
    >>> tos('foo', 0) # '.../scratch.gdb/foo'
    """
    ws = arcpy.env.scratchWorkspace
    if ws is None: ws = arcpy.env.workspace
    if ws is None: ws = arcpy.env.scratchGDB

    if arcpy.Describe(ws).workspaceType.lower() == 'filesystem':
        m = "Scratch workspace is a folder, scratch names may be incorrect."
        msg(m)
        arcpy.AddWarning(m)

    nm = os.path.basename(name)
    nm = arcpy.ValidateTableName(nm, ws)
    if enforce:
        nm = arcpy.CreateScratchName(nm, workspace=ws)
    else:
        nm = os.path.join(ws, nm)
    return nm


def wsp(ws = None):
    """Get or set arcpy.env.workspace and return its path.

    If ws is None and arcpy.env.workspace is None, this function will set
    arcpy.env.workspace to arcpy.env.scratchGDB and return its path.

    Optional:
    ws -- path to workspace, default is None.
        If ws is a non-existing file geodatabse, it will be created.

    Example:
    >>> # if executed in order
    >>> ev = arcpy.env
    >>> wsp() # sets ev.workspace = ec.scratchGDB if ev.workspace is None
    >>> wsp('c:/temp') # sets ev.workspace = 'c:/temp', returns 'c:/temp'
    >>> wsp() # now returns 'c:/temp'
    """
    if ws is None:
        ws = arcpy.env.workspace
        if ws is None:
            ws = arcpy.env.scratchGDB
            arcpy.env.workspace = ws
    else:
        if ws[-4:].lower() == '.gdb' and not arcpy.Exists(ws):
            import re
            ws = arcpy.management.CreateFileGDB(os.path.dirname(ws), re.sub(".gdb", "", os.path.basename(ws), re.IGNORECASE), "CURRENT").getOutput(0)
        arcpy.env.workspace = ws
    return arcpy.env.workspace


def swsp(ws = None):
    """Get or set arcpy.env.scratchWorkspace and return its path.

    If ws is None and arcpy.env.scratchWorkspace is None, this function will set
    arcpy.env.scratchWorkspace to arcpy.env.scratchGDB and return its path.

    This function 'swsp' has also an alias 'wsps'!

    Optional:
    ws -- path to scratch workspace, default is None
        If ws is a non-existing file geodatabse, it will be created.

    Example:
    >>> # if executed in order
    >>> ev = arcpy.env
    >>> swsp() # sets ev.scratchWorkspace = ec.scratchGDB if ev.scratchWorkspace is None
    >>> swsp('c:/temp') # sets ev.scratchWorkspace = 'c:/temp', returns 'c:/temp'
    >>> swsp() # now returns 'c:/temp'
    """
    if ws is None:
        ws = arcpy.env.scratchWorkspace
        if ws is None:
            ws = arcpy.env.scratchGDB
            arcpy.env.scratchWorkspace = ws
    else:
        if ws[-4:].lower() == '.gdb' and not arcpy.Exists(ws):
            import re
            ws = arcpy.management.CreateFileGDB(os.path.dirname(ws), re.sub(".gdb", "", os.path.basename(ws), re.IGNORECASE), "CURRENT").getOutput(0)
        arcpy.env.scratchWorkspace = ws
    return arcpy.env.scratchWorkspace


def summary(tbl, cols=['*'], modes=None, maxcats=10, w='', verbose=True):
    """Summary statistics about columns of a table.

    Required:
    tbl -- table

    Optional:
    cols -- list of columns to look at or ['*'] for all columns (default).
    modes -- list of columns of the same length of cols.
        allowed values are "NUM", "CAT", "IGNORE"
        mode_i indicates if column_i should be treated as numeric value,
        categorical variable, or if it should be ignored.
        Default is None, if which case mode is determined as follows:
            CAT for columns of type TEXT or STRING
            NUM for SHORT, SMALLINTEGER, LONG, INTEGER, DOUBLE, FLOAT
            IGNORE for all other types.
    maxcats -- maximum number of categories to keep track of for CAT columns
        Records of superfluous categories are counted together as ('...').
    w -- where clause to limit the rows of tbl considered, default is ''
    verbose -- suppress printing if False, default is True

    Example:
    >>> summary('c:/foo/bar.shp')
    >>> summary('c:/foo/bar.shp', ['smap', 'eggs'], ['NUM', 'CAT'])
    """
    cattypes = ('TEXT', 'STRING')
    numtypes = ('SHORT', 'SMALLINTEGER', 'LONG', 'INTEGER', 'DOUBLE', 'FLOAT')
    modetypes = ("NUM", "CAT", "IGNORE")
    fields = arcpy.ListFields(tbl)
    fields = dict([(f.name, f) for f in fields])
    if cols in([], ['*'], None):
        cols = fields.keys()

    if modes is None:
        modes = []
        for c in cols:
            fld = fields.get(c, None)
            if fld is None:
                raise ArcapiError("Column %s not found." % (c))
            fldtype = fld.type.upper()
            if fldtype in numtypes:
                modes.append("NUM")
            elif fldtype in cattypes:
                modes.append("CAT")
            else:
                modes.append("IGNORE")
    else:
        modes = [str(m).upper() for m in modes]
        if not set(modes).issubset(set(modetypes)):
            raise ArcapiError("modes can only be one of %s" % (str(modetypes)))

    nc = len(cols)
    cixs = range(nc)
    stats = {}
    for ci in cixs:
        colname = cols[ci]
        stats[ci] = {
            "col": colname,
            "type": getattr(fields.get(colname, None), 'type', None),
            "cats": {}, "min":None, "max":None, "n": 0, "na": 0
        }

    with arcpy.da.SearchCursor(tbl, cols, where_clause = w) as sc:
        for row in sc:
            for ci in cixs:
                mode = modes[ci]
                statsci = stats[ci]
                v = row[ci]
                if mode == "CAT":
                    cats = statsci["cats"]
                    if cats is not None:
                        ncats = len(cats)
                        if v in cats:
                            cats[v] += 1
                        else:
                            if ncats < maxcats:
                                cats[v] = 1
                            else:
                                cats[('...')] = cats.get(('...'), 0) + 1
                elif mode == "NUM":
                    if v is None:
                        statsci["na"] += 1
                    else:
                        statsci["n"] += 1
                        m = statsci["min"]
                        if m is None or v < m:
                            statsci["min"] = v
                        m = statsci["max"]
                        if m is None or v > m:
                            statsci["max"] = v
                        statsci["sum"] = statsci.get("sum", 0) + v
                else:
                    # mode is IGNORE
                    pass

        # calculate means
        for i in cixs:
            sm = stats[i].get('sum', None)
            n = stats[i]['n']
            if n > 0 and sm is not None:
                stats[i]['mean'] = sm / n

        if verbose:
            width = 10
            fulline = '-' * 40
            print(fulline)
            print(str(tbl))
            print(str(arcpy.Describe(tbl).catalogPath))
            print(fulline)
            for j,i in stats.iteritems():
                mode = modes[j]
                print('COLUMN'.ljust(width) + ": " + str(i.get('col', None)))
                print('type'.ljust(width) + ": "+ str(i.get('type', None)))
                if mode == "NUM":
                    print('min'.ljust(width) + ": " + str(i.get('min', None)))
                    print('max'.ljust(width) + ": " + str(i.get('max', None)))
                    print('mean'.ljust(width) + ": " + str(i.get('mean', None)))
                    print('sum'.ljust(width) + ": " + str(i.get('sum', None)))
                    print('n'.ljust(width) + ": " + str(i.get('n', None)))
                    print('na'.ljust(width) + ": " + str(i.get('na', None)))
                elif mode == "CAT":
                    cats = i["cats"]
                    if len(cats) > 0:
                        print("CATEGORIES:")
                        catable = sorted(zip(cats.keys(), cats.values()), key = lambda a: a[1], reverse = True)
                        print_tuples(catable)
                else:
                    pass
                print(fulline)
    return stats


def remap_sa(st, stop, step, n=1):
    """Create a spatial analyst format reclassify remap range (list)
    [[start value, end value, new value]...]

    >>> # ex: make range groups from 50 - 80
    >>> remap_sa(50, 80, 10)
    [[50, 60, 1], [60, 70, 2], [70, 80, 3]]

    st   -- start value (int)
    stop -- stop value (int)
    step -- step value for range (int)

    Optional:
    n -- new value interval, default is 1 (int)
    """

    tups = [[i,i+step] for i in range(st, stop, step)]
    return [[t] + [(tups.index(t)+1)*n] for t in tups]


def remap_3d(st, stop, step, n=1):
    """Create a 3D analyst format reclassify remap range (str)
    "start end new;..."

    Required:
    st --   start value (int)
    stop -- stop value (int)
    step -- step value for range (int)

    Optional:
    n -- new value interval, default is 1 (int)

    Example:
    >>> # make range groups from 50 - 80
    >>> remap_3d(50, 80, 10)
    '50 60 1;60 70 2;70 80 3'
    """

    tups = [[i,i+step] for i in range(st, stop, step)]
    return ';'.join(' '.join([str(i) for i in t] + [str((tups.index(t)+1)*n)]) for t in tups)


def find(pattern, path, sub_dirs=True):
    """Find files matching a wild card pattern.

    Parameters:
    pattern -- wild card search (str)
    path -- root directory to search
    sub_dirs -- search through all sub directories? default is True (bool)

    Example:
    >>> # find SQL databases (.mdf files)
    >>> find('*.mdf', r'/ArcServer1/SDE')
    /arcserver1/SDE/ALBT/Albertville.mdf
    /arcserver1/SDE/ARLI/Arlington.mdf
    /arcserver1/SDE/BELL/BellePlaine.mdf
    /arcserver1/SDE/BGLK/BigLake.mdf
    """
    import fnmatch

    theFiles = []
    for path, dirs, files in os.walk(path):
        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                theFiles.append(os.path.abspath(os.path.join(path, filename)))
        if sub_dirs in [False, 'false', 0]:
            break
    return theFiles


def int_to_float(raster, out_raster, decimals):
    """Convert an Integer Raster to a Float Raster
    *** Requires spatial analyst extension ***

    E.g., for a cell with a value of 45750, using this tool with 3
    decimal places will give this cell a value of 45.750

    Required:
    raster -- input integer raster
    out_raster -- new float raster
    decimals -- number of places to to move decimal for each cell

    Example:
    >>> convertIntegerToFloat(r'C:/Temp/ndvi_int', r'C:/Temp/ndvi_float', 4)
    """
    try:
        import arcpy.sa as sa

        # check out license
        arcpy.CheckOutExtension('Spatial')
        fl_rast = sa.Float(arcpy.Raster(raster) / float(10**int(decimals)))
        try:
            fl_rast.save(out_raster)
        except:
            # having random issues with Esri GRID format, change to tiff
            #   if grid file is created
            if not arcpy.Exists(out_raster):
                out_raster = out_raster.split('.')[0] + '.tif'
                fl_rast.save(out_raster)
        try:
            arcpy.CalculateStatistics_management(out_raster)
            arcpy.BuildPyramids_management(out_raster)
        except:
            pass

        msg('Created: %s' %out_raster)
        arcpy.CheckInExtension('Spatial')
        return out_raster
    except ImportError:
        return 'Module arcpy.sa not found.'


def fill_no_data(in_raster, out_raster, w=5, h=5):
    """Fill "NoData" cells with mean values from focal statistics.

    Use a larger neighborhood for raster with large areas of no data cells.

    *** Requires spatial analyst extension ***

    Required:
    in_raster -- input raster
    out_raster -- output raster

    Optional:
    w -- search radius width for focal stats (rectangle)
    h -- search radius height for focal stats (rectangle)

    Example:
    >>> fill_no_data(r'C:/Temp/ndvi', r'C:/Temp/ndvi_filled', 10, 10)
    """
    try:
        import arcpy.sa as sa
        # Make Copy of Raster
        _dir, name = os.path.split(arcpy.Describe(in_raster).catalogPath)
        temp = os.path.join(_dir, 'rast_copyxxx')
        if arcpy.Exists(temp):
            arcpy.Delete_management(temp)
        arcpy.CopyRaster_management(in_raster, temp)

        # Fill NoData
        arcpy.CheckOutExtension('Spatial')
        filled = sa.Con(sa.IsNull(temp),sa.FocalStatistics(temp,sa.NbrRectangle(w,h),'MEAN'),temp)
        filled.save(out_raster)
        arcpy.BuildPyramids_management(out_raster)
        arcpy.CheckInExtension('Spatial')

        # Delete original and replace
        if arcpy.Exists(temp):
            arcpy.Delete_management(temp)
        msg('Filled NoData Cells in: %s' %out_raster)
        return out_raster
    except ImportError:
        return 'Module arcpy.sa not found.'


def meters_to_feet(in_dem, out_raster, factor=3.28084):
    """Convert DEM Z units by a factor, default factor converts m -> ft.
    *** Requires spatial analyst extension ***

    Required:
    in_dem -- input dem
    out_raster -- new raster with z values as feet
    factor -- number by which the input DEM is multiplied,
        default is 3.28084 to convert metres to feet.

    Example:
    >>> meters_to_feet(r'C:/Temp/dem_m', r'C:/Temp/dem_ft')
    """
    try:
        import arcpy.sa as sa
        arcpy.CheckOutExtension('Spatial')
        out = sa.Float(sa.Times(arcpy.Raster(in_dem), factor))
        try:
            out.save(out_raster)
        except:
            # having random issues with esri GRID format
            #  will try to create as tiff if it fails
            if not arcpy.Exists(out_raster):
                out_raster = out_raster.split('.')[0] + '.tif'
                out.save(out_raster)
        try:
            arcpy.CalculateStatistics_management(out_raster)
            arcpy.BuildPyramids_management(out_raster)
        except:
            pass
        arcpy.AddMessage('Created: %s' %out_raster)
        arcpy.CheckInExtension('Spatial')
        return out_raster
    except ImportError:
        return 'Module arcpy.sa not found'


def currentMxd():
    """Return handle to the CURRENT map document.
    ***Can be used only in an ArcMap session***
    """
    return arcpy.mapping.MapDocument("CURRENT")


def fixArgs(arg, arg_type=list):
    """Fixe arguments from a script tool.

    For example, when using a script tool with a multivalue parameter,
    it comes in as "val_a;val_b;val_c".  This function can automatically
    fix arguments based on the arg_type.
    Another example is the boolean type returned from a script tool -
    instead of True and False, it is returned as "true" and "false".

    Required:
    arg --  argument from script tool (arcpy.GetParameterAsText() or sys.argv[1]) (str)
    arg_type -- type to convert argument from script tool parameter. Default is list.

    Example:
    >>> # example of list returned from script tool multiparameter argument
    >>> arg = "val_a;val_b;val_c"
    >>> fixArgs(arg, list)
    ['val_a', 'val_b', 'val_c']
    """
    if arg_type == list:
        if isinstance(arg, str):
            # need to replace extra quotes for paths with spaces
            # or anything else that has a space in it
            return list(map(lambda a: a.replace("';'",";"), arg.split(';')))
        else:
            return list(arg)
    if arg_type == float:
        if arg != '#':
            return float(arg)
        else:
            return ''
    if arg_type == int:
        return int(arg)
    if arg_type == bool:
        if str(arg).lower() == 'true' or arg == 1:
            return True
        else:
            return False
    if arg_type == str:
        if arg in [None, '', '#']:
            return ''
    return arg


def copy_schema(template, new, sr=''):
    """Copy the schema (field definition) of a feature class or a table.

    Required:
    template -- template table or fc
    new -- new output fc or table

    Optional:
    sr -- spatial reference (only applies if fc) If no sr
          is defined, it will default to sr of template.

    Example:
    >>> copy_schema(r'C:/Temp/soils_city.shp', r'C:/Temp/soils_county.shp')
    """
    path, name = os.path.split(new)
    desc = arcpy.Describe(template)
    ftype = desc.dataType
    if 'table' in ftype.lower():
        arcpy.CreateTable_management(path, name, template)
    else:
        stype = desc.shapeType.upper()
        sm = 'SAME_AS_TEMPLATE'
        if not sr:
            sr = desc.spatialReference
        arcpy.CreateFeatureclass_management(path, name, stype, template, sm, sm, sr)
    return new


def make_poly_from_extent(ext, sr):
    """Make an arcpy polygon object from an input extent object.,Returns
    a polygon geometry object.

    Required:
    ext -- extent object
    sr -- spatial reference

    Example
    >>> ext = arcpy.Describe(fc).extent
    >>> sr = 4326  #WKID for WGS 84
    >>> poly = make_poly_from_extent(ext, sr)
    >>> arcpy.CopyFeatures_management(poly, r'C:/Temp/Project_boundary.shp')
    """
    array = arcpy.Array()
    array.add(ext.lowerLeft)
    array.add(ext.lowerRight)
    array.add(ext.upperRight)
    array.add(ext.upperLeft)
    array.add(ext.lowerLeft)
    return arcpy.Polygon(array, sr)


def list_all_fcs(gdb, wild = '*', ftype='All', rel=False):
    """Return a list of all feature classes in a geodatabase.

    if rel is True, only relative paths will be returned.  If
    false, the full path to each feature classs is returned
    Relative path Example:

    >>> # Return relative paths for fc
    >>> gdb = r'C:/TEMP/test.gdb'
    >>> for fc in getFCPaths(gdb, rel=True):
    >>> print(fc)

    Utilities/Storm_Mh
    Utilities/Storm_Cb
    Transportation/Roads


    Required:
    gdb -- geodatabase containing feature classes to be listed
    wild -- wildcard for feature classes. Default is "*"
    ftype -- feature class type. Default is 'All'
             Valid values:

             Annotation - Only annotation feature classes are returned.
             Arc - Only arc (or line) feature classes are returned.
             Dimension - Only dimension feature classes are returned.
             Edge - Only edge feature classes are returned.
             Junction - Only junction feature classes are returned.
             Label - Only label feature classes are returned.
             Line - Only line (or arc) feature classes are returned.
             Multipatch - Only multipatch feature classes are returned.
             Node - Only node feature classes are returned.
             Point - Only point feature classes are returned.
             Polygon - Only polygon feature classes are returned.
             Polyline - Only line (or arc) feature classes are returned.
             Region - Only region feature classes are returned.
             Route - Only route feature classes are returned.
             Tic - Only tic feature classes are returned.
             All - All datasets in the workspace. This is the default value.

    Optional:
    rel -- option to have relative paths. Default is false;
           will include full paths unless rel is set to True
    """
    # feature type (add all in case '' is returned
    # from script tool
    if not ftype:
        ftype = 'All'
    arcpy.env.workspace = gdb

    # loop through feature classes
    feats = []

    # Add top level fc's (not in feature data sets)
    feats += arcpy.ListFeatureClasses(wild, ftype)

    # loop through feature datasets
    for fd in arcpy.ListDatasets('*', 'Feature'):
        arcpy.env.workspace = fdws = os.path.join(gdb, fd)
        feats += [os.path.join(fd, fc) for fc in
                  arcpy.ListFeatureClasses(wild, ftype)]

    # return list of features, relative pathed or full pathed
    if rel:
        return sorted(feats)
    else:
        return sorted([os.path.join(gdb, ft) for ft in feats])


def field_list(in_fc, filterer=[], oid=True, shape=True, objects=False):
    """Return a list of fields or a list of field objects on input feature class.

    This function will handle list comprehensions to either return field names
    or field objects. Object ID and Geometry fields are omitted by default.

    Required:
    in_fc -- input feature class, feature layer,  table, or table view

    Optional:
    filterer -- Default is empty list.  If a list is passed in, it will list
                all fields
    oid -- Default is True.  If set to True, will list all fields
           excluding Geometry and other Geometry. (bool)
    shape -- Default is True.  If true will return the Geometry field (bool)
    object -- Default is False.  If set to true, will return field objects
              instead of field names allowing for access to field properties such as
              field.name, field.type, field.length, etc. (bool)

    Example:
    >>> field_list(r'C:/Temp/Counties.shp', ['STATE_FIPS', 'COUNTY_CODE'], objects=True)
    """

    # add exclude types and exclude fields
    ex_type = []
    if not oid:
        ex_type.append('OID')
    if not shape:
        ex_type.append('Geometry')
    exclude = map(lambda x: x.lower(), filterer)

    # return either field names or field objects
    if objects:
        return [f for f in arcpy.ListFields(in_fc)
                      if f.type not in ex_type
                      and f.name.lower() not in exclude]
    else:
        return [f.name.encode('utf-8') for f in arcpy.ListFields(in_fc)
                      if f.type not in ex_type
                      and f.name.lower() not in exclude]


def get_field_type(in_field, fc=''):
    """Converts esri field type returned from list fields or describe fields
    to format for adding fields to tables.

    Required:
    in_field -- field name to find field type. If no feature class
        is specified, the in_field paramter should be a describe of
        a field.type

    Optional:
    fc -- feature class or table.  If no feature class is specified,
        the in_field paramter should be a describe of a field.type

    Example
    >>> # field type of 'String' needs to be 'TEXT' to be added to table
    >>> # This is a text type field
    >>> # now get esri field type
    >>> print(getFieldType(table, 'PARCEL_ID'))#esri field.type return is 'String', we want 'TEXT'
    TEXT
    """
    if fc:
        field = [f.type for f in arcpy.ListFields(fc) if f.name == in_field][0]
    else:
        field = in_field
    if field in lut_field_types:
        return lut_field_types[field]
    else:
        return None


def match_field(table_or_list, pat, multi=False):
    """Return a list of field objects where name matches the specified pattern.

    Required:
    table_or_list -- input table or feature class or list of fields
    pat -- pattern to match to field

    Optional:
    multi: if True, will return a list of all matches,
           otherwise returns the first match

    Example:
    >>> match_field(r'C:/Temp/Counties.shp', 'county_*', True)
    ['COUNTY_CODE', 'COUNTY_FIPS']
    """

    import fnmatch

    if isinstance(table_or_list, list):
        fields = table_or_list
    else:
        fields = [f.name for f in arcpy.ListFields(table_or_list)]
    all_mats = []
    for f in fields:
        if fnmatch.fnmatch(f, pat):
            if not multi:
                return f
            else:
                all_mats.append(f)
    return all_mats

def add_fields_from_table(in_tab, template, add_fields=[]):
    """Add fields (schema only) from one table to another

    Required:
    in_tab -- input table
    template -- template table containing fields to add to in_tab
    add_fields -- fields from template table to add to input table (list)

    Example:
    >>> add_fields_from_table(parcels, permits, ['Permit_Num', 'Permit_Date'])
    """

    # fix args if args from script tool
    if isinstance(add_fields, str):
        add_fields = add_fields.split(';')

    # grab field types
    f_dict = dict((f.name, [get_field_type(f.type), f.length, f.aliasName]) for f in arcpy.ListFields(template))

    # Add fields
    for field in add_fields:
        if field in f_dict:
            f_ob = f_dict[field]
            arcpy.AddField_management(in_tab, field, f_ob[0], field_length=f_ob[1], field_alias=f_ob[2])
            msg('Added field: {0}'.format(field))
    return


def create_field_name(fc, new_field):
    """Return a valid field name that does not exist in fc and
    that is based on new_field.

    Required:
    fc -- feature class, feature layer, table, or table view
    new_field -- new field name, will be altered if field already exists

    Example:
    >>> fc = 'c:/testing.gdb/ne_110m_admin_0_countries'
    >>> create_field_name(fc, 'NEWCOL') # NEWCOL
    >>> create_field_name(fc, 'Shape') # Shape_1
    """

    # if fc is a table view or a feature layer, some fields may be hidden;
    # grab the data source to make sure all columns are examined
    fc = arcpy.Describe(fc).catalogPath
    new_field = arcpy.ValidateFieldName(new_field, os.path.dirname(fc))

    # maximum length of the new field name
    maxlen = 64
    dtype = arcpy.Describe(fc).dataType
    if dtype.lower() in ('dbasetable', 'shapefile'):
        maxlen = 10

    # field list
    fields = [f.name.lower() for f in arcpy.ListFields(fc)]

    # see if field already exists
    if new_field.lower() in fields:
        count = 1
        while new_field.lower() in fields:

            if count > 1000:
                raise ArcapiError('Maximum number of iterations reached in uniqueFieldName.')

            if len(new_field) > maxlen:
                ind = maxlen - (1 + len(str(count)))
                new_field = '{0}_{1}'.format(new_field[:ind], count)
                count += 1
            else:
                new_field = '{0}_{1}'.format(new_field, count)
                count += 1

    return new_field


def join_using_dict(source_table, in_field, join_table, join_key, join_values=[]):
    """Join values from one table to another using dictionary.

    Add fields from one table to another by using a dictionary rather
    than joining tables.  There must be a field with common values between the
    two tables to enable attribute matching.  Values from "join_key" field in
    "join_table" should be unique.  This function can be faster than a standard
    Join Tool for tables with only couple of hundreds or thousands of records.
    This function alters the input source_table.
    Returns path to the altered source table.

    source_table -- table to add fields
    in_field -- join field with common values from join_table
    join_table -- table containing fields to add
    join_key -- common field to match values to source_table
    join_values -- fields to add from join_table to source_table

    Example:
    >>> parcels = r'C:/Temp/Parcels.gdb/Parcels'
    >>> permits = r'C:/Temp/Parcels.gdb/Permits'
    >>> add_flds = ['PERMIT_NUM', 'PERMIT_DATE', 'NOTE']
    >>> join_using_dict(parcels, 'PIN', permits', 'PARCEL_ID', add_flds)
    """

    # test version for cursor type (data access module available @ 10.1 +)
    ver = arcpy.GetInstallInfo()['Version']
    dataAccess = False
    if ver != '10.0':
        dataAccess = True


    # Get Catalog path (for feature layers and table views)
    cat_path = arcpy.Describe(source_table).catalogPath

    # Find out if source table is NULLABLE
    if not os.path.splitext(cat_path)[1] in ['.dbf','.shp']:
        nullable = 'NULLABLE'
    else:
        nullable = 'NON_NULLABLE'

    # Add fields to be copied
    update_fields = []
    join_list = arcpy.ListFields(join_table)
    for field in join_list:
        ftype = field.type
        name = field.name
        length = field.length
        pres = field.precision
        scale = field.scale
        alias = field.aliasName
        domain = field.domain
        for fldb in join_values:
            if fldb == name:
                name = create_field_name(source_table, fldb)
                arcpy.AddField_management(source_table,name,ftype,pres,scale,length,alias,nullable,'',domain)
                msg("Added '%s' field to \"%s\"" %(name, os.path.basename(source_table)))
                update_fields.insert(join_values.index(fldb), name.encode('utf-8'))

    # update new fields
    path_dict = {}
    if dataAccess:

        # Create Dictionary
        join_values.insert(0, join_key)
        with arcpy.da.SearchCursor(join_table, join_values) as srows:
            for srow in srows:
                path_dict[srow[0]] = tuple(srow[1:])

        # Update Cursor
        update_index = list(range(len(update_fields)))
        row_index = list(x+1 for x in update_index)
        update_fields.insert(0, in_field)
        with arcpy.da.UpdateCursor(source_table, update_fields) as urows:
            for row in urows:
                if row[0] in path_dict:
                    try:
                        allVals =[path_dict[row[0]][i] for i in update_index]
                        for r,v in zip(row_index, allVals):
                            row[r] = v
                        urows.updateRow(row)
                    except: pass

    else:
        # version 10.0
        rows = arcpy.SearchCursor(join_table)
        for row in rows:
            path_dict[row.getValue(join_key)] = tuple(row.getValue(v) for v in join_values)
        del rows

        # Update Cursor
        rows = arcpy.UpdateCursor(source_table)
        for row in rows:
            theVal = row.getValue(in_field)
            if theVal in path_dict:
                try:
                    for i in range(len(update_fields)):
                        row.setValue(update_fields[i],path_dict[theVal][i])
                    rows.updateRow(row)
                except: pass
        del rows
    msg('Fields in "%s" updated successfully' %(os.path.basename(source_table)))
    return source_table


def concatenate(vals=[], delimiter='', number_only=False):
    """Concatenate a list of values using a specified delimiter.

    Required:
    vals -- list of values to concatenate

    Optional:
    delimiter -- separator for new concatenated string. Default is '' (no delimiter)
    number_only -- if True, only numbers in list will be used. Default is False (bool)
    """
    if number_only:
        return delimiter.join(''.join(str(i) for i in v if str(v).isdigit()) for v in vals)
    else:
        return delimiter.join(map(str, vals))


def concatenate_fields(table, new_field, length, fields=[], delimiter='', number_only=False):
    """Create a new field in a table and concatenate user defined fields.

    This can be used in situations such as creating a Section-Township-Range
    field from 3 different fields.
    Returns the field name that was added.

    Required:
    table -- Input table
    new_field -- new field name
    length -- field length
    fields -- list of fields to concatenate

    Optional:
    delimiter -- join value for concatenated fields
        (example: '-' , all fields will be delimited by dash)
    number_only -- if True, only numeric values from a text field are extracted.
        Default is False.

    Example:
    >>> sec = r'C:/Temp/Sections.shp'
    >>> concatenate_fields(sec, 'SEC_TWP_RNG', 15, ['SECTION', 'TOWNSHIP', 'RANGE'], '-')
    """

    # Add field
    new_field = create_field_name(table, new_field)
    arcpy.AddField_management(table, new_field, 'TEXT', field_length=length)

    # Concatenate fields
    if arcpy.GetInstallInfo()['Version'] != '10.0':
        # da cursor
        with arcpy.da.UpdateCursor(table, fields + [new_field]) as rows:
            for r in rows:
                r[-1] = concatenate(r[:-1], delimiter, number_only)
                rows.updateRow(r)

    else:
        # 10.0 cursor
        rows = arcpy.UpdateCursor(table)
        for r in rows:
            r.setValue(new_field, concatenate([r.getValue(f) for f in fields], delimiter, number_only))
            rows.updateRow(r)
        del r, rows
    return new_field


def list_data(top, **options):
    """Walk down a file structure and pick up all data sets (items).
    Returns a generator of full paths to the items.
    Uses arcpy.da.Walk to discover GIS data.

    Use the oneach parameter to do something with each item as it is discovered.

    Parameters:
        top -- full path to the root workspace to start from

    Optional keyword arguments:
        exclude -- Function that takes item as a parameter and returns True if
            the item should be skipped. Default is None, all items are listed.
        exclude_dir -- Function that takes the directory name as a parameter and
            returns True if the whole directory should be skipped.
            Default is None, all directories are listed.
        oneach -- Function that takes the item as a parameter.
            Default is None and does nothing
        onerror -- Function to handle errors, see arcpy.da.Walk help
        datatypes -- list of all data types to discover, see arcpy.da.Walk help
        type -- Feature and raster data types to discover, see arcpy.da.Walk help
            Feature: Multipatch, Multipoint, Point, Polygon, Polyline
            Raster: BIL, BIP, BMP, BSQ, DAT, GIF, GRID, IMG, JP2, JPG, PNG, TIF
        skippers -- iterable of strings, item is skipped if it contains a skipper
            Skippers are not case sensitive

    Example:
    >>> list_data(r'c:/temp')
    >>> skippers = (".txt", ".xls", ".ttf")
    >>> exclude = lambda a: "_expired2013" in a
    >>> list_data(r'c:/temp', exclude=exclude, skippers=skippers)
    """

    exclude = options.get('exclude', None)
    exclude_dir = options.get('exclude_dir', None)
    oneach = options.get('oneach', None)
    onerror = options.get('onerror', None)
    datatypes = options.get('datatypes', None)
    types = options.get('type', None)
    skippers = options.get('skippers', None)

    if skippers is not None:
        skippers = [str(sk).lower() for sk in skippers]

    for dirpath, dirnames, filenames in arcpy.da.Walk(top, topdown=True, onerror=onerror, followlinks=False, datatype=datatypes, type=types):

        if exclude_dir is not None:
            dirnames = [di for di in dirnames if not exclude_dir(di)]

        for filename in filenames:
            item = os.path.join(dirpath, filename)
            if exclude is not None:
                 # skip items for which exclude is True
                if exclude(item):
                    continue
            if skippers is not None:
                 # skip items that contain any skipper values
                if any([item.lower().find(sk) > -1 for sk in skippers]):
                    continue
            if oneach is not None:
                # handle item if 'oneach' handler provided
                oneach(item)
            yield item


def create_pie_chart(fig, table, case_field, data_field='', fig_title='', x=8.5, y=8.5, rounding=0):
    """Create a pie chart based on a case field and data field.

    If no data_field is specified, the pie chart slices reflect frequency
    of value in the case_field.

    WARNING: although this tool successfully creates a pie chart .png,
             it throws a C++ runtime error.  TODO: Need to investigate this.

    Required:
    fig -- output png file for pie chart
    table -- table for data to create pie chart
    case_field -- field that will be used to summarize values,
                  and also will provide the labels for the legend.

    Optional:
    data_field -- field with values for pie chart.  If no field is
                  specified, count of each value in case_field will be used
    fig_title -- title for the pie chart figure
    x --  size for y-axis side (in inches)
    y --  size for y-axis side (in inches)
    rounding -- rounding for pie chart legend labels.  Default is 0.

    Example:
    >>> wards = r'C:/Temp/Voting_Wards.shp'
    >>> figure = r'C:/Temp/Figures/Election_results.png'
    >>> create_pie_chart(figure, wards, 'CANDIDATE', 'NUM_VOTES', 'Election Results')
    """

    import pylab, numpy, re

    # make sure figure is .png or .jpg
    if not re.findall('.png', fig, flags=re.IGNORECASE):
        out_file += '.png'

    # rounding nested function, (rounding value of 0 from built in round does not return integer)
    def rnd(f, t, rounding):
        return round((f/float(t))*100, rounding) if rounding > 0 else int((f/float(t))*100)

    # Grab unique values
    with arcpy.da.SearchCursor(table, [case_field]) as rows:
        cases = sorted(list(set(r[0] for r in rows)))

    # if not data_field
    tmp_fld = 'cnt_xx_xx_'
    fields = [case_field, data_field]
    if not data_field:
        arcpy.AddField_management(table, tmp_fld, 'SHORT')
        with arcpy.da.UpdateCursor(table, [tmp_fld]) as rows:
            for r in rows:
                r[0] = 1
                rows.updateRow(r)
        fields = [case_field, tmp_fld]

    # vals for slices
    vals=[]

    # sum values
    sum_table = str(arcpy.Statistics_analysis(table, r'in_memory/sum_tab_xxx',
                                              [[fields[1], 'SUM']],
                                              fields[0]).getOutput(0))
    fields[1] = 'SUM_{0}'.format(fields[1])
    with arcpy.da.SearchCursor(sum_table, fields) as rows:
        for r in rows:
            vals.append([r[0],r[1]])

    # clean up tmp_fld if necessary
    if not data_field:
        if tmp_fld in [f.name for f in arcpy.ListFields(table)]:
            try:
                arcpy.DeleteField_management(table, tmp_fld)
            except:
                pass

    # Create Pie Charts
    the_fig = pylab.figure(figsize=(x, y))
    pylab.axes([0.1, 0.1, 0.8, 0.8])
    label = [v[0] for v in vals]
    fracs = [v[1] for v in vals]
    tot = [sum(fracs)] * len(fracs)
    if len(label) == len(fracs):
        cmap = pylab.plt.cm.prism
        color = cmap(numpy.linspace(0., 1., len(fracs)))
        pie_wedges = pylab.pie(fracs,colors=color,pctdistance=0.5, labeldistance=1.1)
        for wedge in pie_wedges[0]:
            wedge.set_edgecolor('white')
        pylab.legend(map(lambda x, f, t: '{0} ({1}, {2}%)'.format(x, f, rnd(f, t, rounding)),
                                                                  label, fracs, tot),
                                                                  loc=(0,0), prop={'size':8})
        pylab.title(fig_title)
        pylab.savefig(fig)
        msg('Created: %s' %fig)
    arcpy.Delete_management(sum_table)
    return fig


def combine_pdfs(out_pdf, pdf_path_or_list, wildcard=''):
    """Combine PDF documents using arcpy mapping  module

    Required:
    out_pdf -- output pdf document (.pdf)
    pdf_path_or_list -- list of pdf documents or folder
        path containing pdf documents.

    Optional:
    wildcard -- optional wildcard search (only applies
        when searching through paths)

    Example:
    >>> # test function with path
    >>> out_pdf = r'C:/Users/calebma/Desktop/test.pdf'
    >>> path = r'C:/Users/calebma/Desktop/pdfTest'
    >>> combine_pdfs(out_pdf, path)

    >>> # test function with list
    >>> out = r'C:/Users/calebma/Desktop/test2.pdf'
    >>> pdfs = [r'C:/Users/calebma/Desktop/pdfTest/Mailing_Labels5160.pdf',
                r'C:/Users/calebma/Desktop/pdfTest/Mailing_Taxpayer.pdf',
                r'C:/Users/calebma/Desktop/pdfTest/stfr.pdf']
    >>> combine_pdfs(out, pdfs)
    """

    import glob

    # Account for differences in ArcGIS for Desktop and ArcGIS Pro
    mp = getattr(arcpy, "mapping", getattr(arcpy, 'mp', None))

    # Create new PDF document
    pdfDoc = mp.PDFDocumentCreate(out_pdf)

    # if list, use that to combine pdfs
    if isinstance(pdf_path_or_list, list):
        for pdf in pdf_path_or_list:
            pdfDoc.appendPages(pdf)
            msg('Added "{0}" to "{1}"'.format(pdf, os.path.basename(out_pdf)))

    # search path to find pdfs
    elif isinstance(pdf_path_or_list, str):
        if os.path.exists(pdf_path_or_list):
            search = os.path.join(pdf_path_or_list,'{0}*.pdf'.format(wildcard))
            for pdf in sorted(glob.glob(search)):
                pdfDoc.appendPages(os.path.join(pdf_path_or_list, pdf))
                msg('Added "{0}" to "{1}"'.format(pdf, os.path.basename(out_pdf)))

    # Save and close pdf document
    pdfDoc.saveAndClose()
    del pdfDoc
    msg('Created: {0}'.format(out_pdf))
    return out_pdf


def request_http(url, data=None, data_type='text', headers={}):
    """Return result of an HTTP Request.

    Only GET and POST methods are supported. To issue a GET request, parameters
    must be encoded as part of the url and data must be None. To issue a POST
    request, parameters must be supplied as a dictionary for parameter data and
    the url must not include parameters.

    Parameters:
        url -- URL to issue the request to
    Optional:
        data -- dictionary of data to send
        data_type -- text(default)|xml|json|jsonp|pjson
            data is always obtained as text, but the this function
            can convert the text depending on the data_type parameter:
                text -- return the raw text as it is
                xml -- parse the text with xml.etree.ElementTree and return
                json -- parse the text with json.loads(text) and return
                jsonp,pjson -- parse the text with json.loads(text) and return
                    also, add parameter callback to the request
        header -- dictionary of headers to include in the request
    Example:
    >>> request('http://google.com')
    >>> u = 'http://sampleserver3.arcgisonline.com/ArcGIS/rest/services'
    >>> request(u,{'f':'json'}, 'json')
    >>> request('http://epsg.io/4326.xml', None, 'xml')
    """

    result = ''
    callback = 'callmeback' # may not be used

    # prepare data
    data_type = str(data_type).lower()
    if data_type in ('jsonp', 'pjson'):
        if data is None:
            data = {}
        data['callback'] = callback

    if data is not None:
         data = urlencode(data)
         data = bytes(data.encode("utf-8"))

    # make the request
    rq = Request(url, data, headers)
    re = urlopen(rq)
    rs = re.read()

    # handle result
    if data_type in ('json', 'jsonp', 'pjson'):
        rs = rs.strip()
        rs = rs.decode("utf-8")

        # strip callback function if present
        if rs.startswith(callback + '('):
            rs = rs.lstrip(callback + '(')
            rs = rs[:rs.rfind(')')]

        result = json.loads(rs)
    elif data_type == 'xml':
        from xml.etree import ElementTree as ET
        rs = rs.strip()
        rs = rs.decode("utf-8")
        result = ET.fromstring(rs)
    elif data_type == 'text':
        result = rs
    else:
        raise Exception('Unsupported data_type %s ' % data_type)

    return result


def request_https(url, data=None, data_type="text", headers={}):
    """Return result of an HTTPS Request.
    Uses HTTPSConnection to issue the request.

    Only GET and POST methods are supported. To issue a GET request, parameters
    must be encoded as part of the url and data must be None. To issue a POST
    request, parameters must be supplied as a dictionary for parameter data and
    the url must not include parameters.

    Parameters:
        url -- URL to issue the request to
    Optional:
        data -- dictionary of data to send
        data_type -- text(default)|xml|json|jsonp|pjson
            data is always obtained as text, but the this function
            can convert the text depending on the data_type parameter:
                text -- return the raw text as it is
                xml -- parse the text with xml.etree.ElementTree and return
                json -- parse the text with json.loads(text) and return
                jsonp,pjson -- parse the text with json.loads(text) and return
                    also, add parameter callback to the request
        header -- dictionary of headers to include in the request
    Example:
    >>> request_https('https://gitgub.com')
    >>> u = 'https://sampleserver3.arcgisonline.com/ArcGIS/rest/services'
    >>> request_https(u,{'f':'json'}, 'json')
    """
    url = str(url)
    callback = '' # may not be used

    # add the https protocol if not already specified
    if not url.lower().startswith("https://"):
        url = "https://" + url

    urlparsed = urlparse(url)
    hostname = urlparsed.hostname
    path = url[8 + len(hostname):] # get path as url without https and host name

    # connect to the host and issue the request
    with closing(HTTPSConnection(hostname)) as cns:

        if data is None:

            if data_type == 'jsonp' or data_type == 'pjson':
                # TODO: Make sure callback parameter is included
                pass

            # use GET request, all parameters must be encoded as part of the url
            cns.request("GET", path, None, headers)

        else:

            if data_type == 'jsonp' or data_type == 'pjson':
                raise Exception("data_type 'jsonp' not allowed for POST method!")

            # use POST request, data must be a dictionary and not part of the url
            d = urlencode(data)
            d = bytes(d.encode("utf-8"))
            cns.request("POST", path, d, headers)

        r = cns.getresponse()
        s = r.read()
        s = s.decode("utf-8")
        cns.close()

    # convert to required format
    result = None
    if data_type is None or data_type == 'text':
        result = s
    elif data_type == 'json':
        result = json.loads(s)
    elif data_type == 'jsonp' or data_type == 'pjson':
        result = json.loads(s.lstrip(callback + "(").rstrip(")"))
    elif data_type == 'xml':
        from xml.etree import ElementTree as ET
        rs = rs.strip()
        result = ET.fromstring(rs)

    return result


def request(url, data=None, data_type='text', headers={}):
    """Return result of an HTTP or HTTPS Request.

    Uses urllib2.Request to issue HTTP request and the HTTPSConnection
    to issue https requests.
    Only GET and POST methods are supported. To issue a GET request, parameters
    must be encoded as part of the url and data must be None. To issue a POST
    request, parameters must be supplied as a dictionary for parameter data and
    the url must not include parameters.

    ***Security warning***
    If url does not contain the protocol (http:// or https://) but just //,
    this function will first try https request, but if that fails, http request
    will be issued. For security reasons, protocol should be always specified,
    otherwise sensitive data inteded for encrypted connection (https) may be
    send to an unencripted connection. For example, consider you use the // to
    request a https url and you need to include secret token in the header.
    If the request fails, this function will attept to issue another request
    over http and will include the secret token with the http request, which can
    then be intercepted by malicious Internet users!

    Parameters:
        url -- URL to issue the request to
    Optional:
        data -- dictionary of data to send
        data_type -- text(default)|xml|json|jsonp|pjson
            data is always obtained as text, but the this function
            can convert the text depending on the data_type parameter:
                text -- return the raw text as it is
                xml -- parse the text with xml.etree.ElementTree and return
                json -- parse the text with json.loads(text) and return
                jsonp,pjson -- parse the text with json.loads(text) and return
                    also, add parameter callback to the request
        headers -- dictionary of headers to include in the request
    Example:
    >>> request('http://google.com')
    >>> u = 'http://sampleserver3.arcgisonline.com/ArcGIS/rest/services'
    >>> request(u,{'f':'json'}, 'json')
    >>> request('http://epsg.io/4326.xml', None, 'xml')
    >>> request('https://gitgub.com')
    """
    url = str(url)
    urll = url.lower()
    if urll.startswith("http://"):
        result = request_http(url, data, data_type, headers)
    elif urll.startswith("https://"):
        result = request_https(url, data, data_type, headers)
    elif url.startswith("//"):
        # try https first, then http
        try:
            result = request_https("https://" + url, data, data_type, headers)
        except:
            result = request_http("http://"+ url, data, data_type, headers)
    else:
        raise Exception("Protocol can only be http or https!")

    return result


def epsg(epsgcode, form='esriwkt'):
    """Get spatial reference system by EPSG code as string.
    Queries the http://epsg.io website.
    epsgcode -- European Petrol Survey Group code (http://www.epsg.org/)
    form -- Format to return:
        html : HTML
        wkt : Well Known Text
        esriwkt : Esri Well Known Text
        gml : GML
        xml : XML
        proj4 : Proj4
        js : proj4js
        geoserver : GeoServer
        map : MAPfile
        mapserverpython : MapServer - Python
        mapnik : Mapnik
        sql : PostGIS
    Example:
    >>> srs_str_by_epsg(27700, 'esriwkt')
    """
    srsstr = request('http://epsg.io/%s.%s' % (epsgcode, str(form).lower()))
    return srsstr


def arctype_to_ptype(tp):
    """Convert ArcGIS field type string to Python type.
      tp -- ArcGIS type as string like SHORT|LONG|TEXT|DOUBLE|FLOAT...

    Returns string for GUID, RASTER, BLOB, or other exotic types.

    Example:
    >>> arctype_to_ptype("SHORT") # returns int
    >>> arctype_to_ptype("long") # returns int
    >>> arctype_to_ptype("SmallInteger") # returns int
    >>> arctype_to_ptype("DATE") # returns datetime.datetime
    """
    tp = str(tp).upper().strip()
    o = str
    if tp == "TEXT" or tp == "STRING":
        o = str
    elif tp == "SHORT" or tp == "SMALLINTEGER":
        o = int
    elif tp == "LONG" or tp == "INTEGER":
        o = int
    elif tp == "DATE" or tp == "DATETIME":
        o = datetime.datetime
    elif tp == "FLOAT" or tp == "SINGLE":
        o = float
    elif tp == "DOUBLE":
        o = float
    else:
        o = str
    return o

def project_coordinates(xys, in_sr, out_sr, datum_transformation=None):
    """Project list of coordinate pairs (or triplets).
        xys -- list of coordinate pairs or triplets to project one by one
        in_sr -- input spatial reference, wkid, prj file, etc.
        out_sr -- output spatial reference, wkid, prj file, etc.
        datum_transformation=None -- datum transformation to use
            if in_sr and out_sr are defined on different datums,
            defining appropriate datum_transformation is necessary
            in order to obtain correct results!
            (hint: use arcpy.ListTransformations to list valid transformations)

    Example:
    >>> dtt = 'TM65_To_WGS_1984_2 + OSGB_1936_To_WGS_1984_NGA_7PAR'
    >>> coordinates = [(240600.0, 375800.0), (245900.0, 372200.0)]
    >>> project_coordinates(coordinates, 29902, 27700, dtt)
    """

    if not type(in_sr) is arcpy.SpatialReference:
        in_sr = arcpy.SpatialReference(in_sr)
    if not type(out_sr) is arcpy.SpatialReference:
        out_sr = arcpy.SpatialReference(out_sr)

    xyspr = []
    for xy in xys:
        pt = arcpy.Point(*xy)
        hasz = True if pt.Z is not None else False
        ptgeo = arcpy.PointGeometry(pt, in_sr)
        ptgeopr = ptgeo.projectAs(out_sr, datum_transformation)
        ptpr = ptgeopr.firstPoint
        if hasz:
            xypr = (ptpr.X, ptpr.Y, ptpr.Z)
        else:
            xypr = (ptpr.X, ptpr.Y)
        xyspr.append(xypr)

    return xyspr


class ArcapiError(Exception):
    """A type of exception raised from arcapi module"""
    pass


"""
Aliases
=======
Modified to allow computers without arcpy import arcapi.
That is why instead of just:
search = arcpy.da.SearchCursor
we need:
searcher = getattr(getattr(arcpy, "da", None), "SearchCursor", None)
"""
searcher = getattr(getattr(arcpy, "da", None), "SearchCursor", None)
updater = getattr(getattr(arcpy, "da", None), "UpdateCursor", None)
inserter = getattr(getattr(arcpy, "da", None), "InsertCursor", None)
add_col = getattr(getattr(arcpy, "management", None), "AddField", None)
descr = getattr(arcpy, "Describe", None)
flyr = getattr(getattr(arcpy, "management", None), "MakeFeatureLayer", None)
rlyr = getattr(getattr(arcpy, "management", None), "MakeRasterLayer", None)
tviw = getattr(getattr(arcpy, "management", None), "MakeTableView", None)
tos = to_scratch
wsps = swsp
osj = os.path.join
bname = os.path.basename
dname = os.path.dirname
srs = getattr(arcpy, "SpatialReference", None)


lut_field_types = {
    'Date':'DATE',
    'String':'TEXT',
    'Single':'FLOAT',
    'Double':'DOUBLE',
    'SmallInteger':'SHORT',
    'Integer':'LONG',
    'GUID':'GUID',
    'Raster':'RASTER'
}


def main():
    pass

if __name__ == '__main__':
    main()
