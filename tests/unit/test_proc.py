from runlens.collectors.proc import ProcCollector


def make_proc(tmp_path):
    process = tmp_path / "123"
    process.mkdir()
    (process / "status").write_text("VmRSS:\t12 kB\nVmHWM:\t20 kB\nThreads:\t3\n")
    (process / "fd").mkdir()
    for fd in range(4):
        (process / "fd" / str(fd)).touch()
    # stat fields 3..13, followed by utime and stime (14 and 15).
    (process / "stat").write_text("123 (a tricky ) name) S " + "0 " * 10 + "7 9 0\n")
    return process


def test_proc_fields_and_comm_parentheses(tmp_path):
    make_proc(tmp_path)
    sample = ProcCollector(tmp_path).sample(123, 456)
    assert sample.elapsed_ns == 456
    assert sample.rss_bytes == 12 * 1024
    assert sample.rss_hwm_bytes == 20 * 1024
    assert sample.threads == 3
    assert sample.fd_count == 4
    assert sample.cpu_user_ticks == 7
    assert sample.cpu_system_ticks == 9
    assert not sample.errors


def test_process_disappeared(tmp_path):
    sample = ProcCollector(tmp_path).sample(999, 0)
    assert sample.rss_bytes is None
    assert sample.fd_count is None
    assert len(sample.errors) == 3


def test_non_utf8_process_name(tmp_path):
    proc = make_proc(tmp_path)
    (proc / "status").write_bytes(b"Name:\t\xff\nVmRSS: 1 kB\nVmHWM: 2 kB\nThreads: 1\n")
    (proc / "stat").write_bytes(b"123 (\xff) S " + b"0 " * 10 + b"7 9\n")
    sample = ProcCollector(tmp_path).sample(123, 0)
    assert sample.rss_bytes == 1024 and sample.cpu_user_ticks == 7
    assert not sample.errors


def test_invalid_and_missing_fields_do_not_hide_fd_data(tmp_path):
    proc = make_proc(tmp_path)
    (proc / "status").write_text("VmRSS: 3 MB\nThreads: -1\n")
    (proc / "stat").write_text("invalid")
    sample = ProcCollector(tmp_path).sample(123, 0)
    assert sample.rss_bytes is None and sample.threads is None
    assert sample.rss_hwm_bytes is None
    assert sample.fd_count == 4
    assert len(sample.errors) == 4


def test_permission_denied_is_explicit(tmp_path, monkeypatch):
    make_proc(tmp_path)

    def denied(path):
        raise PermissionError("denied")

    monkeypatch.setattr("runlens.collectors.proc.os.scandir", denied)
    sample = ProcCollector(tmp_path).sample(123, 0)
    assert sample.fd_count is None
    assert sample.rss_bytes == 12 * 1024
    assert "fd: PermissionError" in sample.errors
