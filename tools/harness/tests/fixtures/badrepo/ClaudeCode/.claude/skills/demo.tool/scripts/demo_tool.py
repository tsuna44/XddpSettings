#!/usr/bin/env python3
"""demo_tool.py — 検査D の introspection テスト用フィクスチャスクリプト。

サブコマンド {run, stat} を持つ argparse。run は --path/--mode、stat は --path のみ。
"""
import argparse


def build_parser():
    p = argparse.ArgumentParser(prog="demo_tool.py")
    sub = p.add_subparsers(dest="cmd")
    run = sub.add_parser("run")
    run.add_argument("--path")
    run.add_argument("--mode")
    stat = sub.add_parser("stat")
    stat.add_argument("--path")
    return p


if __name__ == "__main__":
    build_parser().parse_args()
