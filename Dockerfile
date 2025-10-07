# FRIDAY AI: Multi-stage Docker build for LiveKit agent with automatic plugin modification
FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install LiveKit plugins
RUN pip install livekit-plugins-google livekit-plugins-cartesia livekit-plugins-deepgram

# Development stage with plugin modifications
FROM base as development

# Copy application code
COPY . .

# Copy plugin modification scripts
COPY backup_plugin_modifications/ ./backup_plugin_modifications/
COPY docker_scripts/ ./docker_scripts/

# Apply plugin modifications
RUN python docker_scripts/apply_modifications.py

# Verify modifications were applied correctly
RUN python docker_scripts/verify_modifications.py

# Create conversations directory
RUN mkdir -p conversations

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port for LiveKit agent
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0 if __import__('os').path.exists('conversations') else 1)"

# Default command
CMD ["python", "cagent.py"]

# Production stage (minimal)
FROM base as production

# Copy only necessary files
COPY cagent.py config.py prompts.py tools.py convo_save.py copy_utils.py ./
COPY backup_plugin_modifications/ ./backup_plugin_modifications/
COPY docker_scripts/ ./docker_scripts/

# Apply plugin modifications
RUN python docker_scripts/apply_modifications.py && \
    python docker_scripts/verify_modifications.py

# Create conversations directory
RUN mkdir -p conversations

# Remove unnecessary files
RUN rm -rf backup_plugin_modifications/ docker_scripts/ testing_plugins/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import config; config.setup_conversation_log(); print('Health check passed')"

# Production command
CMD ["python", "cagent.py"]
