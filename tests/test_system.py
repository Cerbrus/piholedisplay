from piholedisplay import system

WIRELESS = """Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
 wlan0: 0000   54.  -56.  -256        0      0      0      0      0        0
"""


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def test_memory_percent_counts_what_is_not_available(tmp_path):
    write(tmp_path, 'proc/meminfo', 'MemTotal:         440340 kB\nMemFree:           31308 kB\nMemAvailable:     198684 kB\n')

    assert system.memory_percent(tmp_path) == 55


def test_temperature_is_whole_degrees(tmp_path):
    write(tmp_path, 'sys/class/thermal/thermal_zone0/temp', '40084\n')

    assert system.temperature(tmp_path) == 40


def test_uptime_is_whole_seconds(tmp_path):
    write(tmp_path, 'proc/uptime', '3470.72 2835.77\n')

    assert system.uptime_seconds(tmp_path) == 3470


def test_wifi_percent_scales_link_quality(tmp_path):
    write(tmp_path, 'proc/net/wireless', WIRELESS)

    assert system.wifi_percent(tmp_path) == 77


def test_wifi_percent_is_missing_without_an_interface(tmp_path):
    write(tmp_path, 'proc/net/wireless', '\n'.join(WIRELESS.splitlines()[:2]) + '\n')

    assert system.wifi_percent(tmp_path) is None


def test_under_voltage_reads_the_since_boot_bit(tmp_path):
    write(tmp_path, 'get_throttled', '50005\n')
    assert system.under_voltage(tmp_path / 'get_throttled', fallback=lambda: None)

    write(tmp_path, 'get_throttled', '0\n')
    assert not system.under_voltage(tmp_path / 'get_throttled', fallback=lambda: '0x50000')


def test_under_voltage_falls_back_to_vcgencmd(tmp_path):
    missing = tmp_path / 'get_throttled'

    assert system.under_voltage(missing, fallback=lambda: '0x50000')
    assert not system.under_voltage(missing, fallback=lambda: '0x0')
    assert not system.under_voltage(missing, fallback=lambda: None)


def test_missing_files_give_missing_values(tmp_path):
    stats = system.read_system(tmp_path / 'nowhere', throttled_fallback=lambda: None)

    assert stats.memory_percent is None
    assert stats.disk_percent is None
    assert stats.temperature is None
    assert stats.uptime_seconds is None
    assert stats.wifi_percent is None
    assert not stats.under_voltage
    assert stats.host.endswith('.local')
