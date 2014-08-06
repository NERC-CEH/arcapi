"""
#-------------------------------------------------------------------------------
# Name:        arcapi.arrest
# Purpose:     ArcGIS REST API Python library
#
# Authors:     Filip Kral
#
# Created:     04/08/2014
# Licence:     LGPL v3
#-------------------------------------------------------------------------------
#
# This module allows you to interact with ArcGIS for Server REST end points
# from Python in a more natural way than just referencing URLs.
#
# The module was developed in Python 2.7 with no dependencies; not even arcpy!
#
#
# LIMITATIONS
# -----------
#
# Some REST end points were omitted because the demand to access them from
# Python has been low. In most cases, using such end points from Python
# would be awkward anyway. However, additional end points can be implemented
# if users request it and provide use cases.
#
# All arrest classes are subclasses of ArrestObject or ArrestService.
# Classes ArrestObject and ArrestService are generic classes that can be
# used to access any ArcGIS REST end point, for example an end point in
# future ArcGIS versions, for which no reciprocal arrest class exists.
#
# Be aware that services have limits on how much data can be send back.
# For example, how many features to return, or maximum size of a raster image.
# This module does not go around these limitations, you have to take care of it.
# For example, if you query world cities with a where clause "COUNTRY = 'US'"
# you may not get back all cities in the US if there are more cities in the US
# than the maximum number of features the service is allowed to send back.
# The limits are managed by server administrators.
#
#
# EXAMPLES
# --------
#
# For example usage of this library, see bottom of this file.
#
# For ArcGIS REST API hierarchy and documentation see:
# http://resources.arcgis.com/en/help/rest/apiref/res-ops.html
#
#
# TODO
# ----
# - Ensure that URLs are properly quoted and unqoted when needed.
# - Implement loging in to be able to use secured services
# - Implement class for manipulating features (ArrestFeatures ? GeoJesPy?
#
#-------------------------------------------------------------------------------
"""

import urllib
import urllib2
import time


def request(url, data=None, data_type='text', headers={}):
    """
    This is the request function from arcapi.
    When you are done with development, make use of the arcapi.request
    """
    import urllib2
    import urllib
    import json

    result = ''
    callback = 'callmeback' # may not be used

    # prepare data
    data_type = str(data_type).lower()
    if data_type in ('jsonp', 'pjson'):
        if data is None:
            data = {}
        data['callback'] = callback

    if data is not None:
         data = urllib.urlencode(data)

    # make the request
    rq = urllib2.Request(url, data, headers)
    re = urllib2.urlopen(rq)
    rs = re.read()

    # handle result
    if data_type in ('json', 'jsonp', 'pjson'):
        rs = rs.strip()

        # strip callback function if present
        if rs.startswith(callback + '('):
            rs = rs.lstrip(callback + '(')
            rs = rs[:rs.rfind(')')]

        result = json.loads(rs)
    elif data_type == 'xml':
        from xml.etree import ElementTree as ET
        rs = rs.strip()
        result = ET.fromstring(rs)
    elif data_type == 'text':
        result = rs
    else:
        raise Exception('Unsupported data_type %s ' % data_type)

    return result


def getjs(u, d=None):
    """Short hand for request(u, {'f':'pjson'}, 'json')
        u -- url
        d -- optional data dictionary to be added to {'f':'pjson'}
    """
    dt = {'f': 'pjson'}
    if d is not None:
        dt.update(d)
    r = request(u, dt, 'json')
    return r


def ujoin(*u):
    """Return pieces joined with '/'
    All but the first argument are urllib.quote'ed."""
    first =str(u[0]).strip()
    other = [urllib.quote(str(s).strip()) for s in u[1:]]
    return "/".join([first] + other)


def enum(**enums):
    """Create an enumerator.
    Example:
    >>> securityLevels = enum(green=0, amber=1, red=2)
    >>> securityLevels.green # returns 0
    >>> clearanceLevel = enum(A='admin', B='edit', C='read', D='reject')
    >>> clearanceLevel.A # returns 'admin'
    """
    return type('Enum', (), enums)


