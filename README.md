arcapi
======
Wrapper functions, helper functions, and aliases that make ArcGIS Python scripting easier.

How to use?
-----------

    import arcapi as ap
    ap.__version__

[![introducing aracpi] (./intro_to_arcapi.jpg "Watch into")](http://youtu.be/qCC2VRywYWg)


Installation
------------
Download this repository, put its contents somewhere into python path, then:

    import arcapi as ap

If you do not want to put it into your python path, then:

    arcapipath = "c:\\path\\to\\folder_containig__arcapi_folder"
    import sys
    sys.path.insert(0, arapipath)
    import arcapi as ap

Resources
---------
- Read [tutorial](https://github.com/NERC-CEH/arcapi/blob/master/arcapi_tutorial.py) to get a glimpse of what arcapi is about.
- Each function in arcapi has a decent docstring, more examples are in [arcapi_test.py](https://github.com/NERC-CEH/arcapi/blob/master/arcapi_test.py).
- Read the header of [arcapi.py](https://github.com/NERC-CEH/arcapi/blob/master/arcapi.py).
- List all functions and their documentation: `help(arcapi)`
- [Esri GeoNet arcapi Group](https://geonet.esri.com/groups/arcapi) and a [forum thread](https://geonet.esri.com/thread/89307)

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
We welcome contributions from anyone and everyone, we appreciate comments and
raising issues as much as we value code contributions.

The preferred way of making contribution is via GitHub as described below,
but feel free to get in touch by email if GitHub is not your cup of tea.

NERC-CEH/arcapi contains two main branches: 'master' and 'develop'.
Master is always clean and functional, develop is for merging feature branches 
before they are added to master. Issue pull requests against the develop branch,
not the master branch. Only the code maintainer should change the master branch
and make tags off the master.

To make a contribution:
1. Fork this repository.
2. Make a new local feature branch from the develop branch.
3. Work in the local feature branch.
4. When done, merge to your fork of the develop branch.
5. Make sure your develop branch is compatible with NERC-CEH/arcapi develop.
6. Issue pull request to NERC-CEH/arcapi develop branch.

If you feel you have made significant contribution anywhere in arcapi files,
please add yourself to the authors at the top of arcapi.
By contributing to arcapi you are releasing the code under the [Lesser General Public License v3](http://choosealicense.com/licenses/lgpl-v3/).
If you add a function, please add a test too.
Read the [Contributing to OS guide](https://guides.github.com/overviews/os-contributing/) for more details.

License
-------
[LGPL v3](https://github.com/NERC-CEH/arcapi/blob/master/LICENSE)
