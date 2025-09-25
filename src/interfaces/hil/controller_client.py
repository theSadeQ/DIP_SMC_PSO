#==========================================================================================\\\
#==================== src/interfaces/hil/controller_client.py ======================\\\
#==========================================================================================\\\
from __future__ import annotations

import argparse
import socket
import struct
import zlib
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

# Prefer the project’s validated loader; fall back to YAML only if unavailable.
try:
    from src.config import load_config as _validated_load_config  # type: ignore
    _HAS_VALIDATED = True
except Exception:  # pragma: no cover
    _HAS_VALIDATED = False
    try:
        import yaml  # type: ignore
    except Exception:  # pragma: no cover
        yaml = None  # type: ignore


def _load_config(cfg_path: Path) -> dict:
    """Prefer validated loading; fallback to YAML only if project loader unavailable."""
    if _HAS_VALIDATED:
        cfg_obj = _validated_load_config(cfg_path)
        return cfg_obj.model_dump()
    if yaml is None:
        raise RuntimeError("Neither validated loader nor PyYAML is available.")
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


# --- Minimal fallback PD controller (matches project interface) ---
class _FallbackPDController:
    def __init__(self):
        self.k_q1 = 50.0
        self.k_q2 = 25.0
        self.k_xd = 5.0
        self.k_q1d = 2.0
        self.k_q2d = 1.0

    def initialize_state(self):
        return ()

    def initialize_history(self):
        return {}

    def compute_control(self, state, state_vars, history):
        # state = [x, q1, q2, xdot, q1dot, q2dot]
        x, q1, q2, xdot, q1dot, q2dot = state
        u = (
            -self.k_q1 * q1
            - self.k_q2 * q2
            - self.k_xd * xdot
            - self.k_q1d * q1dot
            - self.k_q2d * q2dot
        )
        return float(u), state_vars, history


def _build_controller(cfg: dict):
    """Instantiate the configured controller or raise an error.

    In earlier versions this function silently fell back to a built‑in
    PD controller when the factory failed.  Such silent fallbacks can
    obscure configuration errors (e.g., mis‑spelling a controller name)
    and lead to unexpected behaviour.  We now raise a ``RuntimeError``
    when the controller cannot be created.  Failing fast on
    misconfiguration prevents experiments from silently using an
    unintended controller.
    """
    from src.controllers.factory import create_controller  # type: ignore
    ctrl_name = _get(cfg, "simulation.controller", "classical_smc")
    try:
        return create_controller(ctrl_name)
    except Exception as e:
        raise RuntimeError(f"Failed to instantiate controller '{ctrl_name}': {e}") from e


