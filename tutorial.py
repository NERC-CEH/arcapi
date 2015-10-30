"""
#-------------------------------------------------------------------------------
# Name:        arcapi_tutorial
# Purpose:     Tutorial for arcapi module.
#
# Author:      Filip Kral
#
# Created:     20/02/2014
# Licence:     LGPL v3
#-------------------------------------------------------------------------------
# This tutorial shows how to use some functions from the arcapi module
# to explore a dataset in a terminal, PyScripter, or what have you.
#-------------------------------------------------------------------------------
"""

# import the usual module(s)
import arcpy, sys, os
# If you don't have arcapi in your path, you can add it like so:
sys.path.insert(0, r'c:\path\to\folder_containig__arcapi_folder')
# import arcapi using the recommended alias
import arcapi as ap


# Set environment settings, at least workspace.
# base.gdb will be created if it doesn't exist.
ap.wsp('c:\\temp\\base.gdb')
# If you are in ArcMap and want to override the
# default scratch workspace too, call e.g.
ap.swsp(ap.wsp())

# We will work with the famous meuse dataset of soil properties from about
# 150 points near river Meuse collected near city Stein in The Netherlands.
# The meuse dataset can be downloaded from the Internet. You can download it
# directly from Python using urllib2 and save it as a text file onto your
# hard drive like so:
url= 'https://raw.github.com/filipkral/meuse/master/meuse.txt'
text =  os.path.join(arcpy.env.scratchFolder, 'meuse.txt')
import urllib2
ur = urllib2.urlopen(url)
with open(text, 'w') as tx:
    tx.write(ur.read())
ur.close()

# We have our data in a text file, which we need to import into ArcGIS native
# format. We strongly recommend Esri File Geodatabase.
# ap has short name tviw for arcpy.management.CreateTableView,
# flyr and rlyr for CreateFeatureLayer and CreateRasterLayer.
tb = ap.tviw(text, "tb")
# check that the names and data types are what you would expect
ap.names(tb)
ap.types(tb)
# or like this:
zip(ap.names(tb), ap.types(tb))

# It is point data so let's convert it to a point feature class.
# Store it as a point feature class called 'dta' in our base.gdb.
fc = ap.to_points(tb, ap.to_scratch('dta'), 'x', 'y', 28992)
tmp = ap.head(fc)
# We don't need the table view of text any more so get rid of it.
ap.dlt(tb)
# And we don't need the text file itself either so get rid of it.
ap.dlt(text)
# Print first 10 records using default settings (columns as rows)
tmp = ap.head(fc)
# now print 5 rows as a formatted table, print '-' for geometries
tmp = ap.head(fc, 5, False, '|',  '-')

# Print some basic statistics for each column.
tmp = ap.summary(fc)
# Force lime, soil, and ffreq to be treated as categorical variables.
tmp = ap.summary(fc, ['lime', 'soil', 'ffreq'], ['CAT', 'CAT', 'CAT'])


# Make a quick map
# If you are in ArcMap's Python window, add fc as a feature layer.
# This will add the layer if your ArcMap's Geoprocessing options
# allow to 'Add results of geoprocessing operations to the display'.
ap.flyr(fc)
# If you are not in ArcMap, you can still plot the feature class:
ap.chart(fc)


# You can plot values in a column once you read its values into Python.
# Let's first find out what unique landuse categories there are in fc:
ap.distinct(fc, 'landuse')
# How many records of each species are there?
x = ap.values(fc, 'landuse')
ap.frequency(x)

# Now plot zinc concentration for landuse 'W'
z = ap.values(fc, 'zinc', '"landuse" = \'W\'', '"OBJECTID" ASC')
ap.plot(z)
# Arcapi now plots histograms too!
ap.hist(z)
# Show scatter plot of zinc against distance from the river
# The 'order by' clause ensures values come in the same order
d = ap.values(fc, 'dist_m', '"landuse" = \'W\'', '"OBJECTID" ASC')
ap.plot(d, z, main='Zinc', xlab='Ditance', ylab='Zn', pch='o', color='k')


# Suppose we want to add full labels indicating landuse at points.
# This can come as a table, json, or other forms. Anyhow, we would
# convert it to a Python dictionary. I simply re-typed help of 'sp':
# http://cran.r-project.org/web/packages/sp/sp.pdf
landuse2luse = {
    'Aa': 'Agriculture/unspecified', 'Ab': 'Agr/sugar beetsm',
    'Ag': 'Agr/small grains', 'Ah': 'Agr/??', 'Am': 'Agr/maize', 'B': 'woods',
    'Bw': 'trees in pasture', 'DEN': '??', 'Fh': 'tall fruit trees',
    'Fl': 'low fruit trees', 'Fw': 'fruit trees in pasture',
    'Ga': 'home gardens', 'SPO': 'sport field', 'STA': 'stable yard',
    'Tv': '??', 'W': 'pasture'
}
# now we need to add a column for these labels
ap.add_col(fc, 'luse', 'TEXT')
# and update the column with landuse dictionary:
# (If you're in ArcMap and fc's attribute table is open,
# you will need to Reload Cache in Table Options.)
ap.update_col_from_dict(fc, landuse2luse, 'luse', 'landuse')

# So why didn't we use table join to do this? You could, especially if you
# have Advanced license so you can use JoinFied_management. With Basic license,
# it is much easier to use ap.update_col_from_dict, which is also pretty
# fast on mederate-sized datasets thanks to the use of an update cursor.

# Finally, make a note about this update to metadata of fc
ap.meta(fc, 'APPEND', abstract='Updated at ' + ap.tstamp())

# To list all functions available in arcapi and their help:
help(ap.arcapi)