"""Enumerator of possible spatial relationships"""
enumEsriSpatialRel = enum(
    esriSpatialRelIntersects='esriSpatialRelIntersects',
    esriSpatialRelContains='esriSpatialRelContains',
    esriSpatialRelCrosses='esriSpatialRelCrosses',
    esriSpatialRelEnvelopeIntersects='esriSpatialRelEnvelopeIntersects',
    esriSpatialRelIndexIntersects='esriSpatialRelIndexIntersects',
    esriSpatialRelOverlaps='esriSpatialRelOverlaps',
    esriSpatialRelTouches='esriSpatialRelTouches',
    esriSpatialRelWithin='esriSpatialRelWithin',
    esriSpatialRelRelation='esriSpatialRelRelation'
)


"""Enumerator of possible geometry types"""
enumEsriGeometryType = enum(
    esriGeometryPoint='esriGeometryPoint',
    esriGeometryMultipoint='esriGeometryMultipoint',
    esriGeometryPolyline='esriGeometryPolyline',
    esriGeometryPolygon='esriGeometryPolygon',
    esriGeometryEnvelope='esriGeometryEnvelope'
)

"""Enumerator of possible geometry relations"""
enumEsriGeometryRelation = enum(
    esriGeometryRelationCross='esriGeometryRelationCross',
    esriGeometryRelationDisjoint='esriGeometryRelationDisjoint',
    esriGeometryRelationIn='esriGeometryRelationIn',
    esriGeometryRelationInteriorIntersection='esriGeometryRelationInteriorIntersection',
    esriGeometryRelationIntersection='esriGeometryRelationIntersection',
    esriGeometryRelationLineCoincidence='esriGeometryRelationLineCoincidence',
    esriGeometryRelationLineTouch='esriGeometryRelationLineTouch',
    esriGeometryRelationOverlap='esriGeometryRelationOverlap',
    esriGeometryRelationPointTouch='esriGeometryRelationPointTouch',
    esriGeometryRelationTouch='esriGeometryRelationTouch',
    esriGeometryRelationWithin='esriGeometryRelationWithin',
    esriGeometryRelationRelation='esriGeometryRelationRelation'
)


class ArrestObject(object):
    """Generic object for arrest module"""

    def __init__(self, url):
        """Create from url"""
        self.url = url
        dd = getjs(url)
        self.ddict = dd

    def __str__(self):
        return str(self.ddict)

    __repr__ = __str__

    def __getattr__(self, key):
        # override __getattr__ to return content of the data dictionary ddict
        attr = self.ddict.get(key, None)
        return attr


class ArrestCatalog(ArrestObject):
    """http://resources.arcgis.com/en/help/rest/apiref/catalog.html"""

    def get_folder_by_name(self, name):
        """Return subfolder of this catalog as a ArrestCatalog object by name"""
        u = ujoin(self.url, name)
        folder = ArrestCatalog(u)
        return folder

    def get_folder_by_index(self, i):
        """Return subfolder of this catalog as ArrestCatalog object by index"""
        folder = self.get_folder_by_name(self.folders[i])
        return folder

    def get_folders(self):
        """Return subfolders of this catalog as a list of ArrestCatalog objects
        """
        folders = []
        folderitems = self.ddict.get('folders', [])
        for fi in folderitems:
            folder = self.get_folder_by_name(fi)
            folders.append(folder)
        return folders

    def get_service_by_name(self, name):
        """Return service from this catalog by name"""
        service = None
        serviceitems = self.ddict.get('services', [])
        for si in serviceitems:
            sname = si["name"]
            if sname == name:
                stype = si["type"]
                u = ujoin(self.url, sname, stype)
                sclass = lut_servicetype_by_typestr.get(stype, None)
                if sclass is None:
                    raise Exception('Service type %s not supported' % stype)
                service = sclass(u)
        if service is None:
            raise Exception("Service %s not found." % name)
        else:
            return service

    def get_service_by_index(self, i):
        """Return service from this catalog by index"""
        service = None
        serviceitems = self.ddict.get('services', [])
        si = serviceitems[i]
        sname = si["name"]
        stype = si["type"]
        u = ujoin(self.url, sname, stype)
        sclass = lut_servicetype_by_typestr.get(stype, None)
        if sclass is None:
            raise Exception('Service type %s not supported' % stype)
        service = sclass(u)
        return service

    def get_services(self):
        """Return list of services from this catalog"""
        services = []
        serviceitems = self.ddict.get('services', [])
        for si in serviceitems:
            sname = si["name"]
            stype = si["type"]
            u = ujoin(self.url, sname, stype)
            sclass = lut_servicetype_by_typestr.get(stype, None)
            if sclass is None:
                raise Exception('Service type %s not supported' % stype)
            service = sclass(u)
            services.append(service)
        return services


