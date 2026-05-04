#!/bin/bash
# ============================================================================
# INSPECT-AI Production Deployment Script for Hetzner
# ============================================================================
# This script automates the deployment process
# Run with: bash scripts/deploy.sh
# ============================================================================

set -e  # Exit on any error

echo "============================================================================"
echo "🚀 INSPECT-AI Production Deployment"
echo "============================================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo ""
    echo "Please create it first:"
    echo "  1. cp .env.production.example .env"
    echo "  2. Edit .env and fill in your values"
    echo ""
    exit 1
fi

echo "✅ Found .env file"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker is not installed!"
    echo "Please install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ ERROR: Docker Compose is not available!"
    echo "Please install Docker Compose v2"
    exit 1
fi

echo "✅ Docker Compose is available"
echo ""

# Load environment variables
source .env

# Verify critical variables are set
if [ -z "$DOMAIN" ]; then
    echo "❌ ERROR: DOMAIN is not set in .env"
    echo "Please set DOMAIN in your .env file"
    exit 1
fi

echo "✅ Domain configured: $DOMAIN"
echo ""

# Check if DOMAIN contains REPLACE_ME
if [[ "$DOMAIN" == *"REPLACE_ME"* ]]; then
    echo "❌ ERROR: DOMAIN still contains 'REPLACE_ME'"
    echo "Please update DOMAIN in your .env file with your actual IP"
    exit 1
fi

echo "============================================================================"
echo "📦 Step 1: Building Docker Images"
echo "============================================================================"
echo ""

# Build the worker image first (if not built)
echo "Building worker image..."
docker compose -f docker-compose.yml build worker-image

# Build all production images
echo "Building production images..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

echo ""
echo "✅ Images built successfully"
echo ""

echo "============================================================================"
echo "📦 Step 2: Stopping Existing Containers (if any)"
echo "============================================================================"
echo ""

docker compose -f docker-compose.yml -f docker-compose.prod.yml down

echo ""
echo "✅ Stopped existing containers"
echo ""

echo "============================================================================"
echo "📦 Step 3: Starting Production Stack"
echo "============================================================================"
echo ""

# Start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo ""
echo "✅ All services started"
echo ""

echo "============================================================================"
echo "📦 Step 4: Waiting for Services to Be Healthy"
echo "============================================================================"
echo ""

echo "This may take 2-3 minutes for all services to initialize..."
echo ""

# Wait for API to be healthy
echo "⏳ Waiting for API..."
timeout=180
counter=0
until docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=5)" &> /dev/null; do
    sleep 5
    counter=$((counter + 5))
    if [ $counter -ge $timeout ]; then
        echo "❌ Timeout waiting for API to be healthy"
        echo "Check logs with: docker compose -f docker-compose.yml -f docker-compose.prod.yml logs api"
        exit 1
    fi
    echo "  Still waiting... (${counter}s)"
done

echo "✅ API is healthy"
echo ""

# Wait for Next.js to be healthy
echo "⏳ Waiting for Next.js frontend..."
counter=0
until docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T nextjs wget --spider -q http://localhost:3000/ &> /dev/null; do
    sleep 5
    counter=$((counter + 5))
    if [ $counter -ge $timeout ]; then
        echo "❌ Timeout waiting for Next.js to be healthy"
        echo "Check logs with: docker compose -f docker-compose.yml -f docker-compose.prod.yml logs nextjs"
        exit 1
    fi
    echo "  Still waiting... (${counter}s)"
done

echo "✅ Next.js is healthy"
echo ""

# Wait for Caddy to be healthy
echo "⏳ Waiting for Caddy reverse proxy..."
counter=0
until docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T caddy wget --spider -q http://localhost:80/ &> /dev/null; do
    sleep 5
    counter=$((counter + 5))
    if [ $counter -ge 60 ]; then
        echo "❌ Timeout waiting for Caddy to be healthy"
        echo "Check logs with: docker compose -f docker-compose.yml -f docker-compose.prod.yml logs caddy"
        exit 1
    fi
    echo "  Still waiting... (${counter}s)"
done

echo "✅ Caddy is healthy"
echo ""

echo "============================================================================"
echo "📦 Step 5: Running Database Migrations"
echo "============================================================================"
echo ""

# Run Alembic migrations
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api alembic upgrade head

echo ""
echo "✅ Database migrations completed"
echo ""

echo "============================================================================"
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "============================================================================"
echo ""
echo "Your INSPECT-AI application is now running!"
echo ""
echo "🌐 Access your application at:"
echo "   https://$DOMAIN"
echo ""
echo "📊 Useful Commands:"
echo ""
echo "View logs:"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
echo ""
echo "View specific service logs:"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f nextjs"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f caddy"
echo ""
echo "Check service status:"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
echo ""
echo "Stop all services:"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml down"
echo ""
echo "Restart services:"
echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
echo ""
echo "============================================================================"
echo ""
echo "⚠️  IMPORTANT: First-time SSL Certificate"
echo ""
echo "Caddy will automatically get an SSL certificate from Let's Encrypt."
echo "This may take 30-60 seconds on first access."
echo "If you see a security warning, wait a minute and refresh."
echo ""
echo "============================================================================"
