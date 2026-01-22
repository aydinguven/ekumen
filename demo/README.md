# Ekumen - Demo Build

This is a standalone demo version of **Ekumen**. It acts exactly like the real application but does **not** execute any actual system commands.

## Features
- **Simulated Backend:** Uses `mock_runner.py` to generate realistic Ansible output.
- **Safe:** No risk of damaging systems; runs completely locally.
- **Identical UI:** Same interface as the production version.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   python app.py
   ```

3. Open `http://localhost:5000`

## Note
All passwords and hosts are ignored. You can type anything.
