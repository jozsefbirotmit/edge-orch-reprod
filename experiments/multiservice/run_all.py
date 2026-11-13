"""Sequential, reproducible entry point; no network or external data required."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser();p.add_argument('--with-pdf',action='store_true');args=p.parse_args()
    commands=[['-m','unittest','discover','-s','tests','-v'],['run_experiments.py'],
              ['local_robustness.py'],['pulse_thresholds.py'],['analyze_results.py'],
              ['validate_archive.py'],['create_figures.py'],['create_report.py']]
    for command in commands:subprocess.run([sys.executable,*command],cwd=ROOT,check=True)
    if args.with_pdf:
        for _ in range(2):subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error',
                                         'M1_Multiservice_Experiments.tex'],cwd=ROOT,check=True)


if __name__=='__main__':main()
