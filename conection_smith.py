import os
import sys
import pathlib
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parent

env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

subprocess.run(
        [
            sys.executable, "-c",
            "import sys; sys.argv = ['langgraph', 'dev', '--allow-blocking'];"
            " from langgraph_cli.cli import cli; cli()",
        ],
        cwd=str(REPO_ROOT),
        env=env,
    )