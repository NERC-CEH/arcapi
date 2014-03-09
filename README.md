arcapi
======
Wrapper functions, helper functions, and aliases that make ArcGIS Python scripting easier.

How to use?
-----------

    import arcapi as ap
    ap.version()


Installation
------------
Download this repository, put its contents somewhere into python path, then:

    import arcapi as ap

If you do not want to put it into your python path, then:

    arcapipath = "c:\\path\\to\directory\\contating_arcapi_py"
    import sys
    sys.path.insert(0, arapipath)
    import arcapi as ap

Resources
---------
- Read [tutorial](https://github.com/NERC-CEH/arcapi/blob/master/arcapi_tutorial.py) to get a glimpse of what arcapi is about.
- Each function in arcapi has a decent docstring.
- Read the header of [arcapi.py](https://github.com/NERC-CEH/arcapi/blob/master/arcapi.py).
- List all functions and their documentation: `help(arcapi)`
- [ArcGIS Forum thread announcing arcapi] (http://forums.arcgis.com/threads/103666-arcapi-Convenient-API-for-arcpy) (please prefer github for discussions of details)

Dependencies
------------
[ArcGIS for Desktop/Server](http://www.esri.com/software/arcgis/arcgis-for-desktop)
with Python and [ArcPy site package](http://resources.arcgis.com/en/help/main/10.1/index.html#/What_is_ArcPy/000v000000v7000000/).
Modules matplotlib, numpy.
Tested and developed on ArcGIS for Desktop 10.1 SP1.
Some functions require Spatial Analyst Extension in order to be fully functional.


Tests
-----
Tests for arcapi.py are in arapi_tests.py, testing data in ./testing folder.
Everybody is encouraged to write more and better tests.


Issues
------
Feel free to submit issues and enhancement requests.


Contributing
------------
We welcome contributions from anyone and everyone.
If you feel you have made significant contribution anywhere in arcapi files,
please add yourself to the authors at the top of arcapi.
By contributing to arcapi you are releasing the code under the [Lesser General Public License v3](http://choosealicense.com/licenses/lgpl-v3/).
If you add a function, please add a test too.


License
-------
[LGPL v3](https://github.com/NERC-CEH/arcapi/blob/master/LICENSE)
