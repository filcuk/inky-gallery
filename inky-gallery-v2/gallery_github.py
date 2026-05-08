import gc
import os
import time

import ujson
from urllib import urequest

import gallery_common as gc_common
from gallery_log import log


def _encode_path_segment(seg):
    r = []
    for c in seg:
        if ("a" <= c <= "z") or ("A" <= c <= "Z") or ("0" <= c <= "9") or c in "-._":
            r.append(c)
        elif c == " ":
            r.append("%20")
        else:
            r.append("%%%02X" % ord(c))
    return "".join(r)


def _contents_base_url(owner, repo, path, ref):
    base = "https://api.github.com/repos/%s/%s" % (owner, repo)
    path = path.strip("/")
    if path:
        parts = [_encode_path_segment(p) for p in path.split("/") if p]
        return base + "/contents/" + "/".join(parts) + "?ref=" + ref
    return base + "/contents?ref=" + ref


def _headers_list(pat):
    return {
        "User-Agent": "inky-gallery-v2",
        "Authorization": "Bearer " + pat,
        "Accept": "application/vnd.github+json",
    }


def _headers_raw(pat):
    return {
        "User-Agent": "inky-gallery-v2",
        "Authorization": "Bearer " + pat,
        "Accept": "application/vnd.github.v3.raw",
    }


def _stream_to_file(socket, dest_path):
    with open(dest_path, "wb") as f:
        buf = bytearray(1024)
        try:
            while True:
                n = socket.readinto(buf)
                if n == 0:
                    break
                f.write(memoryview(buf)[:n])
        except AttributeError:
            while True:
                chunk = socket.read(1024)
                if not chunk:
                    break
                f.write(chunk)
        del buf
    socket.close()
    gc.collect()


def _file_api_url(owner, repo, file_path, ref):
    base = "https://api.github.com/repos/%s/%s" % (owner, repo)
    parts = [_encode_path_segment(p) for p in file_path.split("/") if p]
    return base + "/contents/" + "/".join(parts) + "?ref=" + ref


def sync_from_github(cfg):
    """Download JPEGs from cfg's GitHub folder into GALLERY_SD_FOLDER.

    Returns (new_files, err). new_files is a list of SD paths that were newly downloaded.
    """
    pat = getattr(cfg, "GITHUB_PAT", "") or ""
    if not pat.strip():
        return [], "GITHUB_PAT missing"

    owner = cfg.GITHUB_OWNER
    repo = cfg.GITHUB_REPO
    branch = getattr(cfg, "GITHUB_BRANCH", "main")
    folder = getattr(cfg, "GITHUB_PATH", "") or ""

    if not gc_common.ensure_sd():
        return [], "SD: %s" % gc_common.friendly_sd_message(gc_common.sd_mount_error() or "")

    dest_root = cfg.GALLERY_SD_FOLDER.rstrip("/")
    gc_common.ensure_dir(dest_root)

    list_url = _contents_base_url(owner, repo, folder, branch)
    log("GitHub: listing", "%s/%s" % (owner, repo), "ref=", branch, "path=", folder or "(root)")
    try:
        sock = urequest.urlopen(list_url, headers=_headers_list(pat))
        body = sock.read()
        sock.close()
    except OSError as e:
        gc.collect()
        return [], "GitHub list failed: %s" % e

    try:
        data = ujson.loads(body)
    except ValueError:
        gc.collect()
        return [], "Bad JSON from GitHub"

    del body
    gc.collect()

    if isinstance(data, dict) and data.get("type") == "file":
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        return [], "Unexpected GitHub response"

    folder_clean = folder.strip("/")
    new_files = []
    total = 0
    downloaded = 0
    skipped = 0
    remote_names = set()

    for ent in entries:
        if ent.get("type") != "file":
            continue
        name = ent.get("name", "")
        low = name.lower()
        if not (low.endswith(".jpg") or low.endswith(".jpeg")):
            continue
        remote_names.add(name)
        total += 1
        rel_path = ent.get("path")
        if not rel_path:
            rel_path = (folder_clean + "/" + name) if folder_clean else name
        remote_size = ent.get("size")
        dest_path = dest_root + "/" + name
        try:
            st = os.stat(dest_path)
            if remote_size is not None and st[6] == remote_size:
                skipped += 1
                log("GitHub: skip", name, "(already downloaded)")
                continue
        except OSError:
            pass

        file_url = _file_api_url(owner, repo, rel_path, branch)
        log("GitHub: download", name, "size=", remote_size if remote_size is not None else "?")
        try:
            fsock = urequest.urlopen(file_url, headers=_headers_raw(pat))
            _stream_to_file(fsock, dest_path)
        except OSError as e:
            gc.collect()
            return new_files, "Download failed %s: %s" % (name, e)
        new_files.append(dest_path)
        downloaded += 1
        log("GitHub: saved", dest_path)
        gc.collect()

    # If files were deleted upstream, move local copies out of the slideshow folder.
    deleted_dir = dest_root + "/deleted"
    try:
        gc_common.ensure_dir(deleted_dir)
    except Exception:
        pass
    moved = 0
    try:
        for n in os.listdir(dest_root):
            if n.startswith(".") or n == "deleted":
                continue
            low = n.lower()
            if not (low.endswith(".jpg") or low.endswith(".jpeg")):
                continue
            if n in remote_names:
                continue
            src = dest_root + "/" + n
            dst = deleted_dir + "/" + n
            try:
                os.stat(dst)
                # Avoid overwrite; add a timestamp suffix.
                ts = str(int(time.time())) if time.time() >= 1e9 else "0"
                base = n
                dot = base.rfind(".")
                if dot > 0:
                    dst = deleted_dir + "/" + base[:dot] + "." + ts + base[dot:]
                else:
                    dst = deleted_dir + "/" + base + "." + ts
            except OSError:
                pass
            try:
                os.rename(src, dst)
                moved += 1
                log("GitHub: moved deleted", src, "->", dst)
            except OSError as e:
                log("GitHub: move failed", src, type(e).__name__, e)
    except OSError:
        pass

    # Keep slideshow playlist clean if we moved anything.
    if moved:
        try:
            items = gc_common.load_playlist(dest_root)
            if items:
                pruned = []
                for p in items:
                    try:
                        os.stat(p)
                        pruned.append(p)
                    except OSError:
                        pass
                gc_common.save_playlist(dest_root, pruned)
        except Exception:
            pass

    log("GitHub: done", "listed =", total, "downloaded =", downloaded, "skipped =", skipped)
    try:
        with open(dest_root + "/.last_github_sync", "w") as f:
            f.write(str(int(time.time())))
    except OSError:
        pass

    gc.collect()
    return new_files, None


def should_sync(cfg):
    interval_s = int(getattr(cfg, "GITHUB_SYNC_INTERVAL_MINUTES", 360)) * 60
    marker = cfg.GALLERY_SD_FOLDER.rstrip("/") + "/.last_github_sync"
    try:
        with open(marker, "r") as f:
            last = int(f.read())
    except (OSError, ValueError):
        last = 0
    now = time.time()
    if now < 1e9:
        return True
    return (now - last) >= interval_s
