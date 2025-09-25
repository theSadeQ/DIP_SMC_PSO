#==========================================================================================\\\
#======================== src/interfaces/hil/plant_server.py ===========================\\\
#==========================================================================================\\\
from __future__ import annotations

import argparse
import socket
import struct
import zlib
import threading
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

try:
    import yaml
except Exception:
    yaml = None

def _load_config(cfg_path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML must be available to read config.yaml")
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f) or {}

def _get(cfg: dict, dotted: str, default=None):
    cur = cfg
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur

def _build_dynamics(cfg: dict):
    """
    Build the dynamics model using the project's light/full models if present.
    """
    use_full = bool(_get(cfg, "simulation.use_full_dynamics", False))
    try:
        if use_full:
            from src.models.double_inverted_pendulum_full import DoubleInvertedPendulumFull as Model
        else:
            from src.models.double_inverted_pendulum_light import DoubleInvertedPendulumLight as Model
    except Exception:
        class Model:
            def __init__(self, dt: float):
                self.dt = dt
            def step(self, x, u):
                x = x.copy()
                x[0] += self.dt
                x[1] += self.dt * x[3]
                x[2] += self.dt * x[4]
                x[3] += self.dt * (u if np.isscalar(u) else u[0] - 0.1 * x[3])
                x[4] += self.dt * ((0.0 if np.isscalar(u) else u[1]) - 0.1 * x[4])
                x[5] += 0.0
                return x
        return Model
    return Model