class HILControllerClient:
    # Packet formats mirror those used by PlantServer: each command and
    # state includes a 32‑bit sequence number, the payload (a single
    # double for commands or six doubles for state), and a CRC‑32
    # checksum.  Including sequence numbers allows detection of stale or
    # duplicate packets, while the CRC verifies integrity over UDP
    # transport【401883805680716†L137-L149】.
    CMD_FMT = "!I d I"  # [CIT-066]
    STATE_FMT = "!I 6d I"  # [CIT-066]
    CMD_SIZE = struct.calcsize(CMD_FMT)
    STATE_SIZE = struct.calcsize(STATE_FMT)

    def __init__(
        self,
        cfg: dict,
        plant_addr: Tuple[str, int],
        bind_addr: Tuple[str, int],
        dt: float,
        steps: int,
        results_path: Path,
        loop_sleep: bool = True,
        recv_timeout_s: float = 2.0,
    ) -> None:
        self.cfg = cfg
        self.plant_addr = plant_addr
        self.bind_addr = bind_addr
        self.dt = float(dt)
        self.steps = int(steps)
        self.results_path = results_path
        self.loop_sleep = bool(loop_sleep)
        self.recv_timeout_s = float(recv_timeout_s)

        self.controller = _build_controller(cfg)
        # Estimator: for now, identity (just use latest measurement)
        init_state = _get(cfg, "simulation.initial_state", [0,0,0,0,0,0])
        self.xhat = np.asarray(init_state, dtype=float).reshape(6)

        self.sock: Optional[socket.socket] = None

        # Logs
        self.t_hist = np.zeros(self.steps + 1, dtype=float)
        self.x_hist = np.zeros((self.steps + 1, 6), dtype=float)
        self.u_hist = np.zeros(self.steps, dtype=float)
        self.x_hist[0] = self.xhat

        # Sequence counters for UDP integrity.  The client increments
        # ``tx_seq`` before sending each command and tracks the highest
        # sequence received in ``rx_seq``.  Using explicit counters
        # supports acknowledgement semantics and detection of stale
        # packets, addressing the network integrity issue raised in
        # the design review.
        self.tx_seq: int = 0
        self.rx_seq: int = 0

    def run(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind to a fixed port so the server can reply to it
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.bind_addr)
        self.sock.settimeout(self.recv_timeout_s)

        # Control loop
        t0 = time.perf_counter()
        for k in range(self.steps):
            self.t_hist[k] = k * self.dt

            # Controller computes command from current estimate
            try:
                u, _, _ = self.controller.compute_control(self.xhat, None, {})
            except TypeError:
                u = float(self.controller.compute_control(self.xhat))
            u = float(u)
            self.u_hist[k] = u

            # Compose and send the command packet with sequence and CRC.  Increment
            # the transmit sequence number prior to sending to avoid zero as a
            # valid sequence.  Compute CRC over the sequence and command value
            # and append it to the packet.  This protects against bit flips in
            # transit and allows the plant server to verify integrity.
            self.tx_seq += 1  # [CIT-066]
            cmd_payload = struct.pack("!I d", self.tx_seq, u)  # [CIT-066]
            crc = zlib.crc32(cmd_payload) & 0xFFFFFFFF  # [CIT-066]
            pkt = cmd_payload + struct.pack("!I", crc)  # [CIT-066]
            self.sock.sendto(pkt, self.plant_addr)

            # Receive measurement.  On timeout retain the previous state
            # estimate.  Otherwise, parse sequence number, six doubles and
            # CRC, and verify integrity before accepting the measurement.  If
            # the sequence is stale (less than ``rx_seq``) or the CRC
            # mismatch occurs, discard the packet.
            meas_data = None
            try:
                meas_data, _ = self.sock.recvfrom(self.STATE_SIZE)
            except socket.timeout:
                meas_data = None
            if meas_data and len(meas_data) >= self.STATE_SIZE:
                try:
                    seq, *vals = struct.unpack(self.STATE_FMT, meas_data[: self.STATE_SIZE])
                except Exception:
                    vals = []
                if vals:
                    # Last element in vals is CRC (as Python int); measurement are 6 doubles.
                    meas_vals = vals[:-1]
                    recv_crc = int(vals[-1])
                    # Recompute CRC over sequence and measurement.
                    payload = struct.pack("!I 6d", seq, *[float(v) for v in meas_vals])  # [CIT-066]
                    calc_crc = zlib.crc32(payload) & 0xFFFFFFFF  # [CIT-066]
                    if recv_crc == calc_crc and seq >= self.rx_seq:
                        self.rx_seq = seq
                        self.xhat = np.asarray(meas_vals, dtype=float).reshape(6)

            # Log current estimate
            self.x_hist[k + 1] = self.xhat

            # Maintain loop period (best-effort)
            if self.loop_sleep:
                elapsed = time.perf_counter() - t0
                next_tick = (k + 1) * self.dt
                sleep_s = max(0.0, next_tick - elapsed)
                if sleep_s > 0:
                    time.sleep(sleep_s)

        # Final timestamp
        self.t_hist[self.steps] = self.steps * self.dt

        # Persist results
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            self.results_path,
            t=self.t_hist,
            x=self.x_hist,
            u=self.u_hist,
            meta=dict(
                plant_ip=self.plant_addr[0],
                plant_port=self.plant_addr[1],
                controller_ip=self.bind_addr[0],
                controller_port=self.bind_addr[1],
                dt=self.dt,
                steps=self.steps,
            ),
        )

        try:
            if self.sock is not None:
                self.sock.close()
        except Exception:
            pass


def run_client(cfg_path: str = "config.yaml", steps: Optional[int] = None, results_path: Optional[str] = None) -> Path:
    cfg_path_p = Path(cfg_path)
    cfg = _load_config(cfg_path_p)

    dt = float(_get(cfg, "simulation.dt", 0.01))
    duration = float(_get(cfg, "simulation.duration", 5.0))
    if steps is None:
        steps = int(round(duration / dt))

    plant_ip = cfg.get("hil", {}).get("plant_ip", "127.0.0.1")
    plant_port = int(cfg.get("hil", {}).get("plant_port", 9000))
    controller_ip = cfg.get("hil", {}).get("controller_ip", "127.0.0.1")
    controller_port = int(cfg.get("hil", {}).get("controller_port", 9001))

    results_path_p = Path(results_path) if results_path else Path("out/hil_results.npz")
    client = HILControllerClient(
        cfg=cfg,
        plant_addr=(plant_ip, plant_port),
        bind_addr=(controller_ip, controller_port),
        dt=dt,
        steps=steps,
        results_path=results_path_p,
    )
    client.run()
    return results_path_p


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="HIL Controller Client (UDP)")
    p.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    p.add_argument("--steps", type=int, default=None, help="Override step count (otherwise uses duration/dt)")
    p.add_argument("--results", type=str, default=None, help="Output path for results .npz (default: out/hil_results.npz)")
    args = p.parse_args(argv)

    outp = run_client(cfg_path=args.config, steps=args.steps, results_path=args.results)
    print(str(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#===========================================================================================================================\\\    
