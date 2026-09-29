# GabCon Rig Control

`mcbuild-dashboard` is a local web dashboard for the Windows/WSL workstation used to run GabCon BuildAI on two RTX 3060 Ti GPUs.

## Start

From the repository inside Ubuntu/WSL:

```bash
uv sync --extra dev
uv run mcbuild-dashboard
```

Open `http://localhost:8787` from Windows. WSL normally forwards loopback ports to the Windows host.

The default bind address is `127.0.0.1`. Keep it that way: this first version has no authentication and is intended for the local/trusted workstation only.

## What it shows

- CPU thread count, load average, WSL uptime and Linux memory usage.
- Linux `/` plus Windows `C:` and `D:` free space when mounted under `/mnt/c` and `/mnt/d`.
- One card per NVIDIA GPU with utilization, VRAM, temperature, power, graphics clock and PCIe link information.
- NVIDIA compute processes when exposed by `nvidia-smi`.
- The recommended first-stage workload split: GPU 0 for the first QLoRA/Qwen smoke tests, GPU 1 for workers/rendering until the PCIe topology has been measured.

## Diagnostics

The browser does **not** expose an arbitrary shell. It can only run a fixed allow-list:

- `nvidia-smi`
- `nvidia-smi topo -m`
- PCIe generation/width query
- PyTorch/CUDA/BF16 probe
- bitsandbytes import probe
- `swift --version`

The PyTorch and bitsandbytes probes use `MCBUILD_TRAIN_PYTHON` when set. Otherwise the dashboard looks for `.venv-train/bin/python` in the repository and finally falls back to the Python interpreter running the dashboard.

Example when the training environment lives in a custom location:

```bash
export MCBUILD_TRAIN_PYTHON="$HOME/src/GabCon-BuildAI/.venv-train/bin/python"
uv run mcbuild-dashboard
```

## Managed service

The dashboard can start and stop one `mcbuild-server` process. Model, reasoning level, maximum iterations and an optional `CUDA_VISIBLE_DEVICES` affinity are validated before the process is launched. Logs are written to:

```text
.mcbuild/dashboard/logs/mcbuild-server.log
```

No GPU power-limit, overclock, driver installation, package installation, shutdown/reboot or arbitrary command endpoint is included.

## Qwen smoke test

The UI displays the prepared first-stage `Qwen/Qwen3.5-4B` 4-bit `swift infer` command with `CUDA_VISIBLE_DEVICES=0`. It is copy-only because `swift infer` is interactive and starting an inference/training workload should remain deliberate.

## Options

```bash
uv run mcbuild-dashboard --host 127.0.0.1 --port 8787
```

Binding to a non-loopback address prints a warning. Add authentication/reverse-proxy controls before exposing the dashboard to another machine or network.
