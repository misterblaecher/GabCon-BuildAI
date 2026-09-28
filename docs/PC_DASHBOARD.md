# GabCon GPU Control

Local web dashboard for the GabCon workstation with the two RTX 3060 Ti cards.
It is intentionally dependency-free: the HTTP server and UI are part of the Python standard library.

## What it shows

- both NVIDIA GPUs: utilization, VRAM, temperature, power, SM clock, current PCIe generation and width;
- CUDA compute processes and their VRAM use;
- WSL/native environment, Python version, RAM and Linux filesystem usage;
- a ready-to-copy Qwen3.5 4-bit `swift infer` command for GPU 0 or GPU 1;
- logs for diagnostics launched from the dashboard.

## Safe actions

The UI can only start three whitelisted diagnostics:

- `nvidia-smi`;
- a PyTorch CUDA/BF16 probe;
- a bitsandbytes import/GPU probe.

A GPU can be selected for the Python probes; the child process then receives `CUDA_VISIBLE_DEVICES=<index>`.
The Stop button only terminates jobs created by the dashboard. There is no arbitrary web shell, no power-limit/clock/voltage
control, and no endpoint that can run user-supplied commands.

## Start it in the training environment

The dashboard itself needs no third-party package, but the PyTorch and bitsandbytes buttons use the Python interpreter that
started it. For the 3060 Ti training machine, start it from the training virtual environment described in the setup notes:

```bash
cd ~/src/GabCon-BuildAI
source .venv-train/bin/activate
PYTHONPATH=src python -m mcbuild.pc_dashboard
```

Open from Windows or WSL:

```text
http://127.0.0.1:8899
```

If the project is installed in that environment, the console script is also available:

```bash
mcbuild-pc-dashboard
```

Use another port when needed:

```bash
PYTHONPATH=src python -m mcbuild.pc_dashboard --port 8900
```

## Security model

The default bind address is `127.0.0.1`. Keep it that way for normal use. Mutating requests require a random token embedded
in the page for the lifetime of the process, and the backend exposes only whitelisted actions.

You can bind to another interface with `--host`, but the server has no user login. Do not expose it directly to the internet
or an untrusted LAN.

## Expected 3060 Ti flow

The dashboard matches the current bring-up order for this machine: first verify `nvidia-smi`, then PyTorch/CUDA, then
bitsandbytes, then Qwen. It does not install CUDA, drivers, FlashAttention or model packages for you. This keeps diagnostics
separate from installation failures.
