#!/usr/bin/env python3
"""读取全国探针日志并测量阶段墙钟；不生成游戏源码或复制候选／抽选业务。"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import re
import time


MARKER = re.compile(r"\[(\d{2}):(\d{2}):(\d{2})\].*TCA_MNP (START|END) (\w+)")
PHASES = {"scan32", "freeze32", "demand", "national_draw128", "create2048", "stress_draw512", "stress_exhaust1536"}


def summarize(log: str, arrivals: dict[str, float] | None = None) -> dict:
    """只解释引擎直接输出的计数及边界，不重新判断任何人物资格。"""
    starts, durations = {}, {}
    for match in MARKER.finditer(log):
        hour, minute, second, edge, name = match.groups()
        seconds = int(hour) * 3600 + int(minute) * 60 + int(second)
        if edge == "START":
            starts[name] = seconds
        elif name in starts:
            elapsed = (seconds - starts[name]) % 86400
            row = {"log_wall_seconds": elapsed,
                   "log_resolution_seconds": 1,
                   "wall_seconds_lower": max(0, elapsed - 1),
                   "wall_seconds_upper": elapsed + 1}
            if arrivals and f"START {name}" in arrivals and f"END {name}" in arrivals:
                row["arrival_seconds"] = arrivals[f"END {name}"] - arrivals[f"START {name}"]
                row["arrival_not_batched"] = row["arrival_seconds"] > 0
            durations[name] = row
    demand, demand_kinds = collections.Counter(), collections.Counter()
    pending_route, pending_kind = None, None
    for line in log.splitlines():
        if "TCA_MNP DEMAND_KIND " in line:
            pending_kind = line.rsplit(" ", 1)[-1]
        elif "TCA_MNP DEMAND_ROUTE " in line:
            pending_route = line.rsplit(" ", 1)[-1]
        elif "TCA_MNP DEMAND_BAND " in line and pending_route:
            demand[f"{pending_route}_{line.rsplit(' ', 1)[-1]}"] += 1
            if pending_kind:
                demand_kinds[f"{pending_kind}_{pending_route}_{line.rsplit(' ', 1)[-1]}"] += 1
            pending_route = None
            pending_kind = None
    # 原生debug_log_scopes直接记录命名数值；不依赖动态本地化解析变量。
    snapshots, pending_snapshot = [], None
    scalar = re.compile(r"^tca_mnp_report_(population|candidates|route|level):\s*(-?\d+(?:\.\d+)?)\s*$")
    for line in log.splitlines():
        if line.endswith("TCA_MNP TOTAL"):
            pending_snapshot = {"kind": "TOTAL"}
        elif line.endswith("TCA_MNP BAND"):
            pending_snapshot = {"kind": "BAND"}
        elif pending_snapshot:
            match = scalar.match(line)
            if match:
                pending_snapshot[match.group(1)] = float(match.group(2))
                needed = {"population", "candidates"} | ({"route", "level"} if pending_snapshot["kind"] == "BAND" else set())
                if needed <= pending_snapshot.keys():
                    snapshots.append(pending_snapshot)
                    pending_snapshot = None
    markers = [line.split("TCA_MNP ", 1)[1] for line in log.splitlines()
               if "TCA_MNP TOTAL " in line or "TCA_MNP BAND " in line]
    for row in snapshots:
        prefix = row["kind"]
        if prefix == "BAND":
            prefix += f" route={row['route']:g} native_level={row['level']:g}"
        markers.append(f"{prefix} population={row['population']:g} preliminary_candidates={row['candidates']:g}")
    return {"phases": durations, "snapshot": markers,
            "native_snapshot_scalars": snapshots,
            "all_phase_pairs_present": PHASES <= durations.keys(),
            "snapshot_numbers_present": len(markers) == 19 and all(re.search(r"population=\d", line) and re.search(r"preliminary_candidates=\d", line) for line in markers),
            "demand_by_route_band": dict(demand),
            "demand_by_kind_route_band": dict(demand_kinds),
            "assertions_passed": len(re.findall(r"TCA_TEST CHECK_PASS tca_test_merit_national_scale \d+", log)),
            "assertions_failed": len(re.findall(r"TCA_TEST CHECK_FAIL tca_test_merit_national_scale \d+", log)),
            "case_pass": "TCA_TEST PASS tca_test_merit_national_scale" in log,
            "timing_caveat": "Log timestamps have one-second resolution. Arrival durations include flush and polling jitter; compare with wall-clock bounds, and reject implausibly batched arrival timing. Creation and startup are separate from measured algorithm phases."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path, help="固定运行根目录或具体run目录；不读取latest.json")
    parser.add_argument("--watch", action="store_true", help="每10ms尾随日志，记录标记抵达的单调时钟")
    parser.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    deadline, arrivals, log = time.monotonic() + args.timeout, {}, ""
    offset, fragment = 0, ""
    while True:
        matches = list(args.run_root.glob("run-*/logs/debug.log"))
        direct = args.run_root / "logs/debug.log"
        if direct.exists():
            matches.append(direct)
        if len(matches) > 1:
            raise SystemExit("运行根目录含多个局，请显式指定某个run目录")
        if matches:
            # 只读取新增字节，避免10ms全文件重读随日志增长而扰动被测游戏。
            with matches[0].open("rb") as stream:
                stream.seek(offset)
                data = stream.read()
                offset = stream.tell()
            fragment += data.decode("utf-8", errors="replace")
            lines = fragment.splitlines(keepends=True)
            fragment = ""
            if lines and not lines[-1].endswith("\n"):
                fragment = lines.pop()
            added = "".join(lines)
            log += added
            now = time.monotonic()
            for match in MARKER.finditer(added):
                edge, name = match.group(4, 5)
                arrivals.setdefault(f"{edge} {name}", now)
            if "TCA_TEST PASS tca_test_merit_national_scale" in log or "TCA_TEST FAIL tca_test_merit_national_scale" in log:
                break
        if not args.watch or time.monotonic() >= deadline:
            break
        time.sleep(0.01)
    report = summarize(log, arrivals if args.watch else None)
    if args.watch:
        report["marker_arrival_monotonic_seconds"] = arrivals
        report["poll_interval_seconds"] = 0.01
    report["run_dir"] = str(matches[0].parent.parent) if matches else None
    if matches:
        # 后续只读日志复核另存摘要，不能覆盖现场watch留下的抵达时间证据。
        output = matches[0].parent.parent / ("merit_national_measurement.json" if args.watch else "merit_national_log_summary.json")
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
