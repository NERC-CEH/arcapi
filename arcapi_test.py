"""
#-------------------------------------------------------------------------------
# Name:        arcapi_test
# Purpose:     Tests for arcapi.arcapi module.
#
# Author:      Filip Kral
#
# Created:     01/02/2014
# Licence:     LGPL v3
#-------------------------------------------------------------------------------
# Most of the functions operate on potentially complex data, or require manual
# checking of results, and therefore testing is rather difficult.
#
# Everybody is encouraged to contribute to tests.
#-------------------------------------------------------------------------------
"""

import unittest
import os
import sys
import arcpy
import arcapi as ap

class TestGlobalFunctions(unittest.TestCase):

    def setUp(self):
        # access testing data
        self.testingfolder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testing')
        self.testing_gdb = os.path.join(self.testingfolder, 'testing.gdb')
        #self.t_table = os.path.join(self.testing_gdb, '\left_i_right')
        #self.t_fc =  os.path.join(self.testing_gdb, 'left_i_right')
        #self.t_cols = ('OBJECTID', 'Shape', 'CCARM2', 'POINT_X', u'POINT_Y', u'ROUND_X', 'ROUND_Y', 'name', 'propagatedName', 'fullName', 'GID', 'DOWNGID', 'HA_NUM','STRAHLER', 'SHREVE', 'OS_NAME', 'FNODE_FULL', 'TNODE_FULL', 'NAMENOXML', 'Shape_Length')
        self.t_fc =  os.path.join(self.testing_gdb, 'ne_110m_admin_0_countries')
        self.t_cols =  ('OBJECTID','Shape','ScaleRank','LabelRank','FeatureCla',
                      'SOVEREIGNT','SOV_A3','ADM0_DIF','LEVEL','TYPE','ADMIN',
                      'ADM0_A3','GEOU_DIF','GEOUNIT','GU_A3','SU_DIF','SUBUNIT',
                      'SU_A3','NAME','ABBREV','POSTAL','NAME_FORMA','TERR_',
                      'NAME_SORT','MAP_COLOR','POP_EST','GDP_MD_EST','FIPS_10_',
                      'ISO_A2','ISO_A3','ISO_N3','Shape_Length','Shape_Area')
        pass

    def tearDown(self):
        pass

    def testnames(self):
        est = map(str, tuple(ap.names(self.t_fc)))
        obs = ('OBJECTID','Shape','ScaleRank','LabelRank','FeatureCla',
                'SOVEREIGNT','SOV_A3','ADM0_DIF','LEVEL','TYPE','ADMIN',
                'ADM0_A3','GEOU_DIF','GEOUNIT','GU_A3','SU_DIF','SUBUNIT',
                'SU_A3','NAME','ABBREV','POSTAL','NAME_FORMA','TERR_',
                'NAME_SORT','MAP_COLOR','POP_EST','GDP_MD_EST','FIPS_10_',
                'ISO_A2','ISO_A3','ISO_N3','Shape_Length','Shape_Area')
        self.assertEqual(tuple(est), obs)
        pass

    def testtypes(self):
        est = map(str, tuple(ap.types(self.t_fc)))
        obs = ('OID','Geometry','SmallInteger','SmallInteger','String','String',
                'String','Single','Single','String','String','String','Single',
                'String', 'String','Single','String','String','String','String',
                'String','String', 'String','String','Single','Double','Double',
                'Single','String','String', 'Single','Double','Double')
        pass

    def testnrow(self):
        est = ap.nrow(self.t_fc)
        obs = 177
        self.assertEqual(est, obs)
        pass

    def testvalues(self):

        fc = self.t_fc
        w = '"OBJECTID" < 11'

        vals1 = ap.values(fc, 'Shape_Length', w)
        vals2 = ap.values(fc, 'Shape_Length', w, 'Shape_Length ASC')
        vals3 = ap.values(fc, 'SHAPE@XY', w)
        vals4 = ap.values(fc, 'SHAPE@XY;Shape_Length', w, 'Shape_Length DESC')
        est = all([len(vi) == 10 for vi in [vals1, vals2, vals3, vals4]])
        self.assertTrue(est)

    def testvalues_crosscolumns(self):
        # the values function requires columns included in the o parameter
        # to be included in the col parameter too, otherwise an invalid
        # sql statement is generated.
        fc = self.t_fc
        w = '"OBJECTID" < 11'
        with self.assertRaises(RuntimeError):
            vals = ap.values(fc, 'SHAPE@XY', w, 'Shape_Length ASC')
        pass


##    def testdistinct(self):
##        pass

    def testhead(self):
        est = 5
        hd = ap.head(self.t_fc, est, geoms = " ", verbose=False)
        obs = len(hd[0])
        self.assertEqual(est, obs)
        pass

    def testchart(self):
        obs = r'c:\temp\chart.jpg'
        t_fc = self.t_fc
        est = ap.chart(t_fc, obs, texts = {'txt': 'Element txt'}, openit=False)
        self.assertEqual(est, obs)
        pass

    def testplot(self):
        pic = r'c:\temp\plot.png'
        x = xrange(20)
        ap.plot(x, out_file=pic, openit=False)
        y = xrange(50,70)
        ap.plot(x, y, pic, 'Main', 'X [m]', 'Y [m]', 'o', 'k', openit=False)
        os.remove(pic)
        with self.assertRaises(ap.ArcapiError):
            ap.plot(x, [1,2,3], pic, 'Main', 'X [m]', 'Y [m]', 'o', 'k', openit=False)
        pass

    def testhist(self):
        pic = r'c:\temp\plot.png'
        x = xrange(20)
        h = ap.hist(x, out_file=pic, openit=False)
        h = ap.hist(x, pic, main='Main', xlab='Xlbl', log=True, openit=False)
        os.remove(pic)
        self.assertFalse(os.path.exists(pic))

    def testbars(self):
        pic = r'c:\temp\plot.png'
        x = xrange(20)
        ap.bars(x, out_file=pic, openit=False)
        y = xrange(50,70)
        ap.bars(x, out_file=pic, labels=y, main='Main', xlab='X', ylab='Y', openit=False)
        ap.bars([], openit=False)
        os.remove(pic)
        self.assertFalse(os.path.exists(pic))

    def testrename_col(self):
        import arcpy
        import tempfile
        owo = arcpy.env.overwriteOutput
        arcpy.env.overwriteOutput = True
        tmpfc = os.path.join(tempfile.gettempdir(), "tmp")
        tmpfc = arcpy.CopyFeatures_management(self.t_fc, tmpfc).getOutput(0)
        est = ap.rename_col(tmpfc, "ABBREV", "ABBREVIATION")
        obs = "ABBREVIATI"
        arcpy.Delete_management(tmpfc)
        arcpy.env.overwriteOutput = owo
        self.assertEqual(est, obs)
        pass

    def testtlist_to_table(self):
        colnames = ['NAME', 'POP_EST']
        coltypes = ['TEXT', 'DOUBLE']
        collengths = [250, '#']
        coldefs = zip(colnames, coltypes, collengths)
        coldefs2 = ['NAME:TEXT', 'POP_EST:DOUBLE']

        # read data
        tl = []
        with arcpy.da.SearchCursor(self.t_fc, colnames) as sc:
            for row in sc:
                tl.append(tuple(row))

        # write as table using log column definition
        ot = arcpy.CreateScratchName('tmp.dbf', workspace='c:\\temp')
        ot = ap.tlist_to_table(tl, ot, coldefs, -9, 'nullText')
        est1 = int(arcpy.GetCount_management(ot).getOutput(0))

        # write as table using short column definition
        ot = arcpy.CreateScratchName('tmp.dbf', workspace='c:\\temp')
        ot = ap.tlist_to_table(tl, ot, coldefs2, -9, 'nullText')
        est2 = int(arcpy.GetCount_management(ot).getOutput(0))
        obs = int(arcpy.GetCount_management(self.t_fc).getOutput(0))

        arcpy.Delete_management(ot)
        self.assertTrue(all((est1 == obs, est2 == obs)))
        pass

##    def testdocu(self):
##        pass

    def testmeta(self):
        fcws = 'c:\\temp'
        tempshp = arcpy.CreateScratchName('tmp.dbf', workspace=fcws).replace('.dbf', '.shp')
        fcnm = os.path.basename(tempshp)

        # testing entries
        ttl,pps,abt = "Bar","example", "Column Spam means eggs"

        fc = arcpy.FeatureClassToFeatureClass_conversion(
            self.t_fc,
            fcws,
            fcnm
        ).getOutput(0)
        ap.meta(fc, 'OVERWRITE', title=ttl)
        editted = ap.meta(fc, 'append', purpose=pps, abstract=abt)
        editted = ap.meta(fc, 'overwrite', title=ttl, purpose=pps, abstract=abt)
        retrieved = ap.meta(fc)
        ap.dlt(fc)
        self.assertEqual(set(editted.values()), set(retrieved.values()))

##    def testmsg(self):
##        pass

    def testfrequency(self):
        est = ap.frequency([1,1,2,3,4,4,4])
        obs = {1: 2, 2: 1, 3: 1, 4: 3}
        samekeys = set(est.keys()) == set(obs.keys())
        good = all([samekeys] + [est[i] == obs[i] for i in est])
        self.assertTrue(good)
        pass

    def testlist_environments(self):
        envs = ap.list_environments([])
        self.assertEqual(len(envs), 50)
        pass

    def testoidF(self):
        est = ap.oidF(self.t_fc)
        obs = "OBJECTID"
        self.assertEqual(str(est), obs)
        pass

    def testshpF(self):
        est = ap.shpF(self.t_fc)
        obs = "Shape"
        self.assertEqual(str(est), obs)
        pass

    def testtstamp(self):
        est = []
        est.append(len(ap.tstamp()) == len('20140216184029'))
        est.append(len(ap.tstamp("lr")) == len('lr20140216184045'))
        est.append(len(ap.tstamp("lr", "%H%M%S")) == len('lr184045'))
        est.append(len(ap.tstamp("lr", "%H%M%S")) == len('lr184045'))
        est.append(len(ap.tstamp("lr", "%H%M%S", s=('run',1))) == len('lr184527_run_1'))
        obs = [True, True, True, True, True]
        self.assertEqual(est, obs)
        pass

    def testdlt(self):
        est = []
        wc = '"OBJECTID" < 11'
        lr = arcpy.management.MakeFeatureLayer(self.t_fc, "lr", wc).getOutput(0)
        # TODO: test for deleting layers won't pass even though ap.dlt works
        #print lr
        #print arcpy.Exists(lr)
        tempfc = 'in_memory\\tmp'
        if arcpy.Exists(tempfc):
            arcpy.Delete_management(tempfc)
        tmpfc = arcpy.CopyFeatures_management(lr, tempfc).getOutput(0)
        tempshp = arcpy.CreateScratchName('tmp.dbf', workspace='c:\\temp').replace('.dbf', '.shp')
        fc = arcpy.CopyFeatures_management(tmpfc, tempshp).getOutput(0)
        ap.dlt(lr)
        est.append(ap.dlt(tmpfc))
        est.append(ap.dlt(fc))
        est.append(ap.dlt('this does not exist'))
        self.assertEquals(est, [True, True, False])
        pass

    def testcleanup(self):
        x = []
        out = arcpy.CreateScratchName("tmp", workspace=arcpy.env.scratchGDB)
        x.append(arcpy.management.Copy(self.t_fc, out).getOutput(0))
        est = ap.cleanup(x)
        obs = 0
        self.assertEqual(est, obs)

    def testto_points(self):
        obs = 10
        wc = '"OBJECTID" < ' + str(obs + 1)
        ofc = arcpy.CreateScratchName("tmp_out.dbf", workspace="c:\\temp").replace('.dbf', '.shp')
        cs = 27700
        ptfc = ap.to_points(self.t_fc, ofc, "POP_EST", "GDP_MD_EST", cs, w = wc)
        est = int(arcpy.GetCount_management(ptfc).getOutput(0))
        arcpy.Delete_management(ptfc)
        self.assertEqual(est, obs)
        pass