class ArrestService(ArrestObject):
    """Generic parent class for ArcGIS REST API service"""

    def opreation(self, operation, **args):
        """Generic interface to call an operation of this service.

        Returns the result of the operation as a json dictionary.

        You must know what operations the service provides and what
        arguments to specify for them. This method is used to execute
        operations in subclasses of ArrestService.

        operation -- name of the operation provided by the service
        **args -- keyword arguments for the operation
        """
        u = ujoin(self.url, operation.lower())
        return getjs(u, args)


class ArrestLayer(ArrestObject):
    """Layer
    We don't make distinction between mapping layer, feature, and image layer,
    Basically only query operation has been implemented.
    """

    def get_field_names(self):
        return [i["name"] for i in self.fields]

    def get_field_by_name(self, name):
        """Return field by name as dict, None if field name not found"""
        field = None
        flist = [i for i in self.fields if i["name"] == name]
        if flist:
            field = flist[0]
        return field

    def get_field_by_alias(self, alias):
        """Return field by name as dict, None if field name not found"""
        field = None
        flist = [i for i in self.fields if i["alias"] == alias]
        if flist:
            field = flist[0]
        return field

    def get_parent_layer(self):
        """Return parent layer as ArrestLayer, None if no parent layer found"""
        parent_lr = self.parentLayer
        if parent_lr is not None:
            i = parent_lr["id"]
            u = ujoin(self.url[:self.url.rstrip('/').rfind('/')], i)
            parent_lr = ArrestLayer(u)
        return parent_lr

    def query(self, **args):
        """Raw interface for the query operation.
        To construct args, see:
        http://resources.arcgis.com/en/help/rest/apiref/query.html
        """
        u = ujoin(self.url, 'query')
        return getjs(u, args)

    def query_hint(self,
        text='', inSR='', relationParam='', objectIds='', where='', time='',
        returnCountOnly=False, returnIdsOnly=False, returnGeometry=True,
        maxAllowableOffset='', outSR='', outFields='*', **args):
        """Programmer friendly interface for the query operation. At least one:
        text -- text to search for in the primary display field, default ''
            for example 'US', 'London', ...
        geometry -- Input geometry for spatial filtering as ESRI REST API json
         or some simplified format e.g.:
         geometry=-100,35,-99,36 # envelope
         geometry=-101.0,32.1 # point
        geometryType -- Input geometry type. Default: esriGeometryEnvelope;
         esriGeometryPoint | esriGeometryMultipoint | esriGeometryPolyline |
         esriGeometryPolygon | esriGeometryEnvelope
        inSR -- spatial reference for input geometry, e.g. {"wkid": 4326}
        spatialRel -- Spatial relationship of input geometry and queried
        features, default is intersect (esriSpatialRelIntersects).
         One of enumEsriSpatialRel:
         esriSpatialRelIntersects | esriSpatialRelContains |
         esriSpatialRelCrosses | esriSpatialRelEnvelopeIntersects |
         esriSpatialRelIndexIntersects | esriSpatialRelOverlaps |
         esriSpatialRelTouches | esriSpatialRelWithin |
         esriSpatialRelRelation
        relationParam -- Spatial relate function, see help. Default is ''.
        objectIds -- comma separated list of object IDs of features to get
        where -- where clause, e.g.: "VALUE > 100 AND COUNTY = 'Orange'"
        time -- The time instant or extent to query, 'null' is infinity. e.g.:
         # (1 Jan 2008 00:00:00 GMT):
         time=1199145600000
         # (1 Jan 2008 00:00:00 GMT to 1 Jan 2009 00:00:00 GMT):
         time=1199145600000, 1230768000000
        returnCountOnly -- True|False(default)
        returnIdsOnly -- True|False(default)
        returnGeometry -- True(default)|False
        maxAllowableOffset -- number of outSR units to be used for
         generalization of returned geometry. e.g. 2. Default is '' (i.e. 0).
        outSR -- output spatial reference, default is native to the service,
         e.g. {"wkid": 4326} or other allowed representation by REST API.
        outFields -- Comma separated list of fields to return, default '*'

        If you are using IDE with intellisense, this function may help you
        construct the query. Otherwise you can always use the raw .query method.

        Named parameters are provided for ArcGIS for Server 10.0,
        extra parameters for later versions can be supplied as other keyword
        arguments as described in help:
        http://resources.arcgis.com/en/help/rest/apiref/index.html?fsfeature.html

        Example:
        >>> url = 'http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/Demographics/ESRI_Census_USA/MapServer/0'
        >>> lr = ArrestLayer(url)
        >>> ftrs = lr.query(where="HOUSEHOLDS = 1", outFields="*")
        >>> ftrs = lr.query(geometry="-87,32,-88,33", outFields="*")
        """
        return self.query(args)

    def query_where(self, where, outFields='*', **args):
        """Simplified interface for the query operation.
            where -- where clause, e.g.: "KMSQ < 100 AND COUNTY = 'Orange'"
            outFields -- comma separated list of fields to select, default '*'
            Other arguments can be passed as keywords.
        """
        pars = {"where": where, "outFields": outFields}
        pars.update(args)
        return self.query(**pars)

