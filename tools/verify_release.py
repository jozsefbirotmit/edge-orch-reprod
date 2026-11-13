#!/usr/bin/env python3
"""Read-only integrity and scientific smoke checks for the frozen VCC research artifact.

python -B tools/verify_release.py --quick
python -B tools/verify_release.py --integrity-only
"""
from pathlib import Path
import argparse, hashlib, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]

def verify_integrity():
    path=ROOT/'SHA256SUMS.txt'
    lines=[line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    for entry in lines:
        digest,rel=entry.split('  ',1)
        target=ROOT/rel
        if not target.is_file(): raise RuntimeError('Missing expected file: '+rel)
        got=hashlib.sha256(target.read_bytes()).hexdigest()
        if got!=digest: raise RuntimeError('Checksum mismatch: '+rel)
    print(f'PASS: {len(lines)} archived SHA-256 checksums')
    return len(lines)

def run(label,folder,*cmd):
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    args=[sys.executable,'-B',*cmd]
    print(f'RUN: {label} [{" ".join(args)}]',flush=True)
    res=subprocess.run(args,cwd=ROOT/folder,env=env)
    if res.returncode: raise RuntimeError(f'{label} exited {res.returncode}')
    print('PASS: '+label,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--quick',action='store_true',help='Hashes plus tests and selected scientific checks')
    group.add_argument('--integrity-only',action='store_true',help='Only hash validation')
    args=parser.parse_args()
    verify_integrity()
    if not args.integrity_only:
        run('13 unit tests','experiments/multiservice','-m','unittest','discover','-s','tests','-v')
        run('Exact n5 quick certificate (read-only)','experiments/multiservice','verify_n5_certificate.py')
        run('Matched 72-population ablation summaries','experiments/ablation','verify_results.py')
        verify_integrity()
        print('ALL QUICK CHECKS PASSED; ARCHIVE UNCHANGED',flush=True)
