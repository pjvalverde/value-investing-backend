#!/bin/bash

echo "Starting Value Investing API on Railway (simplified version)..."
echo "Environment variables:"
echo "PORT: $PORT"
echo "ALPHAVANTAGE_API_KEY: ${ALPHAVANTAGE_API_KEY:0:3}..."
echo "CLAUDE_API_KEY: ${CLAUDE_API_KEY:0:3}..."

python app_simple.py
