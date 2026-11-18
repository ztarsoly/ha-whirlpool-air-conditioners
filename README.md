# Whirlpool Air Conditioners

A Home Assistant custom integration for Whirlpool air conditioners, controlled
through the Whirlpool cloud. It works with accounts from the Whirlpool, Maytag,
KitchenAid and Consul apps, in the EU and US regions.

The cloud pushes changes to Home Assistant as they happen, so there's no polling.

## Supported devices

These air conditioners are confirmed to work with the original Home Assistant
Whirlpool integration this one is based on. Other models may work too.

- Whirlpool SPIW309A2WF
- Whirlpool SPIW312A2WF
- Whirlpool SPIW409A2WF

If yours works (or doesn't), please say so in an
[issue](https://github.com/ztarsoly/ha-whirlpool-air-conditioners/issues).

## Prerequisites

- An account for the Whirlpool app, or for the Maytag, KitchenAid or Consul app.
- Your air conditioners added to that account in the manufacturer's mobile app.
  The integration only sees appliances registered there.

## Features

Each air conditioner on your account becomes a device with these entities.

### Climate

| Feature | Details |
|---|---|
| Modes | Off, Cool, Heat, Fan only, Auto (Whirlpool's 6th Sense mode) |
| Target temperature | 16–30 °C, in 1° steps |
| Fan speed | Off, Auto, Low, Medium, High |
| Swing | Horizontal louver swing on or off |
| Target humidity | Only on units that report a humidity setting |
| Readings | Current temperature and current humidity |

The thermostat card shows the current room temperature next to the target.
Choosing a mode while the unit is off also turns it on.

### Switches

| Entity | What it does |
|---|---|
| Display | Turns the unit's display panel on or off |
| Jet | Turbo mode |
| Power save | Eco mode |
| Super silent | Quiet mode |

### Other entities

| Entity | What it does |
|---|---|
| Sleep mode (select) | Off, Adults, Elderly, Teens, Children. Only on units that report this setting |
| Restart Wi-Fi module (button) | Restarts the unit's Wi-Fi module. Only on units that report this setting |

### Also included

- Re-authentication: if your password changes or the login stops working, Home
  Assistant asks you to enter it again.
- Diagnostics download, with serial numbers, MAC addresses and credentials removed.
- English and Hungarian translations.

## Installation

### Manual

1. Copy the `custom_components/whirlpool_air_conditioners` folder into the
   `custom_components` folder of your Home Assistant configuration directory.
   Create that folder if it doesn't exist.
2. Restart Home Assistant.

### HACS

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/ztarsoly/ha-whirlpool-air-conditioners` with the
   type **Integration**.
3. Install **Whirlpool Air Conditioners** and restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Whirlpool Air Conditioners**.
3. Enter:
   - **Username** and **Password**: the ones you use in the manufacturer's app.
   - **Region**: the region your account is registered in (EU or US).
   - **Brand**: the brand of the mobile app you use. This can differ from the
     brand of your air conditioner.

Setup fails with "No supported appliances found" if the account has no air
conditioner.

## Removal

1. Go to **Settings → Devices & services → Whirlpool Air Conditioners**.
2. Open the menu on the account entry and choose **Delete**, then confirm.
   Home Assistant also deletes the entry's devices and entities. No other
   cleanup is needed.
3. To uninstall the code, remove the integration in HACS, or delete the
   `custom_components/whirlpool_air_conditioners` folder, then restart.

## Known limitations

- Requires an internet connection and the Whirlpool cloud; there's no local control.
- Auto is offered on every unit, because the library can't tell whether a model
  supports 6th Sense. On units without it, choosing Auto fails with "Request failed".
- The target humidity slider uses Home Assistant's default range, because the
  library doesn't report the unit's real limits.
- The library has no functions for sleep mode or the Wi-Fi restart, so the
  integration sends those settings directly. The Wi-Fi restart command value
  hasn't been confirmed on a real unit.
- Not supported by the library: vertical louver swing, fixed louver positions,
  timers, dry mode, filter alerts and energy use.

## Troubleshooting

To get debug logs, add this to `configuration.yaml` and restart:

```yaml
logger:
  default: warning
  logs:
    custom_components.whirlpool_air_conditioners: debug
    whirlpool: debug
```

Or turn on debug logging from the integration's page in
**Settings → Devices & services**.

When reporting a problem, attach the logs and the diagnostics download to an
[issue](https://github.com/ztarsoly/ha-whirlpool-air-conditioners/issues).

## Development

The tests are unit tests written with pytest, pytest-asyncio and pytest-cov.
They call the integration's entities, setup and config flow directly, with
Home Assistant and the Whirlpool cloud mocked, so they need no account or
appliance. Each run prints a coverage report.

You need the Python version your Home Assistant release requires (3.14 at the
time of writing). Run the commands from the repository root.

Linux and macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements_test.txt
.venv/bin/python -m pytest
.venv/bin/python -m pylint custom_components tests
```

Windows (PowerShell or Command Prompt):

```bash
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements_test.txt
.venv\Scripts\python -m pytest
.venv\Scripts\python -m pylint custom_components tests
```

Home Assistant itself doesn't run on Windows, but these tests only import
the parts the integration uses, so they work there too. If installing fails
with "file name too long", move the repository to a shorter path or turn on
Windows long path support.

The test dependencies in `requirements_test.txt` are pinned to exact versions,
so CI only changes when you update them. Coverage must stay at 99% or higher, or the
test run fails.

On every push to `main` and on pull requests, GitHub Actions runs:

- **Tests**: pylint and the tests. The tests still run when pylint fails.
- **Validate**: hassfest, Home Assistant's validator for `manifest.json`,
  translations and file layout.

## Credits

Based on the [Whirlpool Appliances integration](https://www.home-assistant.io/integrations/whirlpool/)
in Home Assistant core (see its documentation for washers, dryers, ovens and
refrigerators), by [@abmantis](https://github.com/abmantis) and
[@mkmer](https://github.com/mkmer). Uses the
[whirlpool-sixth-sense](https://pypi.org/project/whirlpool-sixth-sense/) library.

This project isn't affiliated with or endorsed by Whirlpool Corporation.
Whirlpool is a registered trademark of Whirlpool Corporation.

## License

Licensed under the [Apache License 2.0](LICENSE), the same license as
Home Assistant. Portions of the code come from the Home Assistant Whirlpool
integration, copyright the Home Assistant authors, also under the Apache
License 2.0. The files that came from it have been modified.
