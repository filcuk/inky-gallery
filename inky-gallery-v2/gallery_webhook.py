"""GET webhook notifications after GitHub sync (optional; configured in gallery_config)."""

import gc

import ubinascii
from urllib import urequest

from gallery_log import log


def _qp(s):
    out = []
    for c in str(s):
        o = ord(c)
        if (
            ("a" <= c <= "z")
            or ("A" <= c <= "Z")
            or ("0" <= c <= "9")
            or c in "-._~"
        ):
            out.append(c)
        elif o < 128:
            out.append("%%%02X" % o)
        else:
            for b in c.encode("utf-8"):
                out.append("%%%02X" % b)
    return "".join(out)


def _url_with_query(base_url, params):
    parts = []
    for k, v in params.items():
        if v is None:
            continue
        parts.append(_qp(k) + "=" + _qp(v))
    q = "&".join(parts)
    if "?" in base_url:
        return base_url + "&" + q
    return base_url + "?" + q


def notify_github_sync(cfg, success, downloaded, error=None):
    """GET cfg.WEBHOOK_URL with query params: name, sync (ok|fail), downloaded (if ok), error (if fail).

    Uses HTTP Basic Auth when WEBHOOK_USER / WEBHOOK_PASSWORD are set.
    Never raises: any failure is logged and ignored so the gallery keeps running.
    """
    sock = None
    try:
        url = (getattr(cfg, "WEBHOOK_URL", "") or "").strip()
        if not url:
            return

        name = getattr(cfg, "NAME", "") or ""
        params = {
            "name": name,
            "sync": "ok" if success else "fail",
        }
        if success:
            try:
                params["downloaded"] = str(int(downloaded))
            except (TypeError, ValueError):
                params["downloaded"] = "0"
        else:
            if error:
                params["error"] = str(error)[:200]

        full = _url_with_query(url, params)
        headers = {}
        user = (getattr(cfg, "WEBHOOK_USER", "") or "").strip()
        pwd = getattr(cfg, "WEBHOOK_PASSWORD", "") or ""
        if user or pwd:
            try:
                raw = ubinascii.b2a_base64(("%s:%s" % (user, pwd)).encode("utf-8")).decode()
                raw = raw.replace("\n", "").replace("\r", "")
                headers["Authorization"] = "Basic " + raw
            except Exception:
                pass

        try:
            log("Webhook: sync report", params.get("sync"), "name=", name)
        except Exception:
            pass
        sock = urequest.urlopen(full, headers=headers)
    except Exception as e:
        try:
            log("Webhook: failed (ignored)", type(e).__name__, e)
        except Exception:
            pass
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
    try:
        gc.collect()
    except Exception:
        pass