##    def testwsp(self):
##        pass
##
##    def testswsp(self):
##        pass

    def testto_scratch(self):
        est = []
        obs = []
        arcpy.env.scratchWorkspace = arcpy.env.scratchGDB
        s = arcpy.env.scratchWorkspace

        est.append(ap.to_scratch('foo', 0))
        obs.append(ap.os.path.join(s, 'foo'))
        est.append(ap.to_scratch('foo', 1))
        obs.append(os.path.join(s, 'foo0'))
        est.append(ap.to_scratch('foo.shp', 0))
        obs.append(os.path.join(s, 'foo_shp'))
        est.append(ap.to_scratch('foo.shp', 1))
        obs.append(os.path.join(s, 'foo_shp0'))

        # not tested for file based workspaces
        arcpy.env.scratchWorkspace = arcpy.env.scratchFolder
        a = arcpy.env.scratchWorkspace
        ap.to_scratch('foo', 0) == os.path.join(s, 'foo')
        ap.to_scratch('foo', 1) == os.path.join(s, 'foo0')
        ap.to_scratch('foo.shp', 0) == os.path.join(s, 'foo_shp')
        ap.to_scratch('foo.shp', 1) == os.path.join(s, 'foo_shp0')

        eq = all([ei == oi for ei,oi in zip(est, obs)])
        self.assertTrue(eq)

    def testremap_sa(self):
        est = []

        remapped = ap.remap_3d(10,50,10)
        est.append(remapped == '10 20 1;20 30 2;30 40 3;40 50 4')

        remapped = ap.remap_3d(0,5,1)
        est.append(remapped == '0 1 1;1 2 2;2 3 3;3 4 4;4 5 5')

        remapped = ap.remap_3d(-10,10,5)
        est.append(remapped == '-10 -5 1;-5 0 2;0 5 3;5 10 4')

        remapped = ap.remap_3d(-10,10,-5)
        est.append(remapped == '')

        remapped = ap.remap_3d(10,-20,-7)
        est.append(remapped == '10 3 1;3 -4 2;-4 -11 3;-11 -18 4;-18 -25 5')

        self.assertTrue(all(est))

    def testremap_3d(self):
        est = []

        remapped = ap.remap_sa(10,50,10)
        ob = [[[10, 20], 1], [[20, 30], 2], [[30, 40], 3], [[40, 50], 4]]
        est.append(remapped == ob)

        remapped = ap.remap_sa(0,5,1)
        ob = [[[0, 1], 1], [[1, 2], 2], [[2, 3], 3], [[3, 4], 4], [[4, 5], 5]]
        est.append(remapped == ob)

        remapped = ap.remap_sa(-10,10,5)
        ob = [[[-10, -5], 1], [[-5, 0], 2], [[0, 5], 3], [[5, 10], 4]]
        est.append(remapped == ob)

        remapped = ap.remap_sa(-10,10,-5)
        ob = []
        est.append(remapped == ob)

        remapped = ap.remap_sa(10,-20,-7)
        ob = [
            [[10, 3], 1], [[3, -4], 2], [[-4, -11], 3], [[-11, -18], 4],
            [[-18, -25], 5]
        ]
        est.append(remapped == ob)

        self.assertTrue(all(est))

    def testfind(self):
        self.testingfolder = r'C:\Users\filipkral\Documents\GitHub\arcapi\testing'
        obs = [1, 5]
        est = []
        findings = ap.find('*.shp', self.testingfolder)
        est.append(len(findings))
        findings = ap.find('*110m*', self.testingfolder)
        est.append(len(findings))
        self.assertEqual(est, obs)

    def testconvertIntegerToFloat(self):
        #TODO
        pass

    def testfillNoDataValues(self):
        #TODO
        pass

    def testconvertMetersToFeet(self):
        #TODO
        pass


if __name__ == '__main__':
    unittest.main(verbosity = 2)
