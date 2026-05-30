# Supermemory Multi-Profile Config Wrapper

Some setups use a `profiles` top-level key in `supermemory.json` instead of flat config:

```json
{
  "profiles": {
    "default": {
      "container_tag": "hermes",
      ...
    },
    "regent": {
      "container_tag": "hermes-cabinet",
      ...
    }
  }
}
```

When this is the case, a simple `cp` of the file from default to cron-worker won't auto-activate
the cron-worker profile — it needs its own entry under `profiles.`.

**Fix**: clone the `default` section into `profiles.cron-worker`:

```python
import json
with open('supermemory.json') as f:
    cfg = json.load(f)
cfg['profiles']['cron-worker'] = cfg['profiles']['default'].copy()
with open('supermemory.json', 'w') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
```
