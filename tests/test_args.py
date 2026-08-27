"""The command line's vocabulary: the types and the version lookup."""

import argparse

import pytest

from carbonara import args


@pytest.mark.parametrize("value,expected", [("0", 0.0), ("0.3", 0.3), ("2", 2.0)])
def test_temperature_accepts_the_range(value, expected):
    """0.0 through 2.0 inclusive is what a sampling temperature may be."""
    assert args.temperature(value) == expected


@pytest.mark.parametrize("value", ["-0.1", "2.1", "hot", ""])
def test_temperature_rejects_the_rest(value):
    """Anything outside the range, or not a number, is argparse's error."""
    with pytest.raises(argparse.ArgumentTypeError):
        args.temperature(value)


def test_delay_rejects_a_negative():
    """A per-token delay cannot run backwards."""
    with pytest.raises(argparse.ArgumentTypeError):
        args.delay("-1")


def test_version_lookup_survives_a_missing_distribution(monkeypatch):
    """The parser is built on every invocation past a bare word.

    An unguarded PackageNotFoundError would take down every command rather
    than just this flag.
    """

    def raise_missing(name):
        raise args.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(args.metadata, "version", raise_missing)
    assert args.installed_version() == "unknown (not installed)"
