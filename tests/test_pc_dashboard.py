from __future__ import annotations

import subprocess

import pytest

from mcbuild import pc_dashboard as dashboard


def test_parse_gpu_csv() -> None:
    text = "0, GPU-a, NVIDIA GeForce RTX 3060 Ti, 42, 17, 1024, 8192, 51.5, 200, 1665, 4, 8"
    rows = dashboard._parse_csv_rows(text, dashboard.GPU_QUERY_KEYS)
    assert rows == [
        {
            "index": 0,
            "uuid": "GPU-a",
            "name": "NVIDIA GeForce RTX 3060 Ti",
            "temperature_c": 42,
            "utilization_pct": 17,
            "memory_used_mib": 1024,
            "memory_total_mib": 8192,
            "power_draw_w": 51.5,
            "power_limit_w": 200,
            "clock_sm_mhz": 1665,
            "pcie_gen": 4,
            "pcie_width": 8,
        }
    ]


def test_parse_not_supported_values() -> None:
    text = "1, GPU-b, NVIDIA GeForce RTX 3060 Ti, N/A, 0, 0, 8192, N/A, 200, 210, N/A, N/A"
    row = dashboard._parse_csv_rows(text, dashboard.GPU_QUERY_KEYS)[0]
    assert row["temperature_c"] is None
    assert row["power_draw_w"] is None
    assert row["pcie_gen"] is None
    assert row["pcie_width"] is None


def test_query_gpus_handles_missing_nvidia_smi(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("nvidia-smi")

    monkeypatch.setattr(dashboard, "_run", missing)
    gpus, error = dashboard.query_gpus()
    assert gpus == []
    assert error is not None
    assert "nvidia-smi" in error


@pytest.mark.parametrize(("value", "expected"), [(0, "0"), (1, "1"), ("1", "1"), ("all", "all")])
def test_gpu_normalization(value: object, expected: str) -> None:
    assert dashboard.JobManager._normalize_gpu(value) == expected


def test_gpu_normalization_rejects_shell_like_values() -> None:
    with pytest.raises(ValueError):
        dashboard.JobManager._normalize_gpu("0; rm -rf /")
