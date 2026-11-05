"""SQLite under load: WAL journal, busy timeout, many threads at once, and a database file that is deleted while the
app runs (what produced "attempt to write a readonly database" when two e2e runs shared a DATA_DIR)."""
import threading
import time

from api import db, kotak
from api.config import settings


def _job(i: int) -> dict:
    return {"id": f"conc{i:04d}", "created": time.time(), "status": "queued", "title": f"t{i}", "public": False}


def test_wal_and_busy_timeout_are_on():
    conn = db._store.get()
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 15000
    assert kotak._store.get().execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_many_threads_write_and_read_without_errors():
    errors: list[BaseException] = []

    def worker(k: int) -> None:
        try:
            for n in range(25):
                job = _job(k * 100 + n)
                db.save(job)
                job["status"] = "done"
                db.save(job)
                assert db.load(job["id"])["status"] == "done"
                db.gallery()
                db.add_feedback(job["id"], 5, "", "test")
                kotak.list_family("f" * 16)
        except BaseException as e:  # noqa: BLE001 - collected and asserted below
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(k,)) for k in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not errors, errors[:3]
    assert all(db.load(f"conc{k * 100 + 24:04d}") for k in range(12))


def test_two_connections_write_the_same_file_at_once(tmp_path, monkeypatch):
    """Two processes (or the jobs and kotak modules) each hold a connection; WAL + busy timeout let both write."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    a, b = db.Store(db.SCHEMA), db.Store(db.SCHEMA)
    errors: list[BaseException] = []

    def writer(store: db.Store, prefix: str) -> None:
        try:
            for n in range(200):
                c = store.get()
                c.execute("INSERT INTO feedback(job_id, created, rating, comment, page) VALUES (?,?,?,?,?)",
                          (f"{prefix}{n}", time.time(), 4, "", "x"))
                c.commit()
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    ts = [threading.Thread(target=writer, args=(a, "a")), threading.Thread(target=writer, args=(b, "b"))]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    assert not errors, errors[:3]
    assert a.get().execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 400


def test_reconnects_when_the_database_file_is_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    store = db.Store(db.SCHEMA)
    store.get().execute("INSERT INTO feedback(job_id, created, rating, comment, page) VALUES ('x', 0, 3, '', 'p')")
    store.get().commit()
    for f in tmp_path.glob("dalang.db*"):  # another run clears DATA_DIR under the running app
        f.unlink()
    c = store.get()  # notices the file is gone and reconnects, recreating the tables
    c.execute("INSERT INTO feedback(job_id, created, rating, comment, page) VALUES ('y', 0, 4, '', 'p')")
    c.commit()
    assert [r[0] for r in c.execute("SELECT job_id FROM feedback")] == ["y"]
    assert (tmp_path / "dalang.db").exists()
