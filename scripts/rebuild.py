#!/usr/bin/env python3
"""扫描 debs/ 下所有 .deb，重建 APT 源索引。

每个包只保留版本号最高的一条进入索引。
生成 Packages 及 .gz/.bz2/.xz 三种压缩形式，外加 Release 元信息。
"""
import bz2
import gzip
import hashlib
import io
import lzma
import os
import sys
import tarfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBS = os.path.join(ROOT, "debs")

RELEASE_META = """Origin: Shutao Repo
Label: 蜀洮的源
Suite: stable
Version: 1.0
Codename: ios
Architectures: iphoneos-arm64
Components: main
Description: 蜀洮自用的越狱插件源
"""


def ar_members(blob):
    out = {}
    off = 8
    while off + 60 <= len(blob):
        hdr = blob[off:off + 60]
        name = hdr[0:16].decode("ascii", "replace").strip().rstrip("/")
        try:
            size = int(hdr[48:58].decode("ascii", "replace").strip() or "0")
        except ValueError:
            break
        out[name] = blob[off + 60:off + 60 + size]
        off += 60 + size + (size % 2)
    return out


def read_control(deb_path):
    with open(deb_path, "rb") as fh:
        blob = fh.read()
    members = ar_members(blob)
    ctrl_key = next((k for k in members if k.startswith("control.tar")), None)
    if not ctrl_key:
        return {}
    try:
        tar = tarfile.open(fileobj=io.BytesIO(members[ctrl_key]), mode="r:*")
    except Exception:
        return {}
    target = None
    for name in tar.getnames():
        if name.lstrip("./").split("/")[-1] == "control":
            target = name
            break
    if not target:
        return {}
    text = tar.extractfile(target).read().decode("utf-8", "replace")

    fields = {}
    key = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line[0] in " \t" and key:
            fields[key] += " " + line.strip()
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            fields[key.strip()] = val.strip()
    return fields


def version_key(v):
    parts = []
    for chunk in v.replace("-", ".").replace("_", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return parts


def build_stanza(deb_path, rel_name):
    fields = read_control(deb_path)
    if not fields.get("Package"):
        return None

    size = os.path.getsize(deb_path)
    with open(deb_path, "rb") as fh:
        data = fh.read()

    lines = []
    for key in ("Package", "Name", "Version", "Architecture", "Description",
                "Depends", "Conflicts", "Replaces", "Provides", "Section",
                "Priority", "Maintainer", "Author", "Installed-Size"):
        if key in fields:
            lines.append("%s: %s" % (key, fields[key]))

    lines.append("Filename: ./debs/%s" % rel_name)
    lines.append("Size: %d" % size)
    lines.append("SHA256: %s" % hashlib.sha256(data).hexdigest())
    lines.append("SHA1: %s" % hashlib.sha1(data).hexdigest())
    lines.append("MD5sum: %s" % hashlib.md5(data).hexdigest())
    return "\n".join(lines)


def main():
    if not os.path.isdir(DEBS):
        print("debs/ not found")
        return 1

    names = [f for f in sorted(os.listdir(DEBS))
             if f.endswith(".deb") and os.path.isfile(os.path.join(DEBS, f))]
    if not names:
        print("no .deb in debs/")
        return 1

    best = {}
    for name in names:
        path = os.path.join(DEBS, name)
        fields = read_control(path)
        pkg = fields.get("Package")
        if not pkg:
            print("  skip (no Package): %s" % name)
            continue
        ver = fields.get("Version", "0")
        key = version_key(ver)
        if pkg not in best or key > best[pkg][0]:
            best[pkg] = (key, name, ver)

    stanzas = []
    for pkg in sorted(best):
        _, name, ver = best[pkg]
        stanza = build_stanza(os.path.join(DEBS, name), name)
        if stanza:
            stanzas.append(stanza)
            print("  %-34s %-12s %s" % (pkg, ver, name))

    if not stanzas:
        print("nothing to index")
        return 1

    raw = ("\n\n".join(stanzas) + "\n\n").encode("utf-8")  # 标准格式：以空行结尾

    with open(os.path.join(ROOT, "Packages"), "wb") as fh:
        fh.write(raw)
    with open(os.path.join(ROOT, "Packages.gz"), "wb") as fh:
        fh.write(gzip.compress(raw))
    with open(os.path.join(ROOT, "Packages.bz2"), "wb") as fh:
        fh.write(bz2.compress(raw))
    with open(os.path.join(ROOT, "Packages.xz"), "wb") as fh:
        fh.write(lzma.compress(raw))
    # Release 需要带上 Packages 各格式的校验和。缺这些段时，
    # 部分 APT 版本会认为索引不可信而跳过整个源。
    release_lines = [RELEASE_META.rstrip("\n")]
    release_lines.append("Date: %s" % time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))

    files_info = []
    for fname in ("Packages", "Packages.gz", "Packages.bz2", "Packages.xz"):
        p = os.path.join(ROOT, fname)
        if not os.path.isfile(p):
            continue
        with open(p, "rb") as fh:
            blob = fh.read()
        files_info.append((fname, len(blob),
                           hashlib.md5(blob).hexdigest(),
                           hashlib.sha1(blob).hexdigest(),
                           hashlib.sha256(blob).hexdigest()))

    release_lines.append("MD5Sum:")
    for name, size, md5v, _, _ in files_info:
        release_lines.append(" %s %d %s" % (md5v, size, name))
    release_lines.append("SHA1:")
    for name, size, _, sha1v, _ in files_info:
        release_lines.append(" %s %d %s" % (sha1v, size, name))
    release_lines.append("SHA256:")
    for name, size, _, _, sha256v in files_info:
        release_lines.append(" %s %d %s" % (sha256v, size, name))

    with open(os.path.join(ROOT, "Release"), "wb") as fh:
        fh.write(("\n".join(release_lines) + "\n").encode("utf-8"))

    print("")
    print("index built: %d packages" % len(stanzas))
    print("  Packages %d bytes" % len(raw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
