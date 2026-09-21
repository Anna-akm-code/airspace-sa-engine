"""Generate a labelled synthetic report/map bundle; no live credentials or HTTP."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from sa_engine.artifacts import write_artifacts
from sa_engine.demo import synthetic_result
from sa_engine.history import RunHistory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='runs')
    args = parser.parse_args()
    with TemporaryDirectory() as temporary:
        history = RunHistory(Path(temporary)/'runs.jsonl',Path(temporary)/'positions.jsonl')
        result = synthetic_result(history)
        folder = write_artifacts(result,history,args.output,mode='synthetic')
    print(f'SYNTHETIC DEMO - invented scenario; artifacts: {folder}')


if __name__ == '__main__':
    main()
