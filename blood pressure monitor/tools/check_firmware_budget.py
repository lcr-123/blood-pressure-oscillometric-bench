"""Read-only Keil map/callgraph gate. Run after rebuilding the firmware."""
import argparse
import json
from pathlib import Path
import re

PROJECT = Path(__file__).resolve().parents[1]


def check_budget(map_text, graph_text, startup_text):
    region = re.search(r"Execution Region RW_IRAM1 .*?Size: (0x[0-9a-fA-F]+), Max: (0x[0-9a-fA-F]+)", map_text)
    stack = re.search(r"Stack_Size\s+EQU\s+(0x[0-9a-fA-F]+)", startup_text)
    peak = re.search(r"Maximum Stack Usage\s*=\s*(\d+) bytes", graph_text)
    if not all((region, stack, peak)):
        raise ValueError("Missing RAM region, startup stack size, or callgraph maximum")
    used, limit = (int(value, 16) for value in region.groups())
    reserved, known_peak = int(stack.group(1), 16), int(peak.group(1))
    # This is a conservative static budget, not a runtime high-water measurement.
    # Indirect calls/cycles and interrupt nesting still need target validation.
    if limit != 65536 or limit - used < 2048:
        raise ValueError(f"RAM headroom below 2048 bytes: {used}/{limit}")
    if known_peak + 1024 > reserved:
        raise ValueError(f"Known stack {known_peak} + 1024 IRQ/unknown reserve > {reserved}")
    if not re.search(r"0x[0-9a-fA-F]+\s+-\s+0x00001000\s+Zero\s+RW\s+\d+\s+STACK", map_text):
        raise ValueError("Map does not contain the expected 4096-byte stack")
    return {"ram_used": used, "ram_limit": limit, "ram_headroom": limit - used,
            "stack_reserved": reserved, "stack_known_peak": known_peak,
            "stack_extra_reserve": 1024, "runtime_high_water_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=PROJECT / "MDK-ARM/blood pressure monitor")
    args = parser.parse_args()
    map_file = args.build_dir / "blood pressure monitor.map"
    graph_file = args.build_dir / "blood pressure monitor.htm"
    startup = PROJECT / "MDK-ARM/startup_stm32f103xe.s"
    artifacts = (map_file, graph_file)
    # Prevent an old passing build from masking a new source-level regression.
    inputs = [*PROJECT.glob("Core/Src/*.c"), *PROJECT.glob("Core/Inc/*.h"), startup,
              PROJECT / "MDK-ARM/blood pressure monitor.uvprojx"]
    if min(file.stat().st_mtime_ns for file in artifacts) < max(file.stat().st_mtime_ns for file in inputs):
        raise ValueError("Build artifacts are older than firmware inputs; rebuild first")
    report = check_budget(map_file.read_text(encoding="utf-8", errors="replace"),
                          graph_file.read_text(encoding="utf-8", errors="replace"),
                          startup.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
