"""
Batch run Scala, write output to files.
"""
import os
import subprocess
import shutil
from pathlib import Path

SCALA_PROGRAM = os.environ.get("SCALA_PROGRAM", "scala")
OUTPUT_DIR = Path("scala-analysis")

def main():
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir()

    COMMANDS = [
        "SHOW",
        "SHOW/INTERVAL",
        "SHOW INTERVALS",
        "SHOW/LINE/CENTS INTERVALS",
        "SHOW/SPAN INTERVALS",
        "SHOW DATA",
        "FIT/MODE",
        "FIT/HARMONIC",
    ]

    cmd_file = Path("tmp.cmd")
    for i, p in enumerate(Path("scales").rglob("*.scl")):
        if i % 100 == 0:
            print(i)
        analysis_dir = OUTPUT_DIR / p.relative_to("scales").with_suffix("")
        analysis_dir.mkdir(parents=True)
        for command in COMMANDS:
            output_file = analysis_dir / command.replace(" ", "_").replace("/", "-")
            cmd = "\n".join(
                ["SET PAUSE OFF", f"LOAD {p}", f"FILE {output_file}", command, "EXIT"]
            )
            cmd_file.write_text(cmd)
            subprocess.run([SCALA_PROGRAM, cmd_file], stdout=subprocess.DEVNULL, check=True)
    cmd_file.unlink()


if __name__ == "__main__":
    main()
