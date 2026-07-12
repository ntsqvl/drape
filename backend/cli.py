"""DRAPE CLI harness: the week-1 exit criterion (selfie -> verdict in terminal)
and the day-1/2 live-API gates.

  python cli.py analyze selfie.jpg [--mock] [--json]
  python cli.py credit                 # remaining units + per-feature costs
  python cli.py gate selfie.jpg        # day-1/2 go/no-go probes (live API)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from drape.agent.session import DrapingSession  # noqa: E402
from drape.api.youcam_client import CLOTH, YouCamClient  # noqa: E402


def cmd_analyze(args: argparse.Namespace) -> None:
    client = YouCamClient(mock=True if args.mock else None)
    session = DrapingSession(client=client, selfie=Path(args.selfie))
    verdict = session.run()

    if args.json:
        print(json.dumps(asdict(verdict), indent=2, default=str))
        return

    print("\n=== DRAPING SESSION ===")
    for event in verdict.trace:
        extra = {k: v for k, v in event.items() if k not in ("round", "message")}
        suffix = f"  {extra}" if extra else ""
        print(f"[{event['round']:>7}] {event['message']}{suffix}")

    print("\n=== VERDICT ===")
    print(f"Season:      {verdict.season_name} -- {verdict.tagline}")
    print(f"Confidence:  {verdict.confidence} (temperature: {verdict.temperature})")
    print(f"Axes:        {verdict.profile_axes}")
    print(f"Skin today:  {verdict.skin_state}")
    print(f"Renders:     {verdict.renders_used} VTO calls")
    print(f"\nBest drape:  {verdict.best.name} ({verdict.best.score.score}) -> {verdict.best.render_path}")
    print(f"Worst drape: {verdict.worst.name} ({verdict.worst.score.score}) -> {verdict.worst.render_path}")
    print("\nYour palette, ranked:")
    for p in verdict.palette:
        print(f"  {p['score']:5.1f}  {p['hex']}  {p['name']:<18} {'; '.join(p['reasons'])}")


def cmd_credit(args: argparse.Namespace) -> None:
    client = YouCamClient()
    print(json.dumps({"credit": client.credit(), "feature_cost": client.feature_cost()}, indent=2))


def cmd_gate(args: argparse.Namespace) -> None:
    """Day-1/2 go/no-go: real costs, schema check, drape render consistency."""
    from drape import config
    from drape.api import cloth_vto, skin_tone
    from drape.colorlab import extract, seasons
    from drape.colorlab.lab import delta_e, hex_to_lab

    client = YouCamClient()
    print("1) unit costs:")
    print(json.dumps(client.feature_cost(), indent=2))

    print("\n2) skin-tone-analysis schema:")
    colors = skin_tone.analyze(client, args.selfie)
    print(f"   {colors}")

    print("\n3) drape consistency probe (4 recolored drapes, same garment):")
    probes = ["probe_warm_gold", "probe_cool_orchid", "probe_peach", "probe_espresso"]
    skin_lab = hex_to_lab(colors.skin)
    handle = client.upload(CLOTH, args.selfie)
    for pid in probes:
        drape = config.DRAPES_DIR / f"{pid}.jpg"
        render = cloth_vto.try_on(client, handle, drape)
        measured_hex, measured_lab = extract.garment_color(render, skin=skin_lab)
        requested_hex, _ = seasons.all_drape_colors()[pid]
        drift = delta_e(measured_lab, hex_to_lab(requested_hex))
        print(f"   {pid}: requested {requested_hex}, measured {measured_hex}, deltaE {drift:.1f} -> {render}")
    print("\nInspect the four renders: same garment shape across colors = GO.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="drape")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_analyze = sub.add_parser("analyze", help="run a full draping session")
    p_analyze.add_argument("selfie")
    p_analyze.add_argument("--mock", action="store_true", help="force offline mock mode")
    p_analyze.add_argument("--json", action="store_true")
    p_analyze.set_defaults(func=cmd_analyze)

    p_credit = sub.add_parser("credit", help="remaining units + feature costs")
    p_credit.set_defaults(func=cmd_credit)

    p_gate = sub.add_parser("gate", help="day-1/2 live-API go/no-go probes")
    p_gate.add_argument("selfie")
    p_gate.set_defaults(func=cmd_gate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
