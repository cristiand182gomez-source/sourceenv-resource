"""Directed cost-alias regression. Scripted usage only; no endpoint/apps."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json,tempfile,time,unittest
from endpoint_backend import EndpointBackend
from analyze import retained_costs

class CostAlias(unittest.TestCase):
 def persist(self,attempts):
  with tempfile.TemporaryDirectory() as folder:
   b=EndpointBackend.__new__(EndpointBackend);b.output=Path(folder)
   b.ledger={'started_monotonic':time.monotonic(),'completion_attempts':attempts,'generated_tokens':0}
   b.persist()
   return json.loads((Path(folder)/'costs.json').read_bytes())
 def test_no_requests(self):
  self.assertEqual(self.persist([])['generated_tokens'],0)
 def test_complete_usage(self):
  r=self.persist([{'known_tokens':17,'cap':2048,'reasoning_tokens':0},{'known_tokens':1000,'cap':2048,'reasoning_tokens':0},{'known_tokens':1250,'cap':2048,'reasoning_tokens':0}])
  self.assertEqual((r['generated_tokens'],r['generated_tokens_lower_bound'],r['generated_tokens_upper_bound']),(2267,2267,2267))
 def test_uncertain_partial_usage(self):
  r=self.persist([{'known_tokens':17,'cap':2048,'reasoning_tokens':0},{'known_tokens':None,'cap':2048,'reasoning_tokens':None}])
  self.assertIsNone(r['generated_tokens']);self.assertEqual((r['generated_tokens_lower_bound'],r['generated_tokens_upper_bound']),(17,2065))
 def test_zero_known_usage(self):
  self.assertEqual(self.persist([{'known_tokens':0,'cap':2048,'reasoning_tokens':0}])['generated_tokens'],0)
 def test_legacy_normalization_does_not_mutate_raw(self):
  raw={'generated_tokens':0,'generated_tokens_lower_bound':2267,'generated_tokens_upper_bound':2267}
  r,c=retained_costs(raw);self.assertEqual(r['generated_tokens'],2267);self.assertEqual(raw['generated_tokens'],0)
  self.assertEqual(c['reported'],0)
 def test_uncertain_analysis_not_imputed(self):
  r,c=retained_costs({'generated_tokens':0,'generated_tokens_lower_bound':17,'generated_tokens_upper_bound':2065})
  self.assertIsNone(r['generated_tokens']);self.assertEqual((r['generated_tokens_lower_bound'],r['generated_tokens_upper_bound']),(17,2065))
 def test_correct_alias_not_reclassified(self):
  r,c=retained_costs({'generated_tokens':17,'generated_tokens_lower_bound':17,'generated_tokens_upper_bound':17})
  self.assertIsNone(c);self.assertEqual(r['generated_tokens'],17)

if __name__=='__main__':unittest.main()
