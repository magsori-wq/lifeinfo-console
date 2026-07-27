#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자격증명 스캐너 — 커밋 전에 비밀이 섞였는지 검사한다.

왜 파이썬으로 분리했는가 (2026-07-27):
  원래는 backup_studio.bat 안에서 PowerShell 한 줄로 처리했다. 실제로 돌려보니
  batch 의 ^ 줄바꿈과 따옴표 이스케이프가 깨져 PowerShell 파서 오류가 났고,
  그런데도 스크립트는 "clean - no credential patterns found" 를 출력했다.
  검사가 아예 실행되지 않았는데 통과로 보고한 것이다 — 최악의 실패 방식이다.
  파이썬 파일로 분리하면 이스케이프 문제가 없고, 같은 코드를 그대로 테스트할 수 있다.

판정 원칙
  · 변수명·주석은 통과시키고 실제 비밀값 형태만 잡는다.
    (os.environ["CLIENT_SECRET"] 는 올바른 코드다. 이것까지 막으면 매번 차단되어
     백업이 영구히 불가능해진다.)
  · 파일명·경로는 넉넉하게 잡는다. 이름에 token/secret/credential 이 들어가거나
    .secrets/ 같은 폴더 안에 있으면 내용과 무관하게 보고한다.
  · 판단이 안 되면 통과시키지 않는다(fail-closed).

사용:
    python scan_secrets.py <검사할_폴더>
    python scan_secrets.py <폴더> --json

종료 코드: 0 = 깨끗함, 1 = 의심 항목 발견, 2 = 검사 자체 실패(통과로 취급하지 말 것)
"""

import argparse
import json
import os
import re
import sys

# --- 파일명·경로 규칙 (넓게 잡는다) --------------------------------
# blogger_token.json 처럼 접두어가 붙는 경우가 실제로 있었다.
# token*.json 식으로 앞을 고정하면 놓친다 -> 양쪽 와일드카드로 본다.
NAME_PAT = re.compile(
    r"(token|secret|credential|client[_-]?secret|service[_-]?account|oauth|"
    r"refresh|apikey|api[_-]key|passwd|password)", re.I)
NAME_EXT = {".json", ".txt", ".ini", ".cfg", ".yaml", ".yml", ".env", ".pickle",
            ".pem", ".key", ".p12", ".pfx", ""}
SECRET_DIRS = {".secrets", "secrets", ".credentials", "credentials", ".keys"}

# --- 내용 규칙 (실제 비밀값 형태만) --------------------------------
CONTENT_PAT = [
    ("PEM 개인키", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("Google client_id 실값", re.compile(r"[0-9]{10,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com")),
    ("Google client_secret", re.compile(r"GOCSPX-[A-Za-z0-9_\-]{10,}")),
    ("client_secret 값", re.compile(r'"client_secret"\s*:\s*"[^"]{8,}"')),
    ("refresh_token 값", re.compile(r'"refresh_token"\s*:\s*"[^"]{15,}"')),
    ("access_token 값", re.compile(r'"access_token"\s*:\s*"[^"]{15,}"')),
    ("private_key 값", re.compile(r'"private_key"\s*:\s*"-----BEGIN')),
    ("Google OAuth refresh 형식", re.compile(r"1//[0-9A-Za-z_\-]{30,}")),
    ("AWS 액세스키", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack 토큰", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}")),
]

TEXT_EXT = {".json", ".txt", ".py", ".bat", ".ps1", ".md", ".cfg", ".ini",
            ".yaml", ".yml", ".env", ".sh", ".html", ".js"}
MAX_BYTES = 3_000_000


def scan(root):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        # .git 내부는 검사에서 제외(작업물이 아님)
        dirnames[:] = [d for d in dirnames if d != ".git"]
        rel_dir = os.path.relpath(dirpath, root)
        parts = {p.lower() for p in rel_dir.replace("\\", "/").split("/")}

        in_secret_dir = bool(parts & SECRET_DIRS)
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            base, ext = os.path.splitext(fn)
            ext = ext.lower()

            if in_secret_dir:
                findings.append({"file": rel, "why": "비밀 전용 폴더 안에 있음", "kind": "path"})
                continue
            if NAME_PAT.search(base) and ext in NAME_EXT:
                findings.append({"file": rel, "why": "파일명이 자격증명 형태", "kind": "name"})
                continue
            if ext in {".pem", ".key", ".p12", ".pfx"}:
                findings.append({"file": rel, "why": "키·인증서 확장자", "kind": "name"})
                continue

            if ext not in TEXT_EXT:
                continue
            try:
                if os.path.getsize(full) > MAX_BYTES:
                    continue
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for label, rx in CONTENT_PAT:
                if rx.search(text):
                    findings.append({"file": rel, "why": "내용에 %s" % label, "kind": "content"})
                    break
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print("[검사 실패] 폴더가 없다: %s" % args.root)
        return 2

    try:
        findings = scan(args.root)
    except Exception as e:
        print("[검사 실패] %s: %s" % (type(e).__name__, e))
        print("  -> 통과로 취급하지 말 것. 원인을 고친 뒤 다시 검사하라.")
        return 2

    if args.json:
        print(json.dumps({"count": len(findings), "findings": findings},
                         ensure_ascii=False, indent=1))
    else:
        if not findings:
            print("깨끗함 — 자격증명으로 보이는 항목 없음 (%s)" % args.root)
        else:
            print("자격증명 의심 항목 %d개:" % len(findings))
            for f in findings:
                print("   [%s] %s" % (f["why"], f["file"]))
            print()
            print("이 파일들은 커밋하면 안 된다. 처리 방법:")
            print("  · 토큰·키 파일이면 스테이징 폴더에서 삭제하고 .gitignore 에 추가")
            print("  · 코드에 값이 박혀 있으면 환경변수에서 읽도록 바꾼 뒤 다시 검사")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
