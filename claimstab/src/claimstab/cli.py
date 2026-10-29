from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .core import build_claim_stability, compare_claim_frameworks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claimstab")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser(
        "build",
        help="Build endpoint-dependency and claim-stability matrices",
    )
    build.add_argument("--claims", type=Path, required=True)
    build.add_argument("--reconstruction", type=Path, required=True)
    build.add_argument("--endpoints", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--alpha", type=float, default=0.05)
    compare = subparsers.add_parser(
        "compare",
        help="Compare claimstab with majority and strict multiverse rules",
    )
    compare.add_argument("--claims", type=Path, required=True)
    compare.add_argument("--reconstruction", type=Path, required=True)
    compare.add_argument("--endpoints", type=Path, required=True)
    compare.add_argument("--output-dir", type=Path, required=True)
    compare.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)

    if args.command == "build":
        paths = build_claim_stability(
            claims_path=args.claims,
            reconstruction_path=args.reconstruction,
            endpoints_path=args.endpoints,
            output_dir=args.output_dir,
            alpha=args.alpha,
        )
        for name, path in paths.items():
            print(f"{name}: {path}")
    elif args.command == "compare":
        paths = compare_claim_frameworks(
            claims_path=args.claims,
            reconstruction_path=args.reconstruction,
            endpoints_path=args.endpoints,
            output_dir=args.output_dir,
            alpha=args.alpha,
        )
        for name, path in paths.items():
            print(f"{name}: {path}")
    return 0
