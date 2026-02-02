# Ekumen (Demo Version)

This is a **standalone demo version** of Ekumen, configured with a simulated backend. It does not require Ansible installed and does not execute any real commands.

> **[Live Demo](https://ekumen.aydin.cloud)**

## Purpose

The purpose of this demo is to allow users to explore the Ekumen interface and functionality without setting up an Ansible environment.

## Features (Simulated)

- **Mock Execution**: All Ansible commands are simulated with realistic delays and output.
- **Fail Scenarios**: Type "error" or "fail" in the inventory to simulate a connection failure.
- **Pre-loaded Playbooks**: Includes sample playbooks to demonstrate the library feature.
- **Safe**: Since no commands are actually executed, it is safe to run anywhere.

## Running the Demo

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. Access at `http://localhost:5005`

## Configuration

The demo runs on port **5005** by default to avoid conflicts with the main application. You can change this in `config.py`.

## About Ekumen

For the full version, see the main repository or the parent directory.
