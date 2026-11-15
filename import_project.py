#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility entry point for new movie imports. Uses full longform ingestion."""
import argparse,json
from production_cli import import_film

def main():
    p=argparse.ArgumentParser(description='New offline film project: longform cut proposals, high-res triplets, assets and director DB.')
    p.add_argument('video');p.add_argument('--out',required=True)
    args=p.parse_args()
    print(json.dumps(import_film(args.video,args.out),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
