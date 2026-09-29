from mcbuild.dashboard.server import parse_gpu_csv, parse_meminfo


def test_parse_gpu_csv_converts_numeric_values():
    fields = ("index", "name", "temperature.gpu", "memory.used")
    rows = parse_gpu_csv("0, NVIDIA GeForce RTX 3060 Ti, 55, 1234\n", fields)
    assert rows == [
        {
            "index": 0,
            "name": "NVIDIA GeForce RTX 3060 Ti",
            "temperature.gpu": 55,
            "memory.used": 1234,
        }
    ]


def test_parse_gpu_csv_preserves_na_as_none():
    fields = ("index", "power.draw")
    assert parse_gpu_csv("1, N/A\n", fields) == [{"index": 1, "power.draw": None}]


def test_parse_meminfo_converts_kib_to_bytes():
    info = parse_meminfo("MemTotal:       16384 kB\nMemAvailable:    4096 kB\n")
    assert info["MemTotal"] == 16384 * 1024
    assert info["MemAvailable"] == 4096 * 1024
