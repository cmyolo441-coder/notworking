#!/bin/bash
# BITTU Cloud Deployment Script
# Deploy BITTU to various cloud platforms

set -e

echo "☁️  BITTU Cloud Deployment"
echo "=========================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker first."
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Build Docker image
echo "📦 Building Docker image..."
docker build -t bittu:latest .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo ""
echo "✅ Docker image built successfully!"
echo ""

# Deployment options
echo "Select deployment platform:"
echo "  1) Local (docker run)"
echo "  2) Docker Compose"
echo "  3) Kubernetes"
echo "  4) AWS ECS"
echo "  5) Google Cloud Run"
echo "  6) Azure Container Instances"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 Running locally..."
        docker run -it --rm \
            --name bittu \
            -v $(pwd)/workspace:/workspace \
            -e ZEDPY_API_KEY=${ZEDPY_API_KEY} \
            bittu:latest
        ;;
    2)
        echo ""
        echo "🚀 Starting with Docker Compose..."
        docker-compose up -d
        echo ""
        echo "✅ Started! View logs: docker-compose logs -f"
        echo "   Stop: docker-compose down"
        ;;
    3)
        echo ""
        echo "🚀 Deploying to Kubernetes..."
        
        # Create k8s deployment file
        cat > bittu-k8s.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bittu
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bittu
  template:
    metadata:
      labels:
        app: bittu
    spec:
      containers:
      - name: bittu
        image: bittu:latest
        stdin: true
        tty: true
        env:
        - name: ZEDPY_API_KEY
          valueFrom:
            secretKeyRef:
              name: bittu-secrets
              key: api-key
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      volumes:
      - name: workspace
        emptyDir: {}
---
apiVersion: v1
kind: Secret
metadata:
  name: bittu-secrets
type: Opaque
stringData:
  api-key: ${ZEDPY_API_KEY:-changeme}
EOF
        
        kubectl apply -f bittu-k8s.yaml
        echo "✅ Deployed to Kubernetes!"
        echo "   Check: kubectl get pods"
        ;;
    4)
        echo ""
        echo "🚀 Deploying to AWS ECS..."
        
        # Login to ECR
        aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
        
        # Create ECR repo if not exists
        aws ecr describe-repositories --repository-names bittu 2>/dev/null || \
            aws ecr create-repository --repository-name bittu
        
        # Tag and push
        docker tag bittu:latest $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/bittu:latest
        docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com/bittu:latest
        
        echo "✅ Pushed to ECR! Deploy via AWS Console or CLI."
        ;;
    5)
        echo ""
        echo "🚀 Deploying to Google Cloud Run..."
        
        # Configure Docker for GCR
        gcloud auth configure-docker
        
        # Build and push
        docker tag bittu:latest gcr.io/$(gcloud config get-value project)/bittu:latest
        docker push gcr.io/$(gcloud config get-value project)/bittu:latest
        
        # Deploy to Cloud Run
        gcloud run deploy bittu \
            --image gcr.io/$(gcloud config get-value project)/bittu:latest \
            --platform managed \
            --region us-central1 \
            --allow-unauthenticated \
            --stdin
        
        echo "✅ Deployed to Cloud Run!"
        ;;
    6)
        echo ""
        echo "🚀 Deploying to Azure Container Instances..."
        
        # Create resource group
        az group create --name bittu-rg --location eastus
        
        # Deploy container
        az container create \
            --resource-group bittu-rg \
            --name bittu \
            --image bittu:latest \
            --cpu 1 \
            --memory 1.5 \
            --ports 8080 \
            --environment-variables ZEDPY_API_KEY=${ZEDPY_API_KEY} \
            --tty
        
        echo "✅ Deployed to Azure!"
        echo "   Check: az container show --resource-group bittu-rg --name bittu"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Deployment complete!"
