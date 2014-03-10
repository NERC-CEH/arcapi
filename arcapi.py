"""
#-------------------------------------------------------------------------------
# Name:        arcapi
# Purpose:     Convenient API for arcpy
#
# Authors:     Filip Kral, Caleb Mackey
#
# Created:     01/02/2014
# Licence:     LGPL v3
#-------------------------------------------------------------------------------
# Wrapper functions, helper functions, and aliases that make ArcGIS Python
# scripting easier.
#
# Arcapi is a Python module of functions that simplify common tasks, are easy on the
# programmer, and make prototyping faster. However, Arcapi is intended for skilled
# Python coders with solid experience with ArcPy and ArcGIS.
#
# While the code should work with all types of workspaces, ESRI File Geodatabase
# was adopted as primary format. Most functions were designed for and tested
# with plain tables and feature classes with basic field types like SHORT, LONG,
# TEXT, DOUBLE, FLOAT. If you work with feature datasets, topologies,
# relationship classes, annotation feature classes, TINs, BLOBs, and other
# complex objects, you will likely need to use core arcpy functions.
#
# Exception handling
# ------------------
# Because arcapi functions are generally wrappers around arcpy functions, input
# checking and exception handling is used sporadically. This allows invalid
# input to reach core (arcpy etc.) functions and raised errors propagate back
# the calling functions.
# In rare cases, to distinguish Exceptions raised in arcapi module, an Exception
# of type arcapi.ArcapiError is raised.
#
# ArcGIS Extensions modules
# -------------------------
# Some functions use extensions modules (e.g. Spatial Analyst's arcpy.sa).
# Bodies of these functions are wrapped in try-except(ImportError) statements.
# The extension-dependent functions will return string if the extensions is not
# installed, but rest of arcapi will still work normally.
#
#-------------------------------------------------------------------------------
"""

import os
import sys
import time
import arcpy


def version():
    """Return a 3-tuple indicating version of this module."""
    return (0,1,1)

def names(x, filterer = None):
    """Return list of column names of a table.

    Required:
    x -- input table or table view

    Optional:
    filterer -- function, only fields where filterer returns True are listed

    Example:
    >>> names('c:\\foo\\bar.shp', lambda f: f.name.startswith('eggs'))
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
    >>> types('c:\\foo\\bar.shp', lambda f: f.name.startswith('eggs'))
    """
    flds = arcpy.ListFields(x)
    if filterer is None: filterer = lambda a: True
    return [f.type for f in flds if filterer(f)]

def nrow(x):
    """Return number of rows in a table as integer.

    Required:
    x -- input table or table view

    Example:
    >>> nrow('c:\\foo\\bar.shp')
    """
    return int(arcpy.GetCount_management(x).getOutput(0))

def values(tbl, col, w='', o=None):
    """Return a list of all values in column col in table tbl.

    Required:
    tbl -- input table or table view
    col -- input column name as string

    Optional:
    w -- where clause
    o -- order by clause like '"OBJECTID" ASC, "Shape_Area" DESC'

    Example:
    >>> values('c:\\foo\\bar.shp', "Shape_Lenght")
    >>> values('c:\\foo\\bar.shp', "SHAPE@XY")
    """
    ret = []
    if o is not None:
        o = 'ORDER BY ' + str(o)
    with arcpy.da.SearchCursor(tbl, [col], where_clause = w, sql_clause=(None, o)) as sc:
        for row in sc:
            ret.append(row[0])
    return ret

