"""ETL service tests: stub jobs, so nothing is downloaded and no database is used."""
import pytest

from app.services.etl_service import (
    EtlService,
    ExtractJob,
    ImportJob,
    default_extract_jobs,
)
from etl.extract_worldbank import WorldBankApiError
from etl.step_result import StepResult, StepStatus


def _file_job(tmp_path, item: str) -> ExtractJob:
    path = tmp_path / f"{item}.json"
    path.write_text("{}")
    return ExtractJob("Source", item, lambda: (path, "https://example.org"))


def _failing_job(error: Exception) -> ExtractJob:
    def download():
        raise error

    return ExtractJob("Source", "broken", download)


def test_extract_all_gives_one_result_per_file(tmp_path) -> None:
    service = EtlService(
        extract_jobs=[_file_job(tmp_path, "a"), _file_job(tmp_path, "b")], import_jobs=[]
    )

    results = service.extract_all()

    assert [(r.item, r.status) for r in results] == [
        ("a", StepStatus.OK),
        ("b", StepStatus.OK),
    ]
    assert "a.json" in results[0].detail


def test_expected_download_errors_become_failed_results(tmp_path) -> None:
    service = EtlService(
        extract_jobs=[_failing_job(WorldBankApiError("bad response")), _file_job(tmp_path, "ok")],
        import_jobs=[],
    )

    results = service.extract_all()

    assert results[0].status is StepStatus.FAILED
    assert "WorldBankApiError" in results[0].detail
    assert results[1].status is StepStatus.OK  # the other downloads still run


def test_unexpected_errors_are_not_hidden() -> None:
    service = EtlService(extract_jobs=[_failing_job(RuntimeError("a bug"))], import_jobs=[])

    with pytest.raises(RuntimeError):
        service.extract_all()


def test_transform_and_load_runs_the_jobs_in_order() -> None:
    calls: list[str] = []

    def job(name: str) -> ImportJob:
        def run() -> list[StepResult]:
            calls.append(name)
            return [StepResult.ok(name, "one"), StepResult.ok(name, "two")]

        return ImportJob(name, run)

    service = EtlService(extract_jobs=[], import_jobs=[job("first"), job("second")])

    results = service.transform_and_load_all()

    assert calls == ["first", "second"]
    assert [(r.source, r.item) for r in results] == [
        ("first", "one"),
        ("first", "two"),
        ("second", "one"),
        ("second", "two"),
    ]


def test_default_extract_jobs_cover_every_source() -> None:
    items = [job.item for job in default_extract_jobs()]

    assert items == [
        "countries",
        "NY.GDP.PCAP.CD",
        "SH.XPD.CHEX.GD.ZS",
        "SH.XPD.CHEX.PC.CD",
        "SP.DYN.TFRT.IN",
        "IHME CSV",
    ]
