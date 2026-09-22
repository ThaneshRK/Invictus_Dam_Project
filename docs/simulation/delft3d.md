# Delft3D Adapter

The Phase 5 Delft3D adapter bridges the gap between the generalized Scenario Engine and standard Delft3D FM/FLOW installations.

## Requirements
- `DELFT3D_HOME` environment variable must point to the installation directory.
- `d3d_run.sh` must be executable.

## Security
To prevent shell injection from dynamically generated project names, `subprocess.Popen` is strictly executed with array argument lists:
```python
subprocess.Popen([self.executable, self.mdf_path], ...)
```

## Fixtures
If the adapter detects Delft3D is not installed (e.g. in test CI environments), `validate()` will gracefully proceed, allowing `prepare()` to generate `.mdf` configs to disk, and `run()` to instantly complete, outputting a test fixture payload labeled `TEST FIXTURE`.
