from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from remaining_detectors import zombie_run, resource_burst, spike_score, department_changes, run


class RuleTests(unittest.TestCase):
    def test_zombie_strict_duration_and_gap(self):
        exactly_three=np.arange(13,dtype=np.int64)*900_000
        self.assertEqual(zombie_run(exactly_three)[0],10_800_000)
        longer=np.r_[exactly_three,10_800_001]
        self.assertGreater(zombie_run(longer)[0],10_800_000)
        broken=np.r_[np.arange(7)*900_000,6_300_001+np.arange(7)*900_000]
        self.assertLessEqual(zombie_run(broken)[0],10_800_000)

    def test_crawler_distinct_count_and_window_edges(self):
        times=np.arange(201,dtype=np.int64)*216_000
        self.assertEqual(resource_burst(times,np.arange(201))[0],201)
        self.assertEqual(resource_burst(times+np.r_[np.zeros(200,dtype=int),1],np.arange(201))[0],0)
        self.assertEqual(resource_burst(times,np.zeros(201,dtype=int))[0],0)
        self.assertEqual(resource_burst(times[:200],np.arange(200))[0],0)

    def test_spike_baseline_and_zero_mad(self):
        self.assertEqual(spike_score([0]*14)[0],0)
        self.assertEqual(spike_score([10]*12+[100,100])[0],0)  # strict >95th percentile
        self.assertEqual(spike_score([8,9,10,10,10,11,12,100,110])[0],2)

    def test_department_ties_and_majority_change(self):
        modules=pd.DataFrame({'MODULE_INSTANCE_ID':['a','b','c','d'], 'TERM':['1','1','2','2'], 'DEPARTMENT_ID':['A','B','B','B']})
        regs=pd.DataFrame({'P_ID':['change','change','tie','tie','tie'], 'MODULE_INSTANCE_ID':['a','c','a','b','d']})
        result=department_changes(regs,modules,['change','tie','none']).set_index('P_ID')
        self.assertTrue(result.loc['change','is_monster'])
        self.assertFalse(result.loc['tie','is_monster'])
        self.assertFalse(result.loc['none','is_monster'])

    def test_pipeline_cross_chunk_duplicates_pairs_and_uk_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'Test';folder.mkdir();out=Path(tmp)/'out'
            def save(name,data):pd.DataFrame(data).to_csv(folder/name,index=False)
            save('la_mmh_test_person_dim.csv',{'P_ID':['a','b','c'],'deregistration_date':['04/03/2024',None,None]})
            save('la_mmh_calendar_dim.csv',{'DATE':['2024-03-04','2024-03-05'],'TERM':['Autumn','Spring'],'WEEK_NUMBER':[1,2],'ACADEMIC_YEAR':[2023,2023]})
            save('la_mmh_test_lms_item_activity_by_session_fact.csv',{
                'PIT_ID':['1','2','3','4','5'],'P_ID':['a','b','a','b','a'],
                'DATE':['2024-03-04','2024-03-04','2024-03-05','2024-03-05','2024-03-04'],
                'TIMESTAMP':['2024-03-04T01:00:00Z','2024-03-04T02:00:00Z','2024-03-05T01:00:00Z','2024-03-05T02:00:00Z','2024-03-04T01:00:00Z'],
                'LMS_ITEM_ID':['x','x','y','y','x']})
            save('la_mmh_test_video_activity_by_view_fact.csv',{'PVT_ID':['v1','v2'],'P_ID':['c','clone'],'DATE':['2024-03-04','2024-03-04'],'TIMESTAMP':['2024-03-04T01:00:00Z','2024-03-04T01:00:00Z'],'VIDEO_ID':['v','v']})
            save('la_mmh_test_person_module_instance_fact.csv',{'P_ID':['a','a'],'MODULE_INSTANCE_ID':['m1','m2']})
            save('la_mmh_module_instance_dim.csv',{'MODULE_INSTANCE_ID':['m1','m2'],'TERM':['1','2'],'DEPARTMENT_ID':['A','B']})
            run(tmp,'Test',out,chunksize=2)
            def ids(name):return set(pd.read_csv(out/name/'test_predictions.csv').P_ID)
            self.assertEqual(ids('phantom'),{'a'})
            self.assertEqual(ids('doppelganger'),{'c','clone'})
            self.assertEqual(ids('undead'),{'a'})
            self.assertEqual(ids('shapeshifter'),{'a'})
            evidence=pd.read_csv(out/'undead/test_evidence.csv').set_index('P_ID')
            self.assertEqual(evidence.loc['a','activity_rows_after'],1)


if __name__=='__main__':unittest.main()
