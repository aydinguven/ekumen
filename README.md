# Ekumen

A simple web interface for running Ansible playbooks and ad-hoc commands.

In Ursula K. Le Guin's Hainish Cycle, the *ansible* is a device that allows instantaneous communication across any distance — named from "answerable." The Ekumen is the interstellar collective that uses ansibles to coordinate between worlds separated by light-years, achieving unity through patience and understanding rather than force. Red Hat's Ansible automation tool borrowed the name, and this project borrows from both: connecting distant servers through a web interface, one playbook at a time.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8--3.14-green.svg)

> **[Live Demo](https://ekumen.aydin.cloud)** — Try it safely in your browser with simulated data.

## Screenshots

<table>
  <tr>
    <td align="center">
      <img src="docs/screenshots/ui-adhoc-dark.png" height="400" alt="Dark Mode UI">
      <br><b>Dark Mode — Ad-Hoc Commands</b>
    </td>
    <td align="center">
      <img src="docs/screenshots/ui-playbook-light.png" height="400" alt="Light Mode UI">
      <br><b>Light Mode — Playbook Editor</b>
    </td>
  </tr>
</table>

## Features

- **Ad-hoc Commands** — Run quick Ansible modules against your hosts
- **Playbook Execution** — Execute full YAML playbooks from the browser
- **Playbook Library** — Save and load playbooks from server storage
- **Inventory Management** — Save and reuse inventories from the sidebar
- **Collections & Roles** — Install, manage, and import/export Ansible Galaxy content
- **Secure Authentication** — SSH password and privilege escalation support
- **Output Download** — Save command outputs as text files
- **Command History** — Browse and restore previous commands

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/aydinguven/ekumen/main/scripts/install.sh | sudo bash
```

The service starts automatically on port 5000.

## Alternative Installation

| Method | Documentation |
|--------|--------------|
| **Docker / Podman** | [docs/docker.md](docs/docker.md) |
| **Offline Install** | [docs/offline-install.md](docs/offline-install.md) |

## Configuration

Set environment variables for production:

```bash
export ANSIBLE_SHUTTLE_DEBUG=false
export ANSIBLE_SHUTTLE_HOST=0.0.0.0
export ANSIBLE_SHUTTLE_PORT=5000
```

## Uninstall

```bash
sudo systemctl stop ekumen
sudo systemctl disable ekumen
sudo rm /etc/systemd/system/ekumen.service
sudo systemctl daemon-reload
sudo rm -rf /opt/ekumen
```

## Security Notes

- This application executes Ansible commands on the server
- Deploy behind a reverse proxy with HTTPS in production
- Restrict network access appropriately
- Passwords are never stored, only used in-memory for execution

## Roadmap

### Completed

| Feature | Version | Description |
|---------|---------|-------------|
| Command History | v1.3.0 | Browse and restore previous commands |
| Syntax Highlighting | v1.3.0 | CodeMirror-based YAML editor |
| Playbook Library | v1.4.0 | Save/load playbooks from server storage |
| Inventory Management | v1.5.0 | Save and reuse inventories from sidebar |
| Host Limiting | v1.5.4 | Target specific hosts with `--limit` |
| Collections & Roles | v1.6.0 | Install/manage Ansible Galaxy content |
| Containerization | v1.7.0 | Docker/Podman support |
| GitHub Actions CI/CD | v1.7.2 | Auto-build container images on release |

### Planned

- [ ] **Live Output Streaming** — Real-time output via SSE/WebSockets

## License

MIT License — see [LICENSE](LICENSE) for details.
