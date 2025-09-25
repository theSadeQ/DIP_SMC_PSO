# Hardware-in-the-Loop (HIL)

This section maps to `src/interfaces/hil/` and documents HIL components and workflows.

- Key modules:
  - {py:mod}`src.interfaces.hil.plant_server`
  - {py:mod}`src.interfaces.hil.controller_client`
  - {py:mod}`src.interfaces.hil.real_time_sync`
  - {py:mod}`src.interfaces.hil.data_logging`
  - {py:mod}`src.interfaces.hil.fault_injection`
  - {py:mod}`src.interfaces.hil.simulation_bridge`

## Run HIL (examples)

```bash
python simulate.py --run-hil --plot
python simulate.py --config custom_config.yaml --run-hil
```