def frequency(x):
    """Return a dict of counts of each value in iterable x.

    Values in x must be hashable in order to work as dictionary keys.

    Required:
    x -- input iterable object like list or tuple

    Example:
    >>> frequency([1,1,2,3,4,4,4]) # {1: 2, 2: 1, 3: 1, 4: 3}
    >>> frequency(values('c:\\foo\\bar.shp', 'STATE'))
    """
    x.sort()
    fq = {}
    for i in x:
        if fq.has_key(i):
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
    >>> distinct('c:\\foo\\bar.shp', "CATEGORY")
    >>> distinct('c:\\foo\\bar.shp', "SHAPE@XY")
    """
    return list(set(values(tbl, col, w)))  # the where clause parameter was not applied here


def print_tuples(x, delim=" ", tbl=None, geoms=None, fillchar=" ",  padding=1, verbose=True, returnit = False):
    """Print and/or return list of tuples formatted as a table.

    Intended for quick printing of lists of tuples in the terminal.
    Returns None or the formatted table depending on value of returnit.

    Required:
    x -- input list of tuples to print (can be tuple of tuples, list of lists).

    Optional:
    delim -- delimiter to use between columns
    tbl -- table to take column headings from (default is None)
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
        for f in arcpy.ListFields(tbl):
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
    if verbose: print hdr # print header
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
            print rw # print row
        sbuilder.append(rw)

    ret = "\n".join(sbuilder) if returnit else None
    return ret

def head(tbl, n=10, t=True, delimiter="; ", geoms = None, w = "", verbose=True):
    """Return top rows of table tbl.

    Returns a list where the first element is a list of tuples representing
    first n rows of table tbl, second element is a dictionary like:
    {i: {"name":f.name, "values":[1,2,3,4 ...]}} for each field index i.

    Optional:
    n -- number of rows to read, default is 10
    t -- if True (default), columns are printed as rows, otherwise as columns
    delimiter -- string to be used to separate values (if t is True)
    geoms -- if None (default), print geometries 'as is', else as str(geom).
    w, where clause to limit selection from tbl
    verbose -- suppress printing if False, default is True

    Example:
    >>> tmp = head('c:\\foo\\bar.shp', 5, True, "|", " ")
    """
    flds = arcpy.ListFields(arcpy.Describe(tbl).catalogPath)
    fs = {}
    nflds = len(flds)
    fieldnames = []
    for i in range(nflds):
        f = flds[i]
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
                print toprint
    else:
        if verbose:
            print_tuples(hd, delim=delimiter, tbl=tbl, geoms=geoms, returnit=False)
    return [hd, fs]

