"""
Ekumen - Built-in Playbook Templates Service
Provides production-ready Ansible playbook templates for common infrastructure tasks.
"""

from typing import List, Dict, Optional


PLAYBOOK_TEMPLATES = [
    {
        "id": "system_update",
        "name": "System Update & Clean",
        "category": "Maintenance",
        "description": "Updates packages across Debian/Ubuntu/RHEL/CentOS/Rocky and cleans up unused dependencies.",
        "icon": "🔄",
        "content": """---
- name: Comprehensive System Update & Clean
  hosts: all
  become: true
  tasks:
    - name: Update apt cache and upgrade packages (Debian/Ubuntu)
      apt:
        update_cache: true
        upgrade: dist
        autoremove: true
        autoclean: true
      when: ansible_os_family == "Debian"

    - name: Upgrade all packages with DNF (RHEL/CentOS/Rocky/Fedora)
      dnf:
        name: "*"
        state: latest
        autoremove: true
      when: ansible_os_family == "RedHat" and ansible_pkg_mgr == "dnf"

    - name: Upgrade all packages with YUM (Older RedHat/CentOS)
      yum:
        name: "*"
        state: latest
      when: ansible_os_family == "RedHat" and ansible_pkg_mgr == "yum"

    - name: Check if system reboot is required (Debian/Ubuntu)
      stat:
        path: /var/run/reboot-required
      register: reboot_required
      when: ansible_os_family == "Debian"

    - name: Report reboot status
      debug:
        msg: "⚠️ Reboot is REQUIRED on this host!"
      when: reboot_required is defined and reboot_required.stat.exists
"""
    },
    {
        "id": "nginx_setup",
        "name": "Nginx Web Server Setup",
        "category": "Web & Services",
        "description": "Installs Nginx, enables service on boot, and deploys a clean landing page.",
        "icon": "🌐",
        "content": """---
- name: Install and Configure Nginx Web Server
  hosts: all
  become: true
  vars:
    http_port: 80
    server_message: "Hello from Ekumen-managed Nginx!"

  tasks:
    - name: Install Nginx package
      package:
        name: nginx
        state: present

    - name: Deploy custom index.html
      copy:
        dest: /usr/share/nginx/html/index.html
        content: |
          <!DOCTYPE html>
          <html>
          <head><title>Managed by Ekumen</title></head>
          <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🚀 {{ server_message }}</h1>
            <p>Host: <strong>{{ ansible_hostname }}</strong> ({{ ansible_default_ipv4.address }})</p>
          </body>
          </html>
        mode: '0644'
      ignore_errors: true

    - name: Ensure Nginx is running and enabled on boot
      service:
        name: nginx
        state: started
        enabled: true
"""
    },
    {
        "id": "docker_install",
        "name": "Docker & Docker Compose",
        "category": "DevOps & Containers",
        "description": "Installs Docker Engine, Docker CLI, and Docker Compose plugin.",
        "icon": "🐳",
        "content": """---
- name: Install Docker & Docker Compose
  hosts: all
  become: true
  tasks:
    - name: Install prerequisites (Debian/Ubuntu)
      apt:
        name:
          - ca-certificates
          - curl
          - gnupg
        state: present
        update_cache: true
      when: ansible_os_family == "Debian"

    - name: Install Docker via official get.docker.com script
      shell: "curl -fsSL https://get.docker.com | sh"
      args:
        creates: /usr/bin/docker

    - name: Ensure Docker service is running and enabled
      service:
        name: docker
        state: started
        enabled: true

    - name: Verify Docker version
      command: docker --version
      register: docker_ver
      changed_when: false

    - name: Display installed Docker version
      debug:
        msg: "Docker successfully installed: {{ docker_ver.stdout }}"
"""
    },
    {
        "id": "user_management",
        "name": "User & Sudo Management",
        "category": "Security & Users",
        "description": "Creates a designated system user with sudo access and bash shell.",
        "icon": "👤",
        "content": """---
- name: Provision Administrative User
  hosts: all
  become: true
  vars:
    username: deployer
    user_shell: /bin/bash

  tasks:
    - name: Create group for user
      group:
        name: "{{ username }}"
        state: present

    - name: Create user account
      user:
        name: "{{ username }}"
        group: "{{ username }}"
        groups: "{{ 'sudo' if ansible_os_family == 'Debian' else 'wheel' }}"
        append: true
        shell: "{{ user_shell }}"
        state: present

    - name: Enable passwordless sudo for user
      lineinfile:
        path: "/etc/sudoers.d/{{ username }}"
        line: "{{ username }} ALL=(ALL) NOPASSWD:ALL"
        create: true
        mode: '0440'
        validate: 'visudo -cf %s'
"""
    },
    {
        "id": "system_health_check",
        "name": "System Health & Fact Discovery",
        "category": "Diagnostics",
        "description": "Gathers system architecture, CPU, Memory, and Disk stats.",
        "icon": "🩺",
        "content": """---
- name: System Health & Diagnostics
  hosts: all
  gather_facts: true
  tasks:
    - name: Check Disk Usage
      command: df -h /
      register: disk_info
      changed_when: false

    - name: Check Memory Usage
      command: free -h
      register: mem_info
      changed_when: false

    - name: Check System Uptime
      command: uptime
      register: uptime_info
      changed_when: false

    - name: Print Diagnostic Summary
      debug:
        msg:
          - "Host: {{ ansible_hostname }} ({{ ansible_distribution }} {{ ansible_distribution_version }})"
          - "Kernel: {{ ansible_kernel }} ({{ ansible_architecture }})"
          - "CPUs: {{ ansible_processor_vcpus }} cores"
          - "Memory: {{ ansible_memtotal_mb }} MB total"
          - "Uptime: {{ uptime_info.stdout }}"
          - "Root Disk Space: {{ disk_info.stdout_lines[1] }}"
"""
    }
]


def list_templates() -> List[Dict]:
    """Return all available templates without full content for listing."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "category": t["category"],
            "description": t["description"],
            "icon": t["icon"]
        }
        for t in PLAYBOOK_TEMPLATES
    ]


def get_template(template_id: str) -> Optional[Dict]:
    """Retrieve full template by ID."""
    for t in PLAYBOOK_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
