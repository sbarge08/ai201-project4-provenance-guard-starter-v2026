"""Separate model-stage experiment; not a capstone acceptance trial."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(r'C:\Users\sachi\ai201-project4-provenance-guard-starter-v2026')
OUT = Path(__file__).parent / 'thread-diagnostic.json'

if len(sys.argv) > 1:
    sys.path.insert(0, str(ROOT))
    import torch
    import detector
    from run_capstone_eval import valid_fixtures
    detector.warm_up()
    fixtures = valid_fixtures()
    detector.model_signal(fixtures[2])
    result = {'mode': sys.argv[1], 'intraop_threads': torch.get_num_threads(),
              'interop_threads': torch.get_num_interop_threads(),
              'torch_version': torch.__version__, 'cpu_count': os.cpu_count(),
              'model_stage': []}
    for index in (2, 9):
        durations, scores = [], []
        for _ in range(3):
            start = time.perf_counter()
            scores.append(detector.model_signal(fixtures[index]))
            durations.append(time.perf_counter() - start)
        result['model_stage'].append({'fixture_index': index, 'characters': len(fixtures[index]),
                                     'seconds': durations, 'model_scores': scores})
    print('DIAGNOSTIC_JSON=' + json.dumps(result), flush=True)
else:
    results=[]
    for mode in ('default', 'one-thread'):
        env=os.environ.copy()
        env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONIOENCODING='utf-8')
        if mode == 'one-thread':
            env.update(OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
        completed=subprocess.run([sys.executable, __file__, mode], cwd=ROOT, env=env,
                                 text=True, capture_output=True, timeout=180,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if completed.returncode:
            raise RuntimeError(completed.stderr)
        line=next(l for l in completed.stdout.splitlines() if l.startswith('DIAGNOSTIC_JSON='))
        results.append(json.loads(line.split('=',1)[1]))
        print(json.dumps(results[-1]),flush=True)
        OUT.write_text(json.dumps({'purpose':'Model-stage CPU threading diagnostic; not acceptance results',
                                   'runs':results},indent=2)+'\n',encoding='utf-8')
