# Offline Installation

Install Ekumen on a server without internet access using bundled wheels.

## Steps

1. Download the latest release from another machine:
   - [ekumen-v1.7.2.tar.gz](https://github.com/aydinguven/ekumen/releases/latest/download/ekumen-v1.7.2.tar.gz)

2. Transfer the file to your server.

3. Extract and run the installer:
   ```bash
   tar -xzf ekumen-v1.7.2.tar.gz
   cd ekumen-v1.7.2
   sudo ./scripts/install-offline.sh
   ```

## Compatibility

- **OS:** Linux (x86_64, ARM64)
- **Python:** 3.8 – 3.14 (Wheels included in `wheels/` directory)

## What's Included

The release archive contains pre-downloaded Python wheels for:
- Flask and dependencies
- Gunicorn
- pexpect

This allows installation without any network access.
