#!/bin/bash

# Qdrant Vector Store Setup Script
# ================================
# This script sets up Qdrant using Docker and installs required Python dependencies

set -e

echo "🚀 Setting up Qdrant Vector Store..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker found"

# Stop and remove existing Qdrant container if running
echo "🧹 Cleaning up existing Qdrant containers..."
docker stop qdrant-freelancer 2>/dev/null || true
docker rm qdrant-freelancer 2>/dev/null || true

# Create data directory for persistent storage
mkdir -p ./qdrant_data
echo "📁 Created data directory: ./qdrant_data"

# Start Qdrant container
echo "🐳 Starting Qdrant container..."
docker run -d \
    --name qdrant-freelancer \
    -p 6333:6333 \
    -p 6334:6334 \
    -v $(pwd)/qdrant_data:/qdrant/storage \
    qdrant/qdrant:latest

# Wait for Qdrant to start
echo "⏳ Waiting for Qdrant to start..."
sleep 10

# Check if Qdrant is running
if curl -s http://localhost:6333/health > /dev/null; then
    echo "✅ Qdrant is running successfully!"
    echo "🌐 Web UI available at: http://localhost:6333/dashboard"
    echo "🔗 API endpoint: http://localhost:6333"
else
    echo "❌ Failed to start Qdrant"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip

# Core dependencies
pip install qdrant-client==1.6.9
pip install sentence-transformers==2.2.2
pip install mysql-connector-python==8.2.0

# Optional dependencies for better performance
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers==4.35.2
pip install numpy==1.24.3

echo "✅ Python dependencies installed!"

# Test the installation
echo "🧪 Testing Qdrant connection..."
python3 -c "
from qdrant_client import QdrantClient
try:
    client = QdrantClient('localhost', port=6333)
    info = client.get_collections()
    print('✅ Qdrant connection successful!')
    print(f'📊 Available collections: {len(info.collections)}')
except Exception as e:
    print(f'❌ Connection failed: {e}')
    exit(1)
"

echo ""
echo "🎉 Qdrant setup complete!"
echo ""
echo "Next steps:"
echo "1. Run: python3 qdrant_vector_store.py"
echo "2. This will populate Qdrant with your MySQL data"
echo "3. Use the integration scripts to enhance job matching"
echo ""
echo "📋 Useful commands:"
echo "- View logs: docker logs qdrant-freelancer"
echo "- Stop: docker stop qdrant-freelancer"
echo "- Start: docker start qdrant-freelancer"
echo "- Remove: docker rm qdrant-freelancer"