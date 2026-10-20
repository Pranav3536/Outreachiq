"""Smoke test - verify core dependencies import cleanly."""
import pandas as pd
import streamlit as st


def test_pandas_imports():
    assert pd.__version__


def test_streamlit_imports():
    assert st.__version__
