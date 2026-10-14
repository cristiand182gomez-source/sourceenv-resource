"""Analyze retained native episode logs or released aggregate rows. No execution."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source'))
import argparse,json
from prospective_metrics import analyze,aggregate

def retained_costs(raw):
 # Normalize the stale aggregate alias in older public-runner logs, without
 # changing raw evidence or imputing an uncertain request's cost.
 result=dict(raw);correction=None
 if 'generated_tokens_lower_bound' in raw and 'generated_tokens_upper_bound' in raw:
  low,high=raw['generated_tokens_lower_bound'],raw['generated_tokens_upper_bound']
  exact=low if low==high else None
  if raw.get('generated_tokens')!=exact:
   correction={'field':'generated_tokens','reported':raw.get('generated_tokens'),'normalized':exact,
      'basis':'retained generated_tokens_lower_bound/upper_bound; raw log unchanged'}
   result['generated_tokens']=exact
 return result,correction
def summarize(rows):
 result={}
 for config in sorted({r['configuration'] for r in rows}):
  out={}
  for arm in ['FC','BASE']:
   planned=[r for r in rows if r['configuration']==config and r['arm']==arm]
   valid=[r for r in planned if r['availability']=='VALID' and r['endpoint'] in ['PASS','FAIL']]
   damaged=[r for r in valid if not r['healthy']];healthy=[r for r in valid if r['healthy']]
   out[arm]={'repair_numerator':sum(r['endpoint']=='PASS' for r in damaged),'repair_denominator':len(damaged),
    'healthy_preservation_numerator':sum(r['endpoint']=='PASS' for r in healthy),'healthy_preservation_denominator':len(healthy),
    'planned':len(planned),'available':len(valid),'losses':sum(len(r['losses']) for r in valid),
    'source_effective':sum(r['source']['effective'] for r in valid),'environment_effective':sum(r['environment']['effective'] for r in valid)}
  result[config]=out
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('logs',nargs='*',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
 if not args.logs:
  result=summarize(json.loads((ROOT/'results/r3_by_arm.json').read_bytes()))
 else:
  paths=[]
  for path in args.logs:
   paths.extend(sorted((path/'episodes').glob('*/episode.json')) if path.is_dir() else [path])
  if not paths and not (len(args.logs)==1 and args.logs[0].is_dir() and (args.logs[0]/'run.json').is_file() and (args.logs[0]/'closure.json').is_file()):
   raise RuntimeError('No episode logs found; not a retained run directory')
  episodes=[json.loads(path.read_bytes()) for path in paths]
  if len({e['case_id'] for e in episodes})!=len(episodes):raise RuntimeError('Analyze separate runs separately; duplicate case IDs')
  result={'episodes':{e['case_id']:{**analyze(e),'context_accounting':e.get('context_accounting','not_recorded')} for e in episodes},
          'summary':aggregate(episodes,json.loads((ROOT/'source/cases.json').read_bytes())),
          'context_accounting':{mode:sum(e.get('context_accounting','not_recorded')==mode for e in episodes)
              for mode in sorted({e.get('context_accounting','not_recorded') for e in episodes})}}
  if len(args.logs)==1 and args.logs[0].is_dir():
   costs=args.logs[0]/'costs.json'
   if costs.exists():
    result['costs'],correction=retained_costs(json.loads(costs.read_bytes()))
    if correction:result['costs_normalization']=correction
   metadata=args.logs[0]/'run.json'
   if metadata.exists():result['run_context_accounting']=json.loads(metadata.read_bytes()).get('context_accounting','not_recorded')
 if args.output:
  if args.output.exists():raise RuntimeError('OUTPUT_EXISTS')
  args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
