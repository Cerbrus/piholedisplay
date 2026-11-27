# Configuration

Settings live in `config.json` at the repository root. The file is read again before every refresh, so a change takes effect without a restart.

`config.json` is tracked and gets replaced by every update. Put your own values in `config.local.json` next to it: it is ignored by git and is laid over `config.json`, key by key. For example, to refresh every 10 minutes and turn the screen around:

```json
{
    "interval_minutes": 10,
    "draw_inverted": false
}
```

## Settings

| Setting | Default | Function |
|---|---|---|
| `interval_minutes` | `30` | Minutes between screen refreshes. A refresh flashes the panel for about 15 seconds and wears it a little, so shorter is not better. `0` draws one frame and exits. |
| `retry_seconds` | `60` | How often Pi-hole is asked again while it does not answer. The screen is redrawn once when the data is lost and once when it is back, not on every retry. |
| `draw_inverted` | `true` | `true` or `false` turns the picture upside down, depending on how the Pi is mounted. |
| `corner_padding` | `0` | Pixels the refresh time stays away from the right edge of the panel, for a panel that is worn in its bottom-right corner. `6` moves it one character to the left. The picture served over HTTP is never padded. |
| `log_level` | `"INFO"` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. The log goes to the journal: `journalctl -u pihole-display`. |
| `pihole.api_url` | `"http://localhost/api"` | Address of the Pi-hole v6 API. |
| `pihole.password_file` | `"/etc/pihole/cli_pw"` | File holding the password for the API. The default is the CLI password Pi-hole writes itself; the user running the display has to be in the `pihole` group to read it. `null` for a Pi-hole without a password. |
| `http.port` | `8081` | Port on which the screen is served as a picture, at `/screen.png`. `0` serves nothing. |
| `http.max_age_seconds` | `120` | How long a served picture is reused before the next request draws a new one with fresh numbers. A request for `/screen.png?refresh=1` always draws a new one. |
| `phrases` | about 85 words | Words for the blocked count ("12.431 Yeeted"). One is picked at random on every refresh, from the ones that fit next to the current count. |

## Phrases

A phrase shares one line of 93 pixels with the blocked count, so how long it may be depends on that count: with a count below 100.000 there is room for 11 characters, below a million for 10, above that for 8. Longer phrases are left out of the draw for as long as they do not fit; when none fits, the screen says "Blocked".