def chart(x, out_file='c:\\temp\\chart.jpg', texts={}, template=None, resolution=95, openit=True):
    """Create and open a map (JPG) showing x and return path to the figure path.

    Required:
    x -- input feature class, raster dataset, or a layer

    Optional:
    out_file -- path to output jpeg file, default is 'c:\\temp\\chart.jpg'
    texts -- dict of strings to include in text elements on the map (by name)
    template -- path to the .mxd to be used, default None points to mxd with
        a single text element called "txt"
    resolution -- output resolution in DPI (dots per inch)
    openit -- if True (default), exported jpg is opened in a webbrowser

    Example:
    >>> chart('c:\\foo\\bar.shp')
    >>> chart('c:\\foo\\bar.shp', texts = {'txt': 'A Map'}, resolution = 300)
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
        except Exception, e:
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

def plot(x, y=None, out_file="c:\\temp\\plot.png", main="Arcapi Plot", xlab="X", ylab="Y", pch="+", color="r", openit=True):
    """
    Create and display a plot (PNG) showing x (and y).

    Uses matplotlib.pyplot.scatter.

    Required:
    x -- values to plot on x axis

    Optional:
    y -- values to plot on y axis or None (default), then x will be plotted
        on y axis, using index for x axis.
    out_file -- path to output file, default is 'c:\\temp\\plot.png'
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
    >>> x = xrange(20)
    >>> plot(x)
    >>> plot(x, out_file='c:\\temp\\pic.png')
    >>> y = xrange(50,70)
    >>> plot(x, y, 'c:\\temp\\pic.png', 'Main', 'X [m]', 'Y [m]', 'o', 'k')
    """
    import re
    if not re.findall(".png", out_file, flags=re.IGNORECASE): out_file += ".png"

    if y is None:
        y = x
        len(x)
        x = xrange(len(y))
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

def hist(x, out_file='c:\\temp\\hist.png', openit=True, **args):
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
    out_file -- path to output file, default is 'c:\\temp\\hist.png'
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
    pars = dict([(k,v) for k,v in args.iteritems() if k not in extras])

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

def bars(x, out_file='c:\\temp\\hist.png', openit=True, **args):
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
    out_file -- path to output file, default is 'c:\\temp\\hist.png'
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
    >>> ot = 'c:\\temp\\foo.dbf'
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
        if len(f) > 2:
            flength = int(f[2]) if str(f[2]).isdigit() else '#'
        arcpy.AddField_management(out_tbl, fname, ftype, "#", "#", flength)
    # rewrite all tuples
    fields = [c[0] for c in cols]

    with arcpy.da.InsertCursor(out_tbl, fields) as ic:
        for rw in x:
            if doReplace:
                rw = list(rw)
                if i in replaceNumbers:
                    rw[i] = nullNumber
                if i in replacesText:
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
        print i
        j += 1
        if j == n: break
    return

def meta(datasource, mode="PREPEND", **args):
    """Update metadata of ArcGIS Feature Class, Raster Dataset, Table, etc.

    The following entries (XML elements) can be changed:
    Title ("dataIdInfo/idCitation/resTitle")
    Purpose ("dataIdInfo/idPurp")
    Abstract ("dataIdInfo/idAbs")

    This function exports metadata of the datasource to XML file using template
    Metadata\Stylesheets\gpTools\exact copy of.xslt from ArcGIS installation
    directory. Then it loads the exported XML file into memory using Pythons
    xml.etree.ElementTree, modifies supported elements, writes a new XML file,
    and imports this new XML file as metadata to the datasource.


    Required:
    datasource -- path to the data source to update metadata for
    mode -- {PREPEND|APPEND|OVERWRITE}, indicates whether new entries will be
        prepended or appended to existing entries, or whether new entries will
        overwrite existing entries. Case insensitive.
    **args, keyword arguments of type string indicating what entries to update:
        title, string to use in Title
        purpose, string to use in Purpose
        abstract, string to use in Abstract

    Example:
    >>> fc = 'c:\\foo\\bar.shp'
    >>> meta(fc, 'OVERWRITE', title="Bar") # updates title
    >>> meta(fc, 'append', purpose='example', abstract='Column Spam means eggs')
    """
    import xml.etree.ElementTree as ET
    xslt = None # could be exposed as a parameter to specify alternative xslt file
    tmpmetadatafile = arcpy.CreateScratchName("tmpmetadatafile", workspace=arcpy.env.scratchFolder)

    # checks
    if xslt is None: xslt = os.path.join(arcpy.GetInstallInfo()['InstallDir'], 'Metadata\Stylesheets\gpTools\exact copy of.xslt')
    if not os.path.isfile(xslt): raise ArcapiError("Cannot find xslt file " + str(xslt))
    mode = mode.upper()

    # work
    r = arcpy.XSLTransform_conversion(datasource, xslt, tmpmetadatafile)
    tmpmetadatafile = r.getOutput(0)
    with file(tmpmetadatafile, "r") as f:
        mf = f.read()
    tree = ET.fromstring(mf)

    # get what user wants to update
    entries = {}
    if args.get("title", None) is not None: entries.update({"dataIdInfo/idCitation/resTitle": args.get("title")})
    if args.get("purpose", None) is not None: entries.update({"dataIdInfo/idPurp": args.get("purpose")})
    if args.get("abstract", None) is not None: entries.update({"dataIdInfo/idAbs": args.get("abstract")})

    # update entries
    for p,t in entries.iteritems():
        el = tree.find(p)
        if el is None:
            arcpy.AddWarning("Element " + str(p) + " not found in metadata, creating it from scratch.")
            pparent = "/".join(p.split("/")[:-1])
            parent = tree.find(pparent)
            if parent is None:
                raise ArcapiError("Could not found %s as parent of %s in medatata for %s" % (pparent, p, str(datasource)))
            subel = ET.SubElement(parent, p.split("/")[-1])
            subel.text = ''
            el = subel
            del subel
        else:
            pre, mid, post = ("", "", "")
            if mode != "OVERWRITE":
                mid = '' if el.text is None else el.text # remember existing content if not overwrite
                joiner = "&lt;br/&gt;"
            else:
                mid = str('' if t is None else t)
                joiner = ''
            if mode == "APPEND": post = str('' if t is None else t)
            if mode == "PREPEND": pre = str('' if t is None else t)
            el.text = joiner.join((pre, mid, post))

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

    return r.getOutput(0)

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
    >>> msg('foo', '%H%M%S', True, 'c:\\temp\\log.txt') # P:204531: foo
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
            print str(str(en) + " ").ljust(30, ".") + ": " + str(env)
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
    >>> cleanup(['c:\\foo\\bar.shp', 'lyr', 'c:\\foo\\eggs.tif'])
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
    >>> t = 'c:\\foo\\bar.shp'
    >>> o = 'c:\\foo\\bar_pts.shp'
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
    >>> fc = 'c:\\foo\\bar.shp'
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
    >>> to_scratch('foo', 0) # '...\\scratch.gdb\\foo'
    >>> to_scratch('foo', 1) # '...\\scratch.gdb\\foo0'
    >>> to_scratch('foo.shp', 0) # '...\\scratch.gdb\\foo_shp'
    >>> to_scratch('foo.shp', 1) # '...\\scratch.gdb\\foo_shp0'
    >>> tos('foo', 0) # '...\\scratch.gdb\\foo'
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
    >>> wsp('c:\\temp') # sets ev.workspace = 'c:\\temp', returns 'c:\\temp'
    >>> wsp() # now returns 'c:\\temp'
    """
    if ws is None:
        ws = arcpy.env.workspace
        if ws in None:
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
    >>> swsp('c:\\temp') # sets ev.scratchWorkspace = 'c:\\temp', returns 'c:\\temp'
    >>> swsp() # now returns 'c:\\temp'
    """
    if ws is None:
        ws = arcpy.env.scratchWorkspace
        if ws in None:
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
    >>> summary('c:\\foo\\bar.shp')
    >>> summary('c:\\foo\\bar.shp', ['smap', 'eggs'], ['NUM', 'CAT'])
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
            print fulline
            print str(tbl)
            print str(arcpy.Describe(tbl).catalogPath)
            print fulline
            for j,i in stats.iteritems():
                mode = modes[j]
                print 'COLUMN'.ljust(width) + ": " + str(i.get('col', None))
                print 'type'.ljust(width) + ": "+ str(i.get('type', None))
                if mode == "NUM":
                    print 'min'.ljust(width) + ": " + str(i.get('min', None))
                    print 'max'.ljust(width) + ": " + str(i.get('max', None))
                    print 'mean'.ljust(width) + ": " + str(i.get('mean', None))
                    print 'sum'.ljust(width) + ": " + str(i.get('sum', None))
                    print 'n'.ljust(width) + ": " + str(i.get('n', None))
                    print 'na'.ljust(width) + ": " + str(i.get('na', None))
                elif mode == "CAT":
                    cats = i["cats"]
                    if len(cats) > 0:
                        print "CATEGORIES:"
                        catable = sorted(zip(cats.keys(), cats.values()), key = lambda a: a[1], reverse = True)
                        print_tuples(catable)
                else:
                    pass
                print fulline
    return stats

def remap_sa(st, stop, step, n=1):
    '''
    Creates a spatial analyst format reclassify remap range (list)
    [[start value, end value, new value]...]

    >>> # ex: make range groups from 50 - 80
    >>> remap_sa(50, 80, 10)
    [[50, 60, 1], [60, 70, 2], [70, 80, 3]]

    st:   start value (int)
    stop: stop value (int)
    step: step value for range (int)
    n:    new value interval, default is 1 (int)
    '''

    tups = [[i,i+step] for i in range(st, stop, step)]
    return [[t] + [(tups.index(t)+1)*n] for t in tups]


def remap_3d(st, stop, step, n=1):
    '''
    Creates a 3D analyst format reclassify remap range (str)
    "start end new;..."

    >>> # ex: make range groups from 50 - 80
    >>> remap_3d(50, 80, 10)
    '50 60 1;60 70 2;70 80 3'

    st:   start value (int)
    stop: stop value (int)
    step: step value for range (int)
    n:    new value interval, default is 1 (int)
    '''

    tups = [[i,i+step] for i in range(st, stop, step)]
    return ';'.join(' '.join([str(i) for i in t] + [str((tups.index(t)+1)*n)]) for t in tups)

def find(pattern, path, sub_dirs=True):
    import fnmatch
    '''
    Finds files matching a wild card pattern

    >>> # Example: find SQL databases (.mdf files)
    >>> find('*.mdf', r'\\ArcServer1\SDE')
    \\arcserver1\SDE\ALBT\Albertville.mdf
    \\arcserver1\SDE\ARLI\Arlington.mdf
    \\arcserver1\SDE\BELL\BellePlaine.mdf
    \\arcserver1\SDE\BGLK\BigLake.mdf


    pattern: wild card search (str)
    path:    root directory to search
    sub_dirs: option to search through all sub directories, default is True (bool)
    '''

    theFiles = []
    for path, dirs, files in os.walk(path):
        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                theFiles.append(os.path.abspath(os.path.join(path, filename)))
        if sub_dirs in [False, 'false', 0]:
            break
    return theFiles

def convertIntegerToFloat(raster, out_raster, decimals):
    '''
    Converts an Integer Raster to a Float Raster
    *** Requires spatial analyst extension ***

    Example:   for a cell with a value of 45750, using this tool with 3
    decimal places will give this cell a value of 45.750

    raster:     input integer raster
    out_raster: new float raster
    decimals:   number of places to to move decimal for each cell
    '''
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
        arcpy.AddMessage('Created: %s' %out_raster)
        arcpy.CheckInExtension('Spatial')
        return out_raster
    except ImportError:
        return 'Module arcpy.sa not found.'

def fillNoDataValues(in_raster):
    '''
    Fills "NoData" cells with mean values from focal statistics.
    *** Requires spatial analyst extension ***

    in_raster: input raster
    '''
    try:
        import arcpy.sa as sa
        # Make Copy of Raster
        _dir, name = os.path.split(in_raster)
        temp = os.path.join(_dir, 'rast_copyxxx')
        if arcpy.Exists(temp):
            arcpy.Delete_management(temp)
        arcpy.CopyRaster_management(in_raster, temp)

        # Fill NoData
        arcpy.CheckOutExtension('Spatial')
        filled = sa.Con(sa.IsNull(temp),sa.FocalStatistics(temp,sa.NbrRectangle(3,3),'MEAN'),temp)
        filled_rst = os.path.join(_dir, 'filled_rstxxx')
        filled.save(filled_rst)
        arcpy.BuildPyramids_management(filled_rst)
        arcpy.CheckInExtension('Spatial')

        # Delete original and replace
        if arcpy.Exists(in_raster):
            arcpy.Delete_management(in_raster)
            arcpy.Rename_management(filled_rst, os.path.join(_dir, name))
            arcpy.Delete_management(temp)
        arcpy.AddMessage('Filled NoData Cells in: %s' %in_raster)
        return in_raster
    except ImportError:
        return 'Module arcpy.sa not found.'

def convertMetersToFeet(in_dem, out_raster):
    '''
    Converts DEM z units that are in meters to feet
    *** Requires spatial analyst extension ***

    in_dem: input dem
    out_raster: new raster with z values as feet
    '''
    try:
        import arcpy.sa as sa
        arcpy.CheckOutExtension('Spatial')
        out = sa.Float(sa.Times(arcpy.Raster(in_dem), 3.28084))
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
    ***Can be used only in ArcMap session***
    """
    return arcpy.mapping.MapDocument("CURRENT")

class ArcapiError(Exception):
    """A type of exception raised from arcapi module"""
    pass


"""
Aliases
=======
"""
searcher = arcpy.da.SearchCursor
updater = arcpy.da.UpdateCursor
inserter = arcpy.da.InsertCursor
add_col = arcpy.management.AddField
descr = arcpy.Describe
flyr = arcpy.management.MakeFeatureLayer
rlyr = arcpy.management.MakeRasterLayer
tviw = arcpy.management.MakeTableView
tos = to_scratch
wsps = swsp


def main():
    pass

if __name__ == '__main__':
    main()