class PlantServer:
    # Network packet formats incorporating sequence numbers and CRC‑32.
    # Each command from the controller includes an unsigned 32‑bit sequence
    # number, a 64‑bit float command value and a CRC computed over the
    # sequence and command.  Similarly, each state packet sent back to
    # the controller contains a sequence number, six 64‑bit floats and a
    # CRC.  Including a sequence number enables detection of out‑of‑order
    # or duplicate packets, while the CRC provides integrity checking
    # against bit errors【401883805680716†L137-L149】.  See design review issue #44.
    CMD_FMT = "!I d I"  # [CIT-066]
    CMD_SIZE = struct.calcsize(CMD_FMT)
    STATE_FMT = "!I 6d I"  # [CIT-066]
    STATE_SIZE = struct.calcsize(STATE_FMT)

    def __init__(
        self,
        cfg: dict,
        bind_addr: Tuple[str, int],
        dt: float = 0.01,
        extra_latency_ms: float = 0.0,
        sensor_noise_std: float = 0.0,
        max_steps: Optional[int] = None,
        server_ready_event: Optional[threading.Event] = None,
        *,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.cfg = cfg
        self.bind_addr = bind_addr
        self.dt = float(dt)
        self.extra_latency = float(extra_latency_ms) / 1000.0
        # Standard deviation of additive sensor noise.  A zero value
        # disables noise injection.  When non‑zero the noise is
        # generated using the instance's random number generator
        # ``self.rng`` rather than the global NumPy RNG.  This design
        # follows best practices in stochastic simulation by avoiding
        # global state and enabling reproducible noise sequences when a
        # seed is provided【474685546011607†L282-L292】.
        self.sensor_noise_std = float(sensor_noise_std)
        self.max_steps = max_steps
        self._ready_evt = server_ready_event

        self._sock: Optional[socket.socket] = None
        self._stop_evt = threading.Event()

        init = _get(cfg, "simulation.initial_state", [0, 0, 0, 0, 0, 0])
        self.state = np.array(init, dtype=float)

        Model = _build_dynamics(cfg)
        self.model = Model(self.dt)

        # Random number generator for sensor noise.  If a generator is
        # provided by the caller use it directly; otherwise, create
        # a new generator seeded from the configuration if available.
        if rng is not None:
            self.rng = rng
        else:
            # Attempt to read a seed from the configuration.  Use
            # ``global_seed`` if present or fall back to None for
            # non‑deterministic noise.  Storing the seed at the
            # application level centralises randomness control across
            # subsystems and avoids hidden correlations【474685546011607†L282-L292】.
            seed = _get(cfg, "global_seed", None)
            if seed is not None:
                try:
                    self.rng = np.random.default_rng(int(seed))
                except Exception:
                    self.rng = np.random.default_rng()
            else:
                self.rng = np.random.default_rng()

        # Sequence numbers for command reception and state transmission.  The
        # plant server increments ``rx_seq`` when processing commands and
        # echoes back the last received sequence in the measurement.  This
        # facilitates detection of stale or dropped packets and allows
        # simple acknowledgement semantics.  See design review issue #44.
        self.rx_seq: int = 0
        self.tx_seq: int = 0

    def start(self) -> None:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(self.bind_addr)
            self._sock.settimeout(1.0)
            # Signal readiness AFTER successful bind
            if self._ready_evt is not None:
                self._ready_evt.set()
        except Exception:
            # Unblock waiter and exit if bind fails
            if self._ready_evt is not None:
                self._ready_evt.set()
            logging.exception("PlantServer failed to bind/start")
            return

        steps = 0
        try:
            while not self._stop_evt.is_set():
                try:
                    data, client_addr = self._sock.recvfrom(self.CMD_SIZE)
                except socket.timeout:
                    continue
                if not data or len(data) < self.CMD_SIZE:
                    continue
                # Decode the command packet: sequence, command, CRC.
                try:
                    seq, cmd_val, recv_crc = struct.unpack(self.CMD_FMT, data[: self.CMD_SIZE])
                except Exception:
                    continue
                # Compute CRC over the sequence and command value (excluding the CRC field).
                crc_payload = struct.pack("!I d", seq, cmd_val)  # [CIT-066]
                calc_crc = zlib.crc32(crc_payload) & 0xFFFFFFFF  # [CIT-066]
                # Ignore packets with mismatched CRC or stale sequence numbers.
                if recv_crc != calc_crc or seq < self.rx_seq:
                    continue
                # Update the last received sequence.
                self.rx_seq = seq
                u = float(cmd_val)
                # Step the dynamics.  Accept both scalar and vector commands.
                try:
                    self.state = self.model.step(self.state, u)
                except Exception:
                    try:
                        self.state = self.model.step(self.state, np.array([u, 0.0], dtype=float))
                    except Exception:
                        pass
                # Copy state and inject noise.
                meas = self.state.copy()
                if self.sensor_noise_std > 0.0:
                    meas += self.rng.normal(0.0, self.sensor_noise_std, size=meas.shape)
                # Optional latency.
                if self.extra_latency > 0.0:
                    time.sleep(self.extra_latency)
                # Compose the state packet with sequence number and CRC.  Echo the
                # last received sequence back to the controller as acknowledgement.
                self.tx_seq = self.rx_seq
                # Pack sequence and measurement values (6 floats).
                payload = struct.pack("!I 6d", self.tx_seq, *[float(v) for v in meas[:6]])  # [CIT-066]
                state_crc = zlib.crc32(payload) & 0xFFFFFFFF  # [CIT-066]
                pkt = payload + struct.pack("!I", state_crc)  # [CIT-066]
                try:
                    self._sock.sendto(pkt, client_addr)
                except Exception:
                    pass
                steps += 1
                if self.max_steps is not None and steps >= self.max_steps:
                    break
        finally:
            try:
                self.close()
            except Exception:
                pass

    def close(self) -> None:
        sock = getattr(self, "_sock", None)
        if sock is not None:
            try:
                sock.close()
            finally:
                self._sock = None

    def stop(self) -> None:
        self._stop_evt.set()
        try:
            tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tmp.sendto(b"STOP", self.bind_addr)
            tmp.close()
        except Exception:
            pass


def start_server(cfg_path: str | Path, max_steps: Optional[int] = None) -> PlantServer:
    cfgp = Path(cfg_path)
    cfg = _load_config(cfgp)
    plant_ip = str(_get(cfg, "hil.plant_ip", "127.0.0.1"))
    plant_port = int(_get(cfg, "hil.plant_port", 9000))
    dt = float(_get(cfg, "simulation.dt", 0.01))
    extra_latency_ms = float(_get(cfg, "hil.extra_latency_ms", 0.0))
    sensor_noise_std = float(_get(cfg, "hil.sensor_noise_std", 0.0))

    server = PlantServer(
        cfg=cfg,
        bind_addr=(plant_ip, plant_port),
        dt=dt,
        extra_latency_ms=extra_latency_ms,
        sensor_noise_std=sensor_noise_std,
        max_steps=max_steps,
    )
    server.start()
    return server


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="HIL Plant Server (UDP)")
    p.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    p.add_argument("--max-steps", type=int, default=None, help="Optional: exit after N steps")
    args = p.parse_args(argv)

    _ = start_server(args.config, args.max_steps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#==============================================================================================\\\