class ArrestTable(ArrestLayer):
    """Tables are defined as types of layers here.
    (although... should it be the other way around?)
    """
    pass

class ArrestMapService(ArrestService):
    """MapServer

    Some REST end points of MapService are not exposed because
    they would be of limited use: Map Tile, WMTS, and KML Image.
    """

    def get_layer_names(self):
        """Return list of layer names"""
        return [i["name"] for i in self.layers]

    def get_table_names(self):
        """Return list of table names"""
        return [i["name"] for i in self.tables]

    def get_layer_by_id(self, i):
        """Return ArrestLayer object by layer id"""
        u = ujoin(self.url, i)
        lr = ArrestLayer(u)
        return lr

    def get_layer_by_name(self, name):
        """Return ArrestLayer object by layer name, None if not found"""
        lr = None
        for li in self.layers:
            if li["name"] == str(name):
                lr = self.get_layer_by_id(li["id"])
        return lr

    def get_table_by_id(self, i):
        """Return ArrestLayer object by table id"""
        u = ujoin(self.url, i)
        lr = ArrestTable(u)
        return lr

    def get_table_by_name(self, name):
        """Return ArrestLayer object by table name, None if not found"""
        tb = None
        for ti in self.tables:
            if ti["name"] == str(name):
                tb = self.get_table_by_id(ti["id"])
        return tb

    def get_layers(self, **args):
        """Return layers in this service as a list of ArrestLayer objects
        Keyword arguments may contain:
            parentLayerId -- only layers with this parent layer id will be
                returned; top level layers have parentLayerId = -1
        """
        parent_lr_id = args.get('parentLayerId', None)
        lrs = []
        for i in self.layers:
            if parent_lr_id is None:
                lr = ArrestLayer(ujoin(self.url, i["id"]))
                lrs.append(lr)
            else:
                if i.get("parentLayerId", None) == parent_lr_id:
                    lr = ArrestLayer(ujoin(self.url, i["id"]))
                    lrs.append(lr)
        return lrs

    def get_tables(self, **args):
        """Return tables in this service as a list of ArrestTable objects"""
        tbs = []
        for i in self.tables:
                tb = ArrestLayer(ujoin(self.url, i["id"]))
                tbs.append(tb)
        return tbs

    def export(self, **args):
        """Raw interface for the export operation
        http://resources.arcgis.com/en/help/rest/apiref/export.html
        """
        u = ujoin(self.url, 'export')
        return getjs(u, args)
        # TODO: create export_assist ?

    def identify(self, **args):
        """Raw interface for the identify operation
        http://resources.arcgis.com/en/help/rest/apiref/identify.html
        """
        u = ujoin(self.url, 'identify')
        return getjs(u, args)
        # TODO: create identify_assist ?

    def find(self, **args):
        """Raw interface for the find operation
        http://resources.arcgis.com/en/help/rest/apiref/find.html
        """
        u = ujoin(self.url, 'find')
        return getjs(u, args)
        # TODO: create find_assist ?


class ArrestFeatureService(ArrestMapService): # is type of Map Services here
    """FeatureServer
    Feature Services are currently treated as Map Services
    and only the query operation is allowed.
    This library makes no distinction between Layer and Feature Layer.
    """

class ArrestGeocodeService(ArrestService):
    """GeocodeServer
    Each GeocodeServer may have different requeriements on how the input should
    be structured. Therefore, no helper methods have been implemented here.
    Use the inherited .operation() method with servers you are familiar with
    to run findAddressCandidates, reverseGeocode, geocodeAddresses operations.
    """

class ArrestResult(ArrestObject):
    """ArcGIS for Server Geoprocessing Result"""

