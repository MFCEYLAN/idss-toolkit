import csv
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from idss import Candidate, Weights, rank, sensitivity, benchmark
from idss.cli import run, read_measurements


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.c = [Candidate('A', .9, 1., 100), Candidate('B', .8, 2., 200)]

    def test_hand_calculation(self):
        r = rank(self.c)
        self.assertEqual(r[0]['idss'], 1.)
        self.assertAlmostEqual(r[1]['idss'], ((.8/.9)*.5*.5)**(1/3), places=14)

    def test_cost_unit_invariance(self):
        changed = [Candidate(c.model, c.validation_macro_f1, c.latency_ms_per_record*1000, c.size_bytes*1024) for c in self.c]
        for a,b in zip(rank(self.c), rank(changed)):
            self.assertAlmostEqual(a['idss'], b['idss'])

    def test_primary_quality_only(self):
        rows = rank(self.c, Weights(1,0,0))
        self.assertAlmostEqual(rows[1]['idss'], .8/.9)

    def test_monotonicity(self):
        # Fixed normalizers are supplied by the unchanged, best candidate A.
        old = rank(self.c)[1]['idss']
        new = rank([self.c[0], Candidate('B', .85, 1.5, 150)])[1]['idss']
        self.assertGreater(new, old)

    def test_ties_and_input_order(self):
        c = [Candidate('B', .9, 1., 100), Candidate('A', .9, 1., 100), Candidate('C', .8, 2., 200)]
        rows = rank(c)
        self.assertEqual([r['rank'] for r in rows], [1,1,3])
        self.assertEqual(rows, rank(reversed(c)))

    def test_zero_quality_policy(self):
        self.assertEqual(rank([*self.c, Candidate('zero',0,1,100)])[-1]['idss'],0)
        with self.assertRaises(ValueError): rank([Candidate('zero',0,1,100)])
        self.assertEqual(rank([Candidate('zero',0,1,100)], Weights(0,.5,.5))[0]['idss'],1)

    def test_bad_measurements(self):
        for f,l,s in [(1.1,1,1),(-.1,1,1),(math.nan,1,1),(.9,0,1),(.9,math.inf,1),(.9,1,0),(.9,1,1.5)]:
            with self.subTest(f=f,l=l,s=s), self.assertRaises(ValueError): Candidate('A',f,l,s)

    def test_bad_weights(self):
        for values in [(1,1,1),(-1,1,1),(math.nan,0,1),(math.inf,0,0)]:
            with self.assertRaises(ValueError): Weights(*values)

    def test_duplicate_names(self):
        with self.assertRaises(ValueError): rank([self.c[0],self.c[0]])

    def test_profiles_use_same_data(self):
        result = sensitivity(iter(self.c))
        self.assertEqual(len(result),4)
        for rows in result.values():
            self.assertEqual({r['model'] for r in rows},{'A','B'})


class InterfaceTests(unittest.TestCase):
    def test_separate_platform_normalization_and_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'input.csv'
            p.write_text('dataset,task,platform,workload_id,model,validation_macro_f1,latency_ms_per_record,size_bytes,selection_split\n'
                         'd,b,pc,w,A,0.9,1,100,validation\n'
                         'd,b,pc,w,B,0.8,2,200,validation\n'
                         'd,b,pi,w,A,0.9,20,100,validation\n'
                         'd,b,pi,w,B,0.8,10,200,validation\n')
            r=run(p,Path(t)/'out',Weights())
            self.assertEqual(r[('d','b','pc','w')][0]['latency_component'],1)
            pi_a=next(x for x in r[('d','b','pi','w')] if x['model']=='A')
            self.assertEqual(pi_a['latency_component'],.5)
            self.assertEqual(len(list((Path(t)/'out').iterdir())),5)

    def test_test_split_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'input.csv'
            p.write_text('dataset,task,platform,workload_id,model,validation_macro_f1,latency_ms_per_record,size_bytes,selection_split\nd,b,pc,w,A,.9,1,100,test\n')
            with self.assertRaises(ValueError): run(p,Path(t)/'out',Weights())
            self.assertFalse((Path(t)/'out').exists())

    def test_timing_protocol_and_units(self):
        calls=[]
        with patch('idss.benchmark.perf_counter', side_effect=[0,1,2,4]):
            result=benchmark(lambda x:calls.append(len(x)),[1,2],warmups=1,repeats=2)
        self.assertEqual(calls,[2,2,2])
        self.assertEqual(result['latency_ms_per_record_mean'],750)
        self.assertAlmostEqual(result['latency_ms_per_record_sample_sd'],math.sqrt(125000))


if __name__ == '__main__':
    unittest.main()
