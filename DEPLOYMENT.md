# Deployment Guide - ERT Station

This guide covers deploying ERT Station to various platforms.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Local Development](#local-development)
3. [Linux Server Deployment](#linux-server-deployment)
4. [Docker Deployment](#docker-deployment)
5. [GitHub Actions CI/CD](#github-actions-cicd)
6. [Production Checklist](#production-checklist)
7. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Quick Start

### 1-Minute Setup (Local)

```bash
git clone https://github.com/yourusername/manech_ert.git
cd manech_ert
bash setup.sh
make dev
# Open http://localhost:8000
```

---

## Local Development

### Using Makefile

```bash
# Complete setup
make setup

# Start development (both server + queue worker)
make dev

# Or run separately:
make serve          # Terminal 1
make queue-work     # Terminal 2
```

### Manual Steps

```bash
# Install dependencies
composer install
source venv/bin/activate && pip install -r requirements.txt

# Database setup
cp .env.example .env
php artisan key:generate
php artisan migrate
php artisan db:seed

# Run servers
php artisan serve          # http://localhost:8000
php artisan queue:work     # Background jobs
```

---

## Linux Server Deployment

### Prerequisites

```bash
sudo apt update && sudo apt upgrade -y

# Install Stack
sudo apt install -y \
    php8.3 \
    php8.3-cli \
    php8.3-common \
    php8.3-imap \
    php8.3-intl \
    php8.3-json \
    php8.3-mbstring \
    php8.3-mysql \
    php8.3-zip \
    php8.3-fpm \
    composer \
    nginx \
    mysql-client \
    python3 \
    python3-venv \
    git \
    curl

# Verify installations
php -v
composer -V
python3 --version
```

### Step 1: Clone Repository

```bash
cd /var/www
sudo git clone https://github.com/yourusername/manech_ert.git
cd manech_ert
sudo chown -R $USER:www-data .
```

### Step 2: Setup Application

```bash
# Run setup script
bash setup.sh

# Install dependencies
composer install --no-dev --optimize-autoloader
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
# Edit .env for production
nano .env
```

**Key production settings:**
```env
APP_ENV=production
APP_DEBUG=false
APP_KEY=<generate-via-artisan>

DB_HOST=<your-db-host>
DB_DATABASE=ert_station
DB_USERNAME=ert_user
DB_PASSWORD=<strong-password>

QUEUE_CONNECTION=database
```

### Step 4: Database Setup (if using RDS or external DB)

```bash
# From the server
mysql -h <db-host> -u ert_user -p'<password>' << EOF
CREATE DATABASE IF NOT EXISTS ert_station CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON ert_station.* TO 'ert_user'@'%' IDENTIFIED BY '<password>';
FLUSH PRIVILEGES;
EOF

# Run migrations
php artisan migrate --force
php artisan db:seed --force
```

### Step 5: Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/manech_ert
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    root /var/www/manech_ert/public;
    index index.php index.html index.htm;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    location ~ /\.ht {
        deny all;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/manech_ert /etc/nginx/sites-enabled/

# Remove default
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 6: Configure PHP-FPM

```bash
sudo nano /etc/php/8.3/fpm/php.ini
```

**Key settings:**
```ini
upload_max_filesize = 64M
post_max_size = 64M
max_execution_time = 300
memory_limit = 256M
```

```bash
sudo systemctl restart php8.3-fpm
```

### Step 7: Setup Systemd Services

**Laravel Queue Worker:**
```bash
sudo tee /etc/systemd/system/laravel-queue.service > /dev/null << EOF
[Unit]
Description=Laravel Queue Worker
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/manech_ert
ExecStart=/usr/bin/php artisan queue:work --tries=1 --timeout=3600
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start laravel-queue
sudo systemctl enable laravel-queue
```

**Laravel Scheduler (if needed):**
```bash
sudo tee /etc/cron.d/laravel > /dev/null << EOF
* * * * * www-data cd /var/www/manech_ert && php artisan schedule:run >> /dev/null 2>&1
EOF
```

### Step 8: SSL Certificate (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal is automatic with Certbot
sudo systemctl start certbot.timer
```

### Step 9: Cache Optimization

```bash
php artisan config:cache
php artisan route:cache
php artisan view:cache

# For production
php artisan optimize
```

### Step 10: Verify Deployment

```bash
curl -I https://your-domain.com
```

Expected headers:
```
HTTP/2 200 OK
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM php:8.3-fpm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git composer curl zip unzip \
    libmysqlclient-dev python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install PHP extensions
RUN docker-php-ext-install pdo pdo_mysql mbstring zip

# Set working directory
WORKDIR /app

# Copy application
COPY . .

# Install PHP dependencies
RUN composer install --no-dev --optimize-autoloader

# Setup Python environment
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install -r requirements.txt

# Set permissions
RUN chown -R www-data:www-data . && \
    chmod -R 775 storage bootstrap/cache

EXPOSE 9000

CMD ["php-fpm"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: ert_app
    working_dir: /app
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - DB_HOST=db
      - DB_DATABASE=ert_station
      - DB_USERNAME=ert_user
      - DB_PASSWORD=secure_password
    depends_on:
      - db
    volumes:
      - ./:/app
      - ./storage:/app/storage

  db:
    image: mysql:8.0
    container_name: ert_db
    environment:
      MYSQL_DATABASE: ert_station
      MYSQL_USER: ert_user
      MYSQL_PASSWORD: secure_password
      MYSQL_ROOT_PASSWORD: root_password
    ports:
      - "3306:3306"
    volumes:
      - db_data:/var/lib/mysql

  nginx:
    image: nginx:latest
    container_name: ert_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./:/app
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - app

volumes:
  db_data:
```

**Deploy:**
```bash
docker-compose up -d
docker-compose exec app php artisan migrate
docker-compose exec app php artisan queue:work
```

---

## GitHub Actions CI/CD

### Create .github/workflows/deploy.yml

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_DATABASE: ert_station_test
          MYSQL_ROOT_PASSWORD: password
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3
        ports:
          - 3306:3306

    steps:
      - uses: actions/checkout@v3
      
      - name: Setup PHP
        uses: shivammathur/setup-php@v2
        with:
          php-version: '8.3'
          extensions: mysql, mbstring, zip
          coverage: xdebug

      - name: Install Dependencies
        run: composer install --no-progress

      - name: Copy .env
        run: php -r "file_exists('.env') || copy('.env.example', '.env');"

      - name: Generate Key
        run: php artisan key:generate

      - name: Run Migrations
        run: php artisan migrate
        env:
          DB_HOST: localhost
          DB_DATABASE: ert_station_test
          DB_USERNAME: root
          DB_PASSWORD: password

      - name: Run Tests
        run: php artisan test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /var/www/manech_ert
            git pull origin main
            composer install --no-dev
            php artisan migrate --force
            php artisan cache:clear
            php artisan config:cache
            sudo systemctl restart laravel-queue
            sudo systemctl restart php8.3-fpm
```

---

## Production Checklist

- [ ] `.env` configured for production
- [ ] `APP_DEBUG=false`
- [ ] `APP_ENV=production`
- [ ] `APP_KEY` generated
- [ ] Database encrypted/backed up
- [ ] SSL certificate installed (HTTPS only)
- [ ] Firewall configured (80, 443 only)
- [ ] Rate limiting enabled
- [ ] CORS configured correctly
- [ ] Backup strategy in place
- [ ] Monitoring enabled
- [ ] Error logging configured
- [ ] Database user has limited privileges

---

## Monitoring & Maintenance

### Log Monitoring

```bash
# Real-time logs
tail -f /var/www/manech_ert/storage/logs/laravel.log

# Last 100 errors
grep ERROR /var/www/manech_ert/storage/logs/laravel.log | tail -100
```

### Backup Strategy

```bash
#!/bin/bash
# Backup database and files
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/backups/manech_ert"

# Database backup
mysqldump -h localhost -u ert_user -p'password' ert_station > "$BACKUP_DIR/db_$DATE.sql"

# Files backup
tar -czf "$BACKUP_DIR/files_$DATE.tar.gz" /var/www/manech_ert/storage

# Keep last 30 days
find "$BACKUP_DIR" -name "*.sql" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

### Health Check

```bash
# Check if services are running
systemctl status nginx
systemctl status php8.3-fpm
systemctl status laravel-queue

# Check disk space
df -h

# Check MySQL connection
mysql -h localhost -u ert_user -p'password' ert_station -e "SELECT 1"
```

---

## Troubleshooting

### Queue Jobs Not Processing
```bash
sudo systemctl restart laravel-queue
php artisan queue:failed  # Check failed jobs
php artisan queue:retry   # Retry failed jobs
```

### Database Migration Errors
```bash
php artisan migrate:rollback
php artisan migrate --step=1
```

### File Permissions
```bash
sudo chown -R www-data:www-data /var/www/manech_ert
chmod -R 775 /var/www/manech_ert/storage
```

---

**Last Updated:** May 23, 2026  
**Version:** 1.0.0
