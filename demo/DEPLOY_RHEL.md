# Deploying Ekumen Demo on RHEL

These instructions have been tested on RHEL 8 and 9 (and derivatives like CentOS Stream, Rocky Linux, AlmaLinux).

## 1. Prerequisites

Ensure you have `git` and `python3` installed:

```bash
sudo dnf install -y git python3 python3-pip
```

## 2. Clone the Repository

Clone the repository and navigate to the demo directory:

```bash
git clone https://github.com/aydinguven/ekumen.git
cd ekumen/release/demo
```

## 3. Environment Setup

It is recommended to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Firewall Configuration

The demo runs on port **5005** by default. You need to allow this traffic:

```bash
sudo firewall-cmd --permanent --add-port=5005/tcp
sudo firewall-cmd --reload
```

## 5. Running the Application

### Option A: Quick Test
Run directly with Python (not recommended for long-term use):

```bash
export ANSIBLE_SHUTTLE_HOST=0.0.0.0
python3 app.py
```

### Option B: Production (Gunicorn)
Run using Gunicorn for better performance:

```bash
gunicorn -w 4 -b 0.0.0.0:5005 app:app
```

### Option C: Systemd Service (Persistent)
Create a service file to keep the app running in the background and on boot.

1. Create the service file:
   ```bash
   sudo nano /etc/systemd/system/ekumen-demo.service
   ```

2. Paste the following content (adjust paths/user as needed):
   ```ini
   [Unit]
   Description=Ekumen Demo
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/root/ekumen/release/demo
   Environment="PATH=/root/ekumen/release/demo/venv/bin"
   Environment="ANSIBLE_SHUTTLE_HOST=0.0.0.0"
   Environment="ANSIBLE_SHUTTLE_PORT=5005"
   ExecStart=/root/ekumen/release/demo/venv/bin/gunicorn -w 2 -b 0.0.0.0:5005 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now ekumen-demo
   ```

4. Check status:
   ```bash
   sudo systemctl status ekumen-demo
   ```

## 6. Accessing the Demo
Open your browser and navigate to:
`http://<YOUR_SERVER_IP>:5005`