class ArrestJob(ArrestObject):
    """Geoprocessing Job to use with asynchronous tasks.

    Note that if you have arcpy, another way to use geoprocessing tasks from
    ArcGIS for Server is to add the service as a toolbox and use tasks tools.
    Search Esri help for "Using a geoprocessing service in Python scripts"
    and see help for arcpy.AddToolbox and arcpy.ImportToolbox.
    """

    _finished = ("esriJobSucceeded", "esriJobFailed", "esriJobTimedOut",
            "esriJobCancelled", "esriJobDeleted")

    _unfinished = ("esriJobNew","esriJobSubmitted","esriJobWaiting",
            "esriJobExecuting","esriJobCancelling","esriJobDeleting")

    def update(self):
        """Query the server for a new update on this job"""
        self.ddict = getjs(self.url)

    def get_result_names(self):
        """Return list of result names, None if job has not succeeded (yet)."""
        if self.results is None:
            details = (self.jobId, self.jobStatus)
            raise Exception("Results for job %s:%s not available" % details)
        else:
            return self.results.keys()

    def get_result_by_name(self, name):
        """Return result as ArrestResult object"""
        name = str(name)
        details = (self.jobId, self.jobStatus, name)
        if self.results is None:
            raise Exception("Results for job %s:%s not available" % details[0:2])
        else:
            if name not in self.results:
                raise Exception("Job %s:%s has no result %s" % details)
            else:
                urlpart = self.results[name]["paramUrl"]
                u = ujoin(self.url, urlpart)
                return ArrestResult(u)

    def get_results(self):
        """Return dict of all results as ArrestResult objects"""
        if self.results is None:
            details = (self.jobId, self.jobStatus)
            raise Exception("Results for job %s:%s not available" % details)
        else:
            results = {}
            for k in self.results:
                urlpart = self.results[k]["paramUrl"]
                u = ujoin(self.url, urlpart)
                results.update({k: ArrestResult(u)})
        return results

    def wait_for_results(self, max_time=100, interval=10,
        cancel_long=True, verbose=False
        ):
        """Wait until the job is done or fails and return results.
        max_time -- maximum number of seconds to wait for the result
        interval -- integer number of seconds between updates
        cancel_long -- cancel if waiting > max_time? True(default)|False
        verbose -- print progress? False(default)|True
        """

        interval = int(interval)
        waiting_time = 0
        status = 'esriJobSubmitted'

        if self.jobStatus in self._finished:
            details = (self.jobId, self.jobStatus)
            m = "Job %s:%s has run before, submit a new job!" % details
            raise Exception(m)

        if verbose:
            print "Waiting for job " + str(self.jobId)

        while status not in self._finished and (waiting_time < max_time):
            waiting_time += interval
            time.sleep(interval)
            self.update()
            status = self.jobStatus
            if verbose:
                ms = self.messages
                m = ms[-1].get('description', "") if ms else ''
                print "%s:%s:%s:%s" % (str(waiting_time), self.jobId, status, m)

        self.update()
        if verbose:
            print "Job %s: %s" % (self.jobId, status)

        if cancel_long and (self.jobStatus not in self._finished):
            if verbose:
                print "Cancelling job %s" % self.jobId
            m = self.cancel()
            if verbose:
                print m

        return self.results

    def cancel(self):
        """Issue the cancel operation"""
        return getjs(ujoin(self.url, 'cancel'))

class ArrestTask(ArrestObject):
    """ArcGIS Geoprocessing Task"""

    def execute(self, **args):
        """Execute synchronous task and return result json dictionary

        Example:
        url = 'http://sampleserver5.arcgisonline.com/arcgis/rest/services/GDBVersions/GPServer'
        gpr = ArrestGPService(url)
        tsk = gpr.get_task_by_name('ListVersions')
        tsk.execute()
        """
        u = ujoin(self.url, 'execute')
        return getjs(u, args)

    def submitJob(self, **args):
        """Submit asynchronous task and return ArrestJob object

        Example:
        url = 'http://sampleserver5.arcgisonline.com/arcgis/rest/services/911CallsHotspot/GPServer'
        gpr = ArrestGPService(url)
        tsk = gpr.get_task_by_index(0)
        sql = '("DATE" > date \'1998-01-01 00:00:00\' AND \
                "DATE" < date \'1998-01-31 00:00:00\') AND \
                ("Day" = \'SUN\' OR "Day"= \'SAT\')'
        job = task.submitJob(query=sql)
        res = job.wait_for_results(30, 3, verbose=True)
        out = job.get_result_by_name('Output_Features')
        """
        u = ujoin(self.url, "submitJob")
        job_info = getjs(u, args)
        job_url = ujoin(self.url, "jobs", job_info["jobId"])
        return ArrestJob(job_url)

