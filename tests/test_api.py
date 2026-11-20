import csv
import json
import tempfile
import unittest
from pathlib import Path

from idss import IDSS, Weights

CSV = ('model,validation_macro_f1,latency_ms_per_record,size_bytes\n'
       'A,0.9,1,100\nB,0.8,2,200\n')


class PublicApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'models.csv'
        self.path.write_text(CSV)

    def test_one_call_equal_defaults(self):
        result = IDSS(self.path)
        self.assertEqual(result.weights, Weights())
        self.assertEqual(result.best[0]['model'], 'A')
        self.assertEqual(result.rankings[0]['idss'], 1)
        self.assertEqual(result.calculate(), result.rankings)
        self.assertIn('A: 1.000000', str(result))

    def test_tuple_and_named_weights_agree(self):
        a = IDSS(self.path, weights=(.5,.3,.2))
        b = IDSS(self.path, weights={'quality':.5,'latency':.3,'size':.2})
        self.assertEqual(a.rankings, b.rankings)

    def test_profile_agrees_with_custom_weights(self):
        a = IDSS(self.path, profile='quality_priority')
        b = IDSS(self.path, weights=Weights(.5,.3,.2))
        self.assertEqual(a.rankings, b.rankings)
        self.assertEqual(IDSS(self.path,profile='default').rankings, IDSS(self.path).rankings)

    def test_invalid_weight_selections(self):
        bad = [{'profile':'unknown'}, {'weights':(.2,.3)}, {'weights':(.5,.5,.5)},
               {'weights':{'quality':1}}, {'weights':('a',0,1)},
               {'weights':(.5,.3,.2),'profile':'equal'}]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): IDSS(self.path,**kwargs)

    def test_custom_headers(self):
        self.path.write_text(CSV.replace('model,validation_macro_f1,latency_ms_per_record,size_bytes',
                                        'algorithm,val_f1,latency_ms,pipeline_bytes'))
        result = IDSS(self.path, columns={'model':'algorithm','validation_macro_f1':'val_f1',
                                         'latency_ms_per_record':'latency_ms','size_bytes':'pipeline_bytes'})
        self.assertEqual(result.best[0]['model'],'A')

    def test_missing_mapped_optional_header_rejected(self):
        with self.assertRaises(ValueError): IDSS(self.path, columns={'platform':'device_typo'})

    def test_test_metrics_rejected_when_declared(self):
        self.path.write_text('model,validation_macro_f1,latency_ms_per_record,size_bytes,selection_split\nA,.9,1,100,test\n')
        with self.assertRaises(ValueError): IDSS(self.path)

    def test_metadata_and_snapshot_export(self):
        result = IDSS(self.path, metadata={'cpu':'example'})
        original = self.path.read_bytes()
        self.path.write_text('source file changed after construction')
        out = result.save(self.root/'reports')
        self.assertEqual((out/'input_measurements.csv').read_bytes(), original)
        manifest = json.loads((out/'manifest.json').read_text())
        self.assertTrue(manifest['input_declarations']['assumed_validation_split'])
        self.assertEqual(manifest['measurement_metadata']['cpu'],'example')
        self.assertEqual(manifest['idss_version'],'0.2.0')

    def test_multiple_platforms_are_not_pooled(self):
        self.path.write_text('model,validation_macro_f1,latency_ms_per_record,size_bytes,platform\n'
                             'A,.9,1,100,pc\nB,.8,2,200,pc\n'
                             'A,.9,20,100,pi\nB,.8,10,200,pi\n')
        rows = IDSS(self.path).rankings
        a_pi = next(r for r in rows if r['platform']=='pi' and r['model']=='A')
        self.assertEqual(a_pi['latency_component'],.5)
        self.assertEqual(len(IDSS(self.path).best),2)

    def test_profile_copies_and_result_copies(self):
        profiles = IDSS.profiles()
        profiles['equal']['quality'] = 99
        self.assertEqual(IDSS.profiles()['equal']['quality'],1/3)
        result = IDSS(self.path)
        rows = result.rankings
        rows[0]['idss'] = 0
        self.assertEqual(result.rankings[0]['idss'],1)

    def test_sensitivity_preserves_all_profiles(self):
        rows = IDSS(self.path).sensitivity()
        self.assertEqual(len(rows),8)
        self.assertEqual(len({r['profile'] for r in rows}),4)

    def test_all_tied_winners_preserved(self):
        self.path.write_text(CSV.replace('B,0.8,2,200','B,0.9,1,100'))
        self.assertEqual(len(IDSS(self.path).best),2)


if __name__ == '__main__':
    unittest.main()
