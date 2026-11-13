import pytest
from fastapi.testclient import TestClient

from eng_workbench.api import create_app
from eng_workbench.identity import BEX, IDA, NELL, OTTO
from eng_workbench.store import build_lab_store


@pytest.fixture()
def store():
    return build_lab_store()


@pytest.fixture()
def client(store):
    return TestClient(create_app(store))


@pytest.fixture()
def ida():
    return IDA


@pytest.fixture()
def otto():
    return OTTO


@pytest.fixture()
def nell():
    return NELL


@pytest.fixture()
def bex():
    return BEX
