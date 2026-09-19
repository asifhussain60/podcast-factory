"""Fail fast, and say what to do, BEFORE any remote Cloudflare step.

2026-09-19, isaf-al-talib: every remote read and write came back "Authentication error
[code: 10000]" from deep inside publish, and the only clue was a stack of wrangler output. The
token WAS recognised (`wrangler whoami` succeeds) but lacked permission for D1/R2 — a state the
existing account check cannot see. This probes the three things a publish needs, one cheap call
each, names the failing one, and turns Cloudflare's error into a remedy. Never prints the token.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _cloudflare_preflight as cf  # noqa: E402

TOKEN = "Zx3-Qw9_Lm4pRt7Vb2Nc8Ka5Jd6Hs1Yf0GeUiOoA"  # 40 chars, the shape of a real API token
ACCOUNT = "19cb05067ea7e704f94481df1685ec51"
AUTH_ERR = "✘ [ERROR] A request to the Cloudflare API failed.\n  Authentication error [code: 10000]\n"


def _proc(rc=0, out="", err=""):
    return subprocess.CompletedProcess(["x"], rc, out, err)


class Fake:
    """Answers wrangler calls by subcommand and records them."""

    def __init__(self, whoami=None, d1=None, r2=None):
        self.answers = {"whoami": whoami, "d1": d1, "r2": r2}
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        for key in ("whoami", "d1", "r2"):
            if key in argv:
                a = self.answers[key]
                if isinstance(a, Exception):
                    raise a
                return a if a is not None else _proc(0, ACCOUNT)
        raise AssertionError(argv)


def _run(fake, tmp_path):
    return cf.check_remote_access({"CLOUDFLARE_API_TOKEN": TOKEN}, tmp_path, run=fake)


def test_all_three_probes_pass(tmp_path):
    r = _run(Fake(), tmp_path)
    assert r.ok and [c.name for c in r.checks] == ["account", "database", "storage"]


def test_the_incident_state_recognised_token_but_no_permission_is_named_precisely(tmp_path):
    r = _run(Fake(d1=_proc(1, "", AUTH_ERR), r2=_proc(1, "", AUTH_ERR)), tmp_path)
    assert not r.ok
    failed = {c.name for c in r.checks if not c.ok}
    assert failed == {"database", "storage"}  # the account probe passed: the token is real
    text = r.explain()
    assert "permission" in text.lower() and "D1" in text and "R2" in text
    assert "asifhussain60@gmail.com" in text


def test_a_token_for_the_wrong_account_is_caught(tmp_path):
    r = _run(Fake(whoami=_proc(0, "account: deadbeef")), tmp_path)
    assert not r.ok and not r.checks[0].ok
    assert "asifhussain60@gmail.com" in r.explain()


def test_a_token_with_a_trailing_newline_is_diagnosed(tmp_path):
    err = "Invalid format for Authorization header [code: 6111]"
    r = _run(Fake(whoami=_proc(1, "", err)), tmp_path)
    assert "whitespace" in r.explain().lower() or "newline" in r.explain().lower()


def test_a_hung_call_is_reported_as_a_timeout_not_a_crash(tmp_path):
    from _wrangler import WranglerTimeout

    r = _run(Fake(d1=WranglerTimeout("wrangler d1 timed out after 60s")), tmp_path)
    assert not r.ok
    assert "did not answer" in r.explain().lower()


def test_the_token_never_appears_in_anything_printed(tmp_path):
    leaky = f"request failed with token {TOKEN} in header"
    r = _run(Fake(whoami=_proc(1, leaky, leaky)), tmp_path)
    assert TOKEN not in r.explain()
    assert all(TOKEN not in c.detail for c in r.checks)


def test_a_failing_first_probe_still_runs_the_others_so_one_report_shows_everything(tmp_path):
    fake = Fake(whoami=_proc(1, "", AUTH_ERR))
    _run(fake, tmp_path)
    assert len(fake.calls) == 3


def test_the_database_probe_is_a_read_only_select(tmp_path):
    fake = Fake()
    _run(fake, tmp_path)
    d1 = next(c for c in fake.calls if "d1" in c)
    cmd = d1[d1.index("--command") + 1].strip().lower()
    assert cmd.startswith("select") and "insert" not in cmd and "update" not in cmd


@pytest.mark.parametrize("bad", ["", "   "])
def test_explain_is_never_empty_when_something_failed(bad, tmp_path):
    r = _run(Fake(d1=_proc(1, bad, bad)), tmp_path)
    assert r.explain().strip()


def test_prepare_remote_returns_none_and_loads_the_env_when_everything_passes(tmp_path, monkeypatch):
    import os

    import _production_publish as pp

    monkeypatch.setattr(pp, "cloudflare_env", lambda: {"CLOUDFLARE_API_TOKEN": TOKEN, "X": "1"})
    monkeypatch.setattr(cf, "_wrangler_run", Fake())
    monkeypatch.setattr(cf, "check_remote_access", lambda env, d: cf.Result((cf.Check("account", True),)))
    monkeypatch.delenv("X", raising=False)
    assert cf.prepare_remote(tmp_path) is None
    assert os.environ["X"] == "1"  # the env callers rely on is now in place


def test_prepare_remote_returns_the_report_when_a_probe_fails(tmp_path, monkeypatch):
    import _production_publish as pp

    monkeypatch.setattr(pp, "cloudflare_env", lambda: {"CLOUDFLARE_API_TOKEN": TOKEN})
    monkeypatch.setattr(
        cf, "check_remote_access", lambda env, d: cf.Result((cf.Check("database", False, AUTH_ERR),), TOKEN)
    )
    problem = cf.prepare_remote(tmp_path)
    assert problem and "database" in problem and TOKEN not in problem


def test_prepare_remote_reports_a_missing_token_with_the_keychain_command(tmp_path, monkeypatch):
    import _production_publish as pp

    def none():
        raise RuntimeError("no Cloudflare token: ... security add-generic-password -U ...")

    monkeypatch.setattr(pp, "cloudflare_env", none)
    assert "security add-generic-password" in cf.prepare_remote(tmp_path)


def test_a_token_of_the_wrong_length_is_caught_locally_before_any_network_call(tmp_path):
    """isaf-al-talib, 2026-09-19: the keychain item held 13 characters. A Cloudflare API token is 40,
    so every call failed with a confusing code. The shape is checkable with no network at all."""
    fake = Fake()
    r = cf.check_remote_access({"CLOUDFLARE_API_TOKEN": "tooshort1234x"}, tmp_path, run=fake)
    assert not r.ok
    assert fake.calls == [], "a token that cannot be valid must not be sent to Cloudflare"
    text = r.explain()
    assert "13 characters" in text and "40" in text
    assert "tooshort1234x" not in text, "the value itself is never printed"
    assert "security add-generic-password" in text


@pytest.mark.parametrize("bad", ['"' + "a" * 38 + '"', "Bearer " + "a" * 33, "a" * 39 + "!"])
def test_quotes_a_bearer_prefix_or_odd_characters_fail_the_shape_check(bad, tmp_path):
    fake = Fake()
    r = cf.check_remote_access({"CLOUDFLARE_API_TOKEN": bad}, tmp_path, run=fake)
    assert not r.ok and fake.calls == []


def test_a_well_formed_token_goes_on_to_the_network_probes(tmp_path):
    fake = Fake()
    assert _run(fake, tmp_path).ok and len(fake.calls) == 3


def test_terminal_colour_codes_are_stripped_from_reported_errors(tmp_path):
    coloured = "\x1b[31m✘ \x1b[41;31m[ERROR]\x1b[0m Authentication error [code: 10000]"
    r = _run(Fake(d1=_proc(1, "", coloured)), tmp_path)
    assert "\x1b" not in r.explain() and "[31m" not in r.explain()
