# ERT Station - Electrical Resistivity Tomography Management & Analysis Platform

A specialized web application and RESTful API built with Laravel that serves as the central control dashboard and data ingestion platform for managing field Electrical Resistivity Tomography (ERT) data, automating student lab assignment tracking, and coordinating geophysical datasets for subsurface imaging.

**ERT Station** is a comprehensive field survey management system designed for geophysical research institutions, educational laboratories, and professional surveying organizations. It integrates real-time hardware control, synthetic data generation for training, and advanced data exploration tools to streamline ERT workflow from field acquisition to subsurface interpretation.

## Table of Contents

- [Key Capabilities](#key-capabilities)
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Deployment](#deployment)
- [Development](#development)
- [API Documentation](#api-documentation)

---

## Key Capabilities

✅ **Field Data Management** — Organize and track multiple ERT surveys with full metadata and location references  
✅ **Real-Time Acquisition Control** — Start, monitor, and abort ground surveys with live progress tracking  
✅ **Student Lab Assignment System** — Automate workflow management and data processing for educational institutions  
✅ **Advanced Data Explorer** — Paginate, filter, and analyze thousands of matrix points with subsurface-aware visualization  
✅ **RES2DINV Export** — Export survey data in industry-standard format for professional inversion software  
✅ **Synthetic Physics Emulation** — Generate realistic subsurface structures (aquifers, clay layers, anomalies) for training and validation  
✅ **Hardware-Agnostic Design** — Easily integrate with real geophysical hardware or use emulator for prototyping  
✅ **RESTful API** — Complete JSON API for programmatic data access and integration with external systems

---

## Project Overview

### For Researchers & Geophysicists

ERT Station centralizes the complete workflow:
- **Field Management**: Organize multi-site surveys with GPS coordinates and metadata
- **Data Pipeline**: Automated data ingestion from hardware or manual input
- **Quality Assurance**: Real-time filtering and anomaly detection
- **Export**: Industry-standard RES2DINV format for inversion workflows
- **Collaboration**: Multi-user access with role-based permissions

### For Educational Institutions

ERT Station simplifies student lab assignments:
- **Lab Management**: Create and distribute student assignments with predetermined scan configurations
- **Progress Tracking**: Monitor student data acquisition in real-time
- **Automated Evaluation**: Validate student data quality and completeness
- **Data Archival**: Maintain institutional dataset repository for teaching materials
- **Virtual Lab**: Python emulator allows offline training and prototyping

### Technical Foundation

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Laravel 11, PHP 8.2+ | Web application & API |
| **Frontend** | Blade Templates, JavaScript | Interactive dashboard |
| **Database** | MySQL 8.0+ | Data persistence |
| **Emulator** | Python 3.10+, NumPy | Hardware simulation |
| **Queue** | Laravel Queue | Background job processing |
| **API** | RESTful JSON | External integrations |

---

## Architecture

### Directory Structure

```
manech_ert/
├── app/
│   ├── Console/Jobs/          # Queue jobs (RunGroundScan)
│   ├── Http/Controllers/      # API & Web controllers
│   ├── Models/                # Eloquent models (Scan, MatrixPoint, Project)
│   └── ...
├── emulator/
│   ├── matrix_scanner.py      # Python hardware emulator with synthetic physics
│   └── __init__.py
├── resources/views/
│   ├── scans/show.blade.php   # Data grid, explorer, export UI
│   ├── projects/              # Project management views
│   └── ...
├── routes/
│   ├── web.php                # Web routes
│   └── api.php
├── storage/
│   ├── logs/laravel.log       # Application logs
│   └── ...
├── database/
│   ├── migrations/            # Schema versions
│   └── seeders/
├── venv/                       # Python virtual environment
├── requirements.txt            # Python dependencies
├── Makefile                    # Build & dev commands
├── setup.sh                    # Automated setup script
└── README.md                   # This file
```

### Data Model

**Core Entities:**
- **Projects** - Survey sites/locations with metadata
- **Scans** - Individual ERT surveys within a project
- **MatrixPoints** - Electrode configuration data (A, B, M, N electrodes + measurements)
- **SystemStates** - System control flags (kill signal for emergency abort)

**Relationships:**
```
Project (1) ──── (N) Scans
Scan    (1) ──── (N) MatrixPoints
```

---

## System Requirements

### Minimum
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows (WSL2)
- **PHP**: 8.2 or higher
- **Python**: 3.10 or higher
- **MySQL**: 8.0 or higher
- **RAM**: 2 GB
- **Disk**: 1 GB

### Recommended
- **PHP**: 8.3+
- **MySQL**: 8.4+
- **Python**: 3.12+
- **RAM**: 4+ GB

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/manech_ert.git
cd manech_ert
```

### 2. Quick Setup (Recommended)

```bash
# Run the automated setup script
bash setup.sh

# Or use the Makefile
make setup
```

### 3. Manual Setup Steps

```bash
# PHP dependencies
composer install

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
php artisan key:generate

# Database
php artisan migrate
php artisan db:seed  # Optional: sample data
```

---

## Configuration

### Environment Variables (.env)

**Laravel Settings:**
```env
APP_URL=http://localhost:8000
APP_ENV=local
APP_DEBUG=true
```

**Database:**
```env
DB_HOST=127.0.0.1
DB_DATABASE=ert_station
DB_USERNAME=ert_user
DB_PASSWORD=12341234
```

**Python Emulator:**
```env
PYTHON_VENV_PATH=./venv
PYTHON_EXECUTABLE=${PYTHON_VENV_PATH}/bin/python3
```

### Database Initialization

```bash
# Create MySQL database and user
mysql -u root -p << EOF
CREATE DATABASE ert_station CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ert_user'@'localhost' IDENTIFIED BY '12341234';
GRANT ALL PRIVILEGES ON ert_station.* TO 'ert_user'@'localhost';
FLUSH PRIVILEGES;
EOF

# Run migrations
php artisan migrate
```

---

## Running the Application

### Development Server

```bash
# Terminal 1: Laravel web server
php artisan serve  # http://localhost:8000

# Terminal 2: Queue worker (for background jobs)
php artisan queue:work

# Terminal 3 (Optional): Real-time log monitoring
tail -f storage/logs/laravel.log
```

**Or use Makefile:**
```bash
make dev    # Starts both server & queue worker
```

### Production Server

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Nginx configuration
- SSL/TLS setup
- Systemd services
- Docker deployment
- GitHub Actions CI/CD

---

## API Documentation

### Core Endpoints

#### Projects
- `GET /projects` — List all projects
- `POST /projects` — Create new project
- `GET /projects/{id}/scans` — List scans in project

#### Scans
- `GET /scan/{id}` — Get scan details
- `POST /scan/start` — Start a new scan
- `POST /scan/abort` — Abort running scan
- `GET /scan/{id}/points` — Get paginated matrix points
  - Query parameters: `page`, `stake_a` (filter), `stake_b` (filter)
- `GET /scan/{id}/export` — Export scan to CSV (RES2DINV format)

#### Response Example

```json
{
  "current_page": 1,
  "data": [
    {
      "id": 944,
      "scan_id": 20,
      "stake_a": 1,
      "stake_b": 2,
      "stake_m": 3,
      "stake_n": 4,
      "measured_voltage": 9.543,
      "injected_current": 1.001,
      "calculated_apparent_resistivity": 28.615,
      "timestamp": "2026-05-23 10:30:10"
    }
  ],
  "last_page": 1,
  "total": 24,
  "per_page": 100
}
```

---

## Development

### Using Makefile Commands

```bash
make help               # Show all available commands
make dev               # Start dev server + queue
make serve             # Start web server only
make queue-work        # Start queue worker only
make test              # Run tests
make lint              # Check code style
make migrate           # Run database migrations
make db-reset          # Reset database
make logs              # Tail application logs
```

### Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style
- Writing tests
- Submitting pull requests
- Reporting bugs

### Testing

```bash
# Run all tests
make test

# With coverage
make coverage

# Lint code
make lint
```

---

## Troubleshooting

### Queue Jobs Not Processing

```bash
php artisan queue:work --tries=1 --timeout=3600 --verbose
```

### Matrix Points Not Appearing

1. Check queue is running: `ps aux | grep "queue:work"`
2. Check logs: `tail -f storage/logs/laravel.log`
3. Verify database: `SELECT COUNT(*) FROM matrix_points WHERE scan_id = 20;`

### Python Emulator Crashes

```bash
source venv/bin/activate
python3 emulator/matrix_scanner.py --scan_id=1 --spacing=1.0
```

### Database Connection Errors

```bash
mysql -h 127.0.0.1 -u ert_user -p12341234 -e "SELECT 1;" ert_station
```

---

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) — Multi-platform deployment guide
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution guidelines
- [SECURITY.md](SECURITY.md) — Security policies & vulnerability reporting
- [Makefile](Makefile) — Available build & development commands

---

## Support & Community

- **Issues**: Report bugs on GitHub
- **Discussions**: Share ideas and get help
- **Email**: support@manech_ert.local
- **Documentation**: See docs/ directory

---

**Last Updated:** May 23, 2026  
**Version:** 1.0.0  
**Status:** Production Ready

For security vulnerability reports, please email **security@manech_ert.local** instead of using the issue tracker. See [SECURITY.md](SECURITY.md) for full details.

## License

ERT Station is open-sourced software licensed under the [MIT license](LICENSE).

