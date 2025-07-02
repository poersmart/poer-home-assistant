# poer-home-assistant

Home Assistant custom integration for POER devices.

## Important note for upgraders

If, after upgrading, your devices suddenly don't work, please delete them via the UI and re-add them again.  There are a number of new features which require
new metadata to be discovered at the setup phase.  This may not be present on existing devices.
If this doesn't work you can roll back to a previous release via HACS, and please log an issue with the details of your problem.

## Supported devices

This integration supports various models of POER devices, which may also be known as:

- PTC10
- PTC20/26
- PTV30

## Installation

### Requirements

You need to have the POER App configured and working in Home Assistant in order to use this integration.

### Manual installation

cd config
git clone https://github.com/poersmart/poer-home-assistant.git
cd poer-home-assistant
./install.sh /config

### HACS

This integration is now available from within HACS.

Search for "poer" and click install.  You will also get notified of future upgrades.

### Config

After setting up, you can config two parameters Settings -> Integrations -> LEDnetWF -> Config.

- Disconnect delay or timeout: Timeout for bluetooth disconnect (0 for never)



Thanks!