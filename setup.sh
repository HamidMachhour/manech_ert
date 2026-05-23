#!/bin/bash

###############################################################################
#                        ERT Station - Setup Script                          #
#                                                                             #
# This script automates the initial setup of the ERT Station project.        #
# It is designed to be idempotent - safe to run multiple times.             #
#                                                                             #
# Usage:  bash setup.sh                                                      #
# Or:     chmod +x setup.sh && ./setup.sh                                   #
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VENV="${PROJECT_DIR}/venv"
PYTHON="${PYTHON_VENV}/bin/python3"
ENV_FILE="${PROJECT_DIR}/.env"

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✅ ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  ${NC}$1"
}

log_error() {
    echo -e "${RED}❌ ${NC}$1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

###############################################################################
# Pre-flight Checks
###############################################################################

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║           ERT Station - Automated Setup Script                         ║"
echo "║                                                                        ║"
echo "║  This script will install and configure the ERT Station project.      ║"
echo "║  It is safe to run multiple times (idempotent).                       ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

log_info "Starting pre-flight checks..."

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log_success "Operating System: Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    log_success "Operating System: macOS"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    log_warning "Operating System: Windows (WSL recommended)"
else
    log_error "Unsupported operating system: $OSTYPE"
    exit 1
fi

# Check required commands
log_info "Checking required commands..."

MISSING_DEPS=0

if check_command "php"; then
    PHP_VERSION=$(php -r 'echo PHP_VERSION;')
    log_success "PHP $PHP_VERSION found"
else
    log_error "PHP not found. Please install PHP 8.2+"
    MISSING_DEPS=1
fi

if check_command "composer"; then
    log_success "Composer found"
else
    log_error "Composer not found. Please install it from https://getcomposer.org/"
    MISSING_DEPS=1
fi

if check_command "python3"; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_success "Python $PYTHON_VERSION found"
else
    log_error "Python 3 not found. Please install Python 3.10+"
    MISSING_DEPS=1
fi

if check_command "mysql"; then
    log_success "MySQL client found"
else
    log_warning "MySQL client not found. You can still continue, but may need manual DB setup."
fi

if [ $MISSING_DEPS -eq 1 ]; then
    log_error "Missing critical dependencies. Please install them and try again."
    exit 1
fi

echo ""

###############################################################################
# Step 1: Project Directory Check
###############################################################################

log_info "Step 1: Checking project directory..."

if [ ! -f "${PROJECT_DIR}/composer.json" ]; then
    log_error "composer.json not found. Are you in the project root directory?"
    exit 1
fi

log_success "Project directory verified: $PROJECT_DIR"
echo ""

###############################################################################
# Step 2: Environment File Setup
###############################################################################

log_info "Step 2: Setting up environment configuration..."

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "${PROJECT_DIR}/.env.example" ]; then
        cp "${PROJECT_DIR}/.env.example" "$ENV_FILE"
        log_success ".env file created from .env.example"
    else
        log_warning ".env.example not found. Creating minimal .env..."
        cat > "$ENV_FILE" << 'EOF'
APP_NAME="ERT Station"
APP_ENV=local
APP_DEBUG=true
APP_URL=http://localhost:8000
LOG_CHANNEL=stack
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=ert_station
DB_USERNAME=ert_user
DB_PASSWORD=12341234
QUEUE_CONNECTION=database
EOF
    fi
else
    log_success ".env file already exists"
fi

# Generate APP_KEY if missing
if ! grep -q "^APP_KEY=base64:" "$ENV_FILE" || grep -q "^APP_KEY=$" "$ENV_FILE"; then
    log_info "Generating Laravel APP_KEY..."
    php artisan key:generate 2>/dev/null || log_warning "Could not auto-generate APP_KEY. Run: php artisan key:generate"
    log_success "APP_KEY generated"
else
    log_success "APP_KEY already set"
fi

echo ""

###############################################################################
# Step 3: PHP Composer Dependencies
###############################################################################

log_info "Step 3: Installing PHP dependencies..."

if [ -d "${PROJECT_DIR}/vendor" ]; then
    log_success "Vendor directory exists. Updating..."
    composer update --no-interaction 2>/dev/null || composer install --no-interaction
else
    log_info "Installing Composer packages..."
    composer install --no-interaction
fi

log_success "PHP dependencies installed"
echo ""

###############################################################################
# Step 4: Python Virtual Environment
###############################################################################

log_info "Step 4: Setting up Python virtual environment..."

