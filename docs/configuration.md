# Configuration

Settings live in `config.json` at the repository root. The file is read again before every refresh, so a change takes effect without a restart.

`config.json` is tracked and gets replaced by every update. Put your own values in `config.local.json` next to it: it is ignored by git and is laid over `config.json`, key by key. For example, to refresh every 5 minutes and turn the screen around:

```json
{
    "interval_minutes": 5,
    "draw_inverted": false
}
```

## Settings

| Setting | Default | Function |
|---|---|---|
| `interval_minutes` | `10` | Minutes between screen refreshes. `0` draws one frame and exits. |
| `retry_seconds` | `60` | How often Pi-hole is asked again while it does not answer. The screen is redrawn once when the data is lost and once when it is back, not on every retry. |
| `draw_inverted` | `true` | `true` or `false` turns the picture upside down, depending on how the Pi is mounted. |
| `log_level` | `"INFO"` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. The log goes to the journal: `journalctl -u pihole-display`. |
| `pihole.api_url` | `"http://localhost/api"` | Address of the Pi-hole v6 API. |
| `pihole.password_file` | `"/etc/pihole/cli_pw"` | File holding the password for the API. The default is the CLI password Pi-hole writes itself; the user running the display has to be in the `pihole` group to read it. `null` for a Pi-hole without a password. |
| `phrases` | about 70 words | Words for the blocked count ("12.431 Yeeted"). One is picked at random on every refresh, from the ones that fit next to the current count. |

## Phrases

A phrase shares one line of 93 pixels with the blocked count, so how long it may be depends on that count: with a count below 100.000 there is room for 11 characters, below a million for 10, above that for 8. Longer phrases are left out of the draw for as long as they do not fit; when none fits, the screen says "Blocked".
