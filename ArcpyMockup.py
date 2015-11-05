"""
#-------------------------------------------------------------------------------
# Name:        arcapi.ArcpyMockup
# Purpose:     Class to pretend that arcpy is always present.
#
# Authors:     Filip Kral,
#
# Created:     28/07/2014
# Licence:     LGPL v3
#-------------------------------------------------------------------------------
#
# Not all functions in arcapi require arcpy. This module allows you to use
# arcapi even if you don't have arcpy. The functions that require arcpy will
# not work, but you can still use functions that do not need arcpy.
#
#
# You do not have to do anything to load arcapi, it has been coded to use this
# module. If you want to pretend that arcpy is present on computers without
# ArcGIS in your own projects, you can reuse the class from this module like so:
#
# try:
#     import arcpy
# except ImportError:
#     arcpy = ArcpyMockup()
#
#-------------------------------------------------------------------------------
"""

from types import ModuleType

class ArcpyMockup(ModuleType):
    """This class will create object that looks like
    the arcpy module on computers where arcpy is not
    available so that users without arcpy can still use
    arcapi functions that do not require arcpy.
    Calls to functions that require arcpy will print
    a WARNING message.
    """

    def __init__(self):
        """Create mockup of the arcpy module"""
        self.da = None

    # override some methods
    def AddMessage(self, m):
        print(m)

    def AddWarning(self, m):
        print(m)

    def __getattr__(self, key):
        m = 'WARNING: Arcapi loaded without arcpy, %s not available' % key
        print(m)
        return None

    __all__ = []   # support wildcard imports
