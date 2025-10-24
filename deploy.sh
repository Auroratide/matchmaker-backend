#!/bin/bash

# Deploy matchmake_scheduled function to Google Cloud Functions
# This script deploys the scheduled matchmaking function that can be triggered by Cloud Scheduler

set -e  # Exit on any error

PROJECT_ID="${GCLOUD_PROJECT_ID}"
REGION="${GCLOUD_REGION}"
MATCHMAKE_FUNCTION_NAME="matchmake_scheduled"
MATCHMAKE_ENTRY_POINT="matchmake_scheduled"
VERIFY_FUNCTION_NAME="verify_email"
VERIFY_ENTRY_POINT="verify"
TOPIC="matchmake-trigger"
RUNTIME="${RUNTIME:-python311}"
MEMORY="${MEMORY:-512MB}"
TIMEOUT="${TIMEOUT:-540s}"  # 9 minutes (max for Cloud Functions gen1)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment of ${FUNCTION_NAME}...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
	echo -e "${RED}Error: gcloud CLI is not installed. Please install it first.${NC}"
	exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
	echo -e "${RED}Error: No active gcloud authentication found. Please run 'gcloud auth login' first.${NC}"
	exit 1
fi

# Validate project ID is set
if [ "$PROJECT_ID" = "YOUR_PROJECT_ID" ]; then
	echo -e "${RED}Error: Please update PROJECT_ID in this script with your actual GCP project ID.${NC}"
	exit 1
fi

# Set the project
echo -e "${YELLOW}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project $PROJECT_ID

# Check if .env file exists for environment variables
if [ ! -f ".env" ]; then
	echo -e "${RED}Error: .env file not found. Please create it based on .env.example${NC}"
	exit 1
fi

# Read environment variables from .env file
echo -e "${YELLOW}Reading environment variables from .env file...${NC}"
ENV_VARS=""
while IFS='=' read -r key value; do
	# Skip empty lines and comments
	if [[ -n "$key" && ! "$key" =~ ^[[:space:]]*# ]]; then
		# Remove any quotes from the value
		value=$(echo "$value" | sed 's/^["'\'']//' | sed 's/["'\'']$//')
		if [ -n "$ENV_VARS" ]; then
			ENV_VARS="${ENV_VARS},"
		fi
		ENV_VARS="${ENV_VARS}${key}=${value}"
	fi
done < .env

if [ -z "$ENV_VARS" ]; then
	echo -e "${RED}Error: No environment variables found in .env file${NC}"
	exit 1
fi

echo -e "${YELLOW}Found environment variables: $(echo $ENV_VARS | sed 's/=[^,]*//g')${NC}"

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable eventarc.googleapis.com

# Create Pub/Sub topic if it doesn't exist
echo -e "${YELLOW}Creating Pub/Sub topic if it doesn't exist...${NC}"
gcloud pubsub topics create $TOPIC --quiet || echo "Topic already exists"

# Deploy the functions
echo -e "${YELLOW}Deploying Matchmake Cloud Function...${NC}"
gcloud functions deploy $MATCHMAKE_FUNCTION_NAME \
	--gen2 \
	--runtime=$RUNTIME \
	--region=$REGION \
	--source=. \
	--entry-point=$MATCHMAKE_ENTRY_POINT \
	--memory=$MEMORY \
	--timeout=$TIMEOUT \
	--trigger-topic=$TOPIC \
	--set-env-vars="$ENV_VARS" \
	--max-instances=1 \
	--no-allow-unauthenticated

if [ $? -eq 0 ]; then
	echo -e "${GREEN}✅ Function deployed successfully!${NC}"
	echo -e "${GREEN}Function name: ${MATCHMAKE_FUNCTION_NAME}${NC}"
else
	echo -e "${RED}❌ Deployment failed!${NC}"
	exit 1
fi

echo -e "${YELLOW}Deploying Verify Cloud Function...${NC}"
gcloud functions deploy $VERIFY_FUNCTION_NAME \
	--gen2 \
	--runtime=$RUNTIME \
	--region=$REGION \
	--source=. \
	--entry-point=$VERIFY_ENTRY_POINT \
	--memory=$MEMORY \
	--timeout=$TIMEOUT \
	--trigger-http \
	--set-env-vars="$ENV_VARS" \
	--allow-unauthenticated

if [ $? -eq 0 ]; then
	echo -e "${GREEN}✅ Function deployed successfully!${NC}"
	echo -e "${GREEN}Function name: ${VERIFY_FUNCTION_NAME}${NC}"
else
	echo -e "${RED}❌ Deployment failed!${NC}"
	exit 1
fi

echo -e "${GREEN}Deployment complete!${NC}"
