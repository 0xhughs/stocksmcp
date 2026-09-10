# LOOP identity tools

Coordinator-only helpers for snapshot and contract identity required by `LOOP.md`.

Manifest JSON written under `manifests/` is excluded from snapshot coverage so identity files do not hash themselves.

```bash
python3 loop/identity.py snapshot loop/manifests/snapshot.json
python3 loop/identity.py contract loop/manifests/contract.json
```