class ArrestGPService(ArrestService):
    """GPServer"""

    def get_tasks(self):
        """Return tasks in this service as a list of ArrestTask objects"""
        tasks = []
        for ti in self.tasks:
            u = ujoin(self.url, ti)
            task = ArrestTask(u)
            tasks.append(task)
        return tasks

    def get_task_by_name(self, name):
        """Return ArrestTask object by task name, None if not found"""
        task = None
        if str(name) in self.tasks:
            u = ujoin(self.url, name)
            task = ArrestTask(u)
        return task

    def get_task_by_index(self, i):
        """Return ArrestTask object by task index"""
        name = self.tasks[i]
        task = self.get_task_by_name(name)
        return task


class ArrestGeometryService(ArrestService):
    """GeometryServer

    This class allows you to use operations of ArcGIS Geometry Service.
    Do not overload sample geometry services published by Esri or other party!
    Use such sample services for testing only.
    Publish your own geometry service for more frequent use.

    This class implements methods to assist you with constructing queries
    for the operations supported by ArcGIS for Server 10.1. However, you
    must know what server version you use and what operations it supports.

    In case you need to use operation for which there is no method, use the
    inherited generic method ArrestService.operation(...).

    Please refer to ArcGIS REST API help for details:

    Geometry Server (and its operations)
    http://resources.arcgis.com/en/help/rest/apiref/geometryserver.html

    Datum Transformations
    http://resources.arcgis.com/en/help/rest/apiref/dattrans.html

    Geographic Coordinate Systems
    http://resources.arcgis.com/en/help/rest/apiref/gcs.html

    Projected Coordinate Systems
    http://resources.arcgis.com/en/help/rest/apiref/pcs.html

    """

    def project(self, geometries, inSR, outSR,
        transformation='', transformForward=''
        ):
        """Interface for Project operation.
        >>> s.project('123,456', 27700, 4326, 1314, True)
        >>> s.project('http://online/file.txt, 4326, 2770, 1314, False)
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('project', **pars)

    def simplify(self, geometries, sr):
        """Interface for Simplify operation
        Example:
        g = {"geometryType": "esriGeometryPolyline", "geometries": [{"paths": [
          [[-97.68,32.87],[-97.61,32.86],[-97.62,32.84],[-97.67,32.82]]
        ],"spatialReference" : {"wkid" : 4326}}]}

        s.simplify(g, 4326)
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('simplify', **pars)

    def buffer(self,
        geometries, inSR, distances,
        outSR='', bufferSR='',
        unit='', unionResults=False, geodesic=False
        ):
        """Interface for Buffer operation
        >>> s.buffer('123,456', 27700, 100)
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('buffer', **pars)

    def areasAndLengths(self, polygons, sr,
         lengthUnit='', areaUnit='', calculationType="planar"
         ):
        """Interface for Areas And Lengths operation
        polygons -- list of polygons to calculate areas and lengths for
        sr -- Spatial Reference of polygons as WKID or json
        lengthUnit -- optional length unit code, default is inferred from sr
        areaUnit -- optional area unit code, default is inferred from sr
        calculationType -- planar(default)|geodesic|preserveShape
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('areasAndLengths', **pars)

    def lengths(self, polylines, sr, lengthUnit='', calculationType="planar"):
        """Interface for Lengths operation
        polylines -- list of polylines to calculate lengths for
        sr -- Spatial Reference of polylines as WKID or json
        lengthUnit -- optional length unit code, default is inferred from sr
        calculationType -- planar(default)|geodesic|preserveShape

        Parameter 'geodesic' deprecated at 10.1, use .operation(...) if needed.
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('lengths', **pars)

    def labelPoints(self, polygons, sr):
        """Interface for Label Points operation
        polygons -- list of polygons to calculate label points for
        sr -- Spatial Reference of polygons as WKID or json
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('labelPoints', **pars)

    def relation(self, geometries1, geometries2, sr, relation,relationParam=''):
        """Interface for Relation operation

        geometries1, geometries2 -- lists of geometries to calculate relate
        sr -- Spatial Reference as WKID or json
        relation -- relation to test, member of enum enumEsriGeometryRelation
        relationParam -- only relevant if parameter relation is
            esriGeometryRelationRelation, e.g. 'RELATE(G1, G2, "FFFTTT***")'

        allowed relations:
        esriGeometryRelationCross|esriGeometryRelationDisjoint|
        esriGeometryRelationIn|esriGeometryRelationInteriorIntersection|
        esriGeometryRelationIntersection|esriGeometryRelationLineCoincidence|
        esriGeometryRelationLineTouch|esriGeometryRelationOverlap|
        esriGeometryRelationPointTouch|esriGeometryRelationTouch|
        esriGeometryRelationWithin|esriGeometryRelationRelation
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('relation', **pars)

    def densify(self, geometries, sr, maxSegmentLength,
        geodesic=False, lengthUnit=''
        ):
        """Interface for Densify operation
        geometries -- list of geometries to densify
        sr -- Spatial Reference as WKID or json
        maxSegmentLength -- segments longer than this will be densified
        geodesic -- Use the GCS of sr to densify? False(default)|True
        lengthUnit -- optional length unit code for maxSegmentLength,
            default inferred from sr
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('densify', **pars)

    def distance(self, geometry1, geometry2, sr,
        distanceUnit="", geodesic=False
        ):
        """Interface for Distance operation
        geometry1 -- geometry to measure the distance from
        geometry2 -- geometry to measure the distance to
        sr -- Spatial Reference as WKID or json
        distanceUnit -- optional length unit code,  default inferred from sr
        geodesic -- Calculate geodesic distance? False(default)|True
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('distance', **pars)

    def union(self, geometries, sr):
        """Interface for Union operation
        geometries -- list of geometries to union
        sr -- Spatial Reference as WKID or json
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('union', **pars)

    def intersect(self, geometries, geometry, sr):
        """Interface for Intersect operation
        geometries -- list of geometries to intersect with geometry
        geometry -- geometries will be intersected with this geometry
        sr -- Spatial Reference as WKID or json
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('intersect', **pars)

    def cut(self, cutter, target, sr):
        """Interface for Cut operation
        cutter -- Polyline to be used to divide the target
        target -- List of polylines or polygons to be cut
        sr -- Spatial Reference as WKID or json
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('cut', **pars)

    def trimExtend(self, polylines, trimExtendTo, sr, extendHow):
        """Interface for TrimExtend operation
        polylines -- list of polylines to be trimmed or extended
        trimExtendTo -- Polyline to be used as a guide for trimming/extending
        sr -- Spatial Reference as WKID or json
        extendHow -- optional flag 0|1|2|4|8|16, default is 0, see help.
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('trimExtend', **pars)

    def offset(self, geometries, sr, offsetDistance, offsetUnit='',
        offsetHow='esriGeometryOffsetRounded', bevelRatio='1.1',
        simplifyResult=False):
        """Interface for Offset operation
        geometries -- list of geometries to be offset
        sr -- Spatial Reference as WKID or json
        offsetDistance -- distance for constructing the offset from geometries
        offsetUnit -- offsetDistance unit code, default inferred from sr
        offsetHow -- one of:
            esriGeometryOffsetRounded(default)|
            esriGeometryOffsetMitered|
            esriGeometryOffsetBevelled
        bevelRatio -- default is 1.1, see help for details
        simplifyResult -- False(default)|True
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('offset', **pars)

    def generalize(self, geometries, sr, maxDeviation, deviationUnit):
        """Interface for Generalize operation
        geometries -- list of geometries to generalize
        sr -- Spatial Reference as WKID or json
        maxDeviation -- maximum deviation for generalizing
        deviationUnit -- maxDeviation unit code, default inferred from sr
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('generalize', **pars)

    def autoComplete(self, polygons, polylines, sr):
        """Interface for AutoComplete operation
        polygons -- List of polygons used for some boundaries for new polygons
        polylines -- List of polylines to be used as the remaining boundaries
        sr -- Spatial Reference as wKID or json
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('autoComplete', **pars)

    def reshape(self, target, reshaper, sr):
        """Interface for Reshape operation
        target -- polyline or polygon to be reshaped
        reshaper -- single part polyline to do the reshaping
        sr -- Spatial Reference as WKID or json
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('reshape', **pars)

    def convexHull(self, geometries, sr):
        """Interface for ConvexHull operation
        geometries -- list of geometries to create convex hull for
        sr -- Spatial Reference as WKID or json
        """
        pars = locals()
        pars.pop("self")
        return self.opreation('convexHull', **pars)

class ArrestImageService(ArrestService):
    pass

class ArrestNetworkService(ArrestService):
    pass

class ArrestGeodataService(ArrestService):
    pass

class ArrestGlobeService(ArrestService):
    pass

class ArrestMobileService(ArrestService):
    pass

lut_servicetype_by_typestr = {
    "GeometryServer": ArrestGeometryService,
    "MapServer": ArrestMapService,
    "FeatureServer": ArrestFeatureService,
    "GeocodeServer": ArrestGeocodeService,
    "GPServer": ArrestGPService,
    "GeometryServer":ArrestGeometryService,
    "ImageServer": ArrestImageService,
    "NetworkServer": ArrestNetworkService,
    "GeodataServer": ArrestGeodataService,
    "GlobeServer": ArrestGlobeService,
    "MobileServer": ArrestMobileService
}


if __name__ == "__main__":

    # play with some catalog
    serverurl = r'http://sampleserver1.arcgisonline.com/ArcGIS/rest/services'
    server = ArrestCatalog(serverurl)
    server.ddict
    server.folders
    server.services
    folders = server.get_folders()
    services = server.get_services()

    # play with some map service
    mapserverurl = 'http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/Demographics/ESRI_Census_USA/MapServer'
    service = ArrestMapService(mapserverurl)
    service.get_layer_names()

    lr = service.get_layer_by_name('Detailed Counties')

    # play with a layer (can be created as ArrestLayer(url) too)
    lr.get_field_names()
    lr.fields
    lr.url
    plr = lr.get_parent_layer()
    plr.name

    ftrs = lr.query(where="STATE_NAME = 'Illinois'",
        outFields='FIPS,NAME', returnGeometry=False)

    # It is still a bit wolly when I get to the actural features,
    # but it's workable
    map(lambda a: a['attributes'], ftrs["features"])
    getter = lambda a: (a['attributes']['NAME'],a['attributes']['FIPS'])
    map(getter, ftrs["features"])

    # A simplified query
    ftrs = lr.query_where("STATE_NAME = 'Illinois'", 'FIPS,NAME'
        , returnGeometry=False)
    map(lambda a: a['attributes'], ftrs["features"])

    # Geometry service
    gms = server.get_service_by_name('Geometry')

    g = {"geometryType": "esriGeometryPolyline", "geometries": [ {"paths": [
            [[-97.68,32.87],[-97.61,32.86],[-97.62,32.84],[-97.67,32.82]]
          ], "spatialReference" : {"wkid" : 4326} } ]}

    pt1 = { "geometryType" : "esriGeometryPoint", "geometry" : {
        "x" : -118.15, "y" : 33.80, "spatialReference" : {"wkid" : 4326}
    }}
    pt2 = { "geometryType" : "esriGeometryPoint", "geometry" : {
        "x" : -128.15, "y" : 43.80, "spatialReference" : {"wkid" : 4326}
    }}

    print gms.simplify(g, 4326)
    print gms.buffer('123,456', 27700, 100)
    print gms.distance(pt1, pt2, 4326, geodesic=True)
    print gms.convexHull(g, 4326)

    # lengths available in 10.1 and above only:
    print gms.lengths(g["geometries"], 4326, 9001, calculationType="geodesic")


    # Geoprocessing is possible too!

    # Synchronous
    gpsurl = 'http://sampleserver5.arcgisonline.com/arcgis/rest/services/GDBVersions/GPServer'
    gps = ArrestGPService(gpsurl)
    gps.tasks
    task = gps.get_task_by_name('ListVersions')
    task.execute()

    # Asynchronous
    gpaurl = 'http://sampleserver5.arcgisonline.com/arcgis/rest/services/911CallsHotspot/GPServer'
    gpa = ArrestGPService(gpaurl)
    task = gpa.get_task_by_index(0)
    task.name
    task.displayName
    task.parameters
    sql = """("DATE" > date '1998-01-01 00:00:00' AND \
         "DATE" < date '1998-01-31 00:00:00') AND \
         ("Day" = 'SUN' OR "Day"= 'SAT')"""

    job = task.submitJob(query=sql)
    r = job.wait_for_results(30, 3, verbose=True)
    job.get_result_names()
    job.get_result_by_name('Output_Features')
    job.get_results()
    #job.update()
    #job.cancel()



