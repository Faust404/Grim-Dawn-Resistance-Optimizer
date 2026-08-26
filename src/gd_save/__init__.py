"""Shipped Grim Dawn save pipeline (stdlib only).

The records database is too large to commit raw (514 MB, over GitHub's blob
limit), so records.db.gz (53 MB) is the committed artifact. records.db is
extracted once, lazily, into the package dir (system tempdir fallback when the
package dir is read-only), then opened read-only. Extraction is atomic
(temp file + os.replace), so concurrent first uses — e.g. four gunicorn
workers — race safely: last writer wins, readers never see a partial file.
"""
import gzip
import os
import shutil
import sqlite3
import tempfile
import threading
import time

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_NAME = 'records.db'
_GZ_NAME = 'records.db.gz'
_lock = threading.Lock()
_db_path = None


def _decompress(gz_path, target):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target) or None,
                               suffix='.tmp')
    os.close(fd)
    try:
        with gzip.open(gz_path, 'rb') as src, open(tmp, 'wb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        os.replace(tmp, target)  # atomic on POSIX and NTFS
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def get_db_path():
    """Return the path of an extracted records.db, extracting it on first use."""
    global _db_path
    if _db_path is not None and os.path.exists(_db_path):
        return _db_path
    with _lock:  # serializes only within this process; cross-process is safe
        if _db_path is not None and os.path.exists(_db_path):
            return _db_path
        target = os.path.join(_PKG_DIR, _DB_NAME)
        gz = os.path.join(_PKG_DIR, _GZ_NAME)
        if not os.path.exists(target):
            if not os.path.exists(gz):
                raise RuntimeError(f'{_GZ_NAME} missing in {_PKG_DIR}')
            try:
                _decompress(gz, target)
            except OSError:  # read-only package dir -> tempdir
                fd, target = tempfile.mkstemp(prefix='gd_save_', suffix='.db')
                os.close(fd)
                os.unlink(target)
                _decompress(gz, target)
        _db_path = target
        return _db_path


def connect_db():
    """Open records.db read-only; retries briefly to absorb a concurrent
    first-time extraction in a sibling gunicorn worker."""
    path = None
    for attempt in range(3):
        try:
            if path is None:
                path = get_db_path()
            uri = 'file:' + path.replace('\\', '/') + '?mode=ro'
            return sqlite3.connect(uri, uri=True)
        except sqlite3.OperationalError:
            path = None
            time.sleep(0.25 * (attempt + 1))
    raise