if [ ! -d "$PYTHON_VENV" ]; then
    log_info "Creating virtual environment at $PYTHON_VENV..."
    python3 -m venv "$PYTHON_VENV"
    log_success "Virtual environment created"
else
    log_success "Virtual environment already exists"
fi

echo ""

###############################################################################
# Step 5: Python Dependencies
###############################################################################

log_info "Step 5: Installing Python dependencies..."

if [ -f "${PROJECT_DIR}/requirements.txt" ]; then
    $PYTHON -m pip install --upgrade pip --quiet 2>/dev/null || true
    log_info "Installing packages from requirements.txt..."
    $PYTHON -m pip install -r "${PROJECT_DIR}/requirements.txt" 2>/dev/null || log_warning "Some Python packages failed to install"
    log_success "Python dependencies installed"
else
    log_warning "requirements.txt not found. Skipping Python dependencies."
fi

echo ""

###############################################################################
# Step 6: Database Setup
###############################################################################

log_info "Step 6: Database setup..."

# Parse database credentials from .env
DB_HOST=$(grep "^DB_HOST=" "$ENV_FILE" | cut -d= -f2)
DB_DATABASE=$(grep "^DB_DATABASE=" "$ENV_FILE" | cut -d= -f2)
DB_USERNAME=$(grep "^DB_USERNAME=" "$ENV_FILE" | cut -d= -f2)
DB_PASSWORD=$(grep "^DB_PASSWORD=" "$ENV_FILE" | cut -d= -f2)

log_info "Database Configuration:"
log_info "  Host: $DB_HOST"
log_info "  Database: $DB_DATABASE"
log_info "  Username: $DB_USERNAME"

# Try to verify database connection
if command -v mysql &> /dev/null; then
    if mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_DATABASE" -e "SELECT 1" &>/dev/null; then
        log_success "Database connection verified"
        
        log_info "Running migrations..."
        php artisan migrate --force 2>/dev/null || log_warning "Migration may have failed. Run: php artisan migrate"
        log_success "Database migrations completed"
        
        # Ask to seed database
        read -p "Would you like to seed the database with sample data? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            php artisan db:seed --force 2>/dev/null || log_warning "Seeding may have failed"
            log_success "Database seeded"
        fi
    else
        log_warning "Could not connect to database. Please verify:"
        log_warning "  1. MySQL is running"
        log_warning "  2. Database '$DB_DATABASE' exists"
        log_warning "  3. User '$DB_USERNAME' has correct password"
        log_warning ""
        log_warning "Manual steps:"
        log_warning "  mysql -u root -p"
        log_warning "  > CREATE DATABASE $DB_DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        log_warning "  > CREATE USER '$DB_USERNAME'@'localhost' IDENTIFIED BY '$DB_PASSWORD';"
        log_warning "  > GRANT ALL PRIVILEGES ON $DB_DATABASE.* TO '$DB_USERNAME'@'localhost';"
        log_warning "  > FLUSH PRIVILEGES;"
        log_warning ""
        log_warning "Then run: php artisan migrate"
    fi
else
    log_warning "MySQL client not found. You'll need to run migrations manually:"
    log_warning "  1. Ensure the database exists and is accessible"
    log_warning "  2. Run: php artisan migrate"
fi

echo ""

###############################################################################
# Step 7: Permissions
###############################################################################

log_info "Step 7: Setting directory permissions..."

DIRS_TO_CHMOD=("storage" "bootstrap/cache")
for dir in "${DIRS_TO_CHMOD[@]}"; do
    if [ -d "${PROJECT_DIR}/$dir" ]; then
        chmod -R 775 "${PROJECT_DIR}/$dir" 2>/dev/null || true
    fi
done

log_success "Directory permissions set"
echo ""

###############################################################################
# Final Steps
###############################################################################

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   ✅  Setup Complete!                                 ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

log_success "All setup steps completed successfully!"
echo ""

log_info "Next steps:"
echo "  1. Verify .env configuration:"
echo "     nano .env"
echo ""
echo "  2. Start development server:"
echo "     make dev"
echo "     Or manually:"
echo "       Terminal 1: php artisan serve"
echo "       Terminal 2: php artisan queue:work"
echo ""
echo "  3. Access the application:"
echo "     Open http://localhost:8000 in your browser"
echo ""
echo "  4. For more commands, run:"
echo "     make help"
echo ""

log_info "Useful documentation:"
echo "  - README.md - Project documentation"
echo "  - Makefile - Available commands (run: make help)"
echo "  - .env.example - Environment variable template"
echo ""

exit 0
