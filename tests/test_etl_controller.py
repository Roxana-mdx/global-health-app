"""Action controller tests: a fake ETL service, so nothing is downloaded or loaded."""
import pytest

from app.dependencies import get_etl_service
from app.main import app
from etl.step_result import StepResult
from tests.fakes import FakeEtlService


def _use(results):
    service = FakeEtlService(results)
    app.dependency_overrides[get_etl_service] = lambda: service
    return service


@pytest.mark.parametrize(
    "path, expected_call",
    [("/actions/extract", "extract"), ("/actions/load", "transform_and_load")],
)
def test_each_action_calls_one_service_method(client, path, expected_call) -> None:
    service = _use([StepResult.ok("World Bank", "NY.GDP.PCAP.CD", "raw=1  clean=1  loaded=1")])

    response = client.post(path)

    assert response.status_code == 200
    assert service.calls == [expected_call]
    assert "NY.GDP.PCAP.CD" in response.text
    assert "step(s) failed" not in response.text


def test_failed_steps_are_reported_and_escaped(client) -> None:
    _use([StepResult.from_error("World Bank", "NY.GDP.PCAP.CD", ValueError("<script>alert(1)</script>"))])

    response = client.post("/actions/load")

    assert "1 step(s) failed" in response.text
    assert "&lt;script&gt;" in response.text
    assert "<script>" not in response.text


@pytest.mark.parametrize("path", ["/actions/extract", "/actions/load"])
def test_actions_do_not_answer_to_get(client, path) -> None:
    assert client.get(path).status_code == 405
