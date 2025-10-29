#!/usr/bin/env python3
"""
Temporary Scheduler API for Testing Upload Functionality
Runs upload cron logic via FastAPI/Uvicorn for testing without interfering with LiveKit agent.

This is a temporary testing setup that simulates cron behavior using Uvicorn.
Later this can be replaced with actual cron jobs or systemd timers.

Usage:
    uvicorn scheduler_api:app --host 0.0.0.0 --port 9000 --reload

Endpoints:
    GET / - Status check
    GET /force-sync - Manual trigger upload sync
    GET /status - Get current sync statistics
"""

from fastapi import FastAPI, BackgroundTasks
import asyncio
import time
import logging
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from upload_cron import CentralMetadataUploadCron, setup_logging

app = FastAPI(
    title="Voice Bot Upload Scheduler API",
    description="Temporary testing scheduler for upload functionality",
    version="1.0.0"
)

# Global variables for sync control
sync_running = False
last_sync_time = None
sync_stats = {
    "total_runs": 0,
    "successful_runs": 0,
    "failed_runs": 0,
    "last_sync_duration": 0,
    "last_sync_stats": {}
}

# Initialize the upload cron
upload_cron = CentralMetadataUploadCron(
    metadata_dir="call_metadata",
    batch_size=10  # Process up to 10 files per sync
)

async def periodic_sync(interval_seconds: int = 300):  # Default: 5 minutes
    """Periodic sync task that runs the upload cron"""
    global sync_running, last_sync_time, sync_stats

    while True:
        try:
            if not sync_running:
                sync_running = True
                last_sync_time = datetime.now()

                logging.info(f"[{last_sync_time.strftime('%H:%M:%S')}] Starting scheduled upload sync...")

                # Run the upload cron
                start_time = time.time()
                stats = upload_cron.run_scan_and_upload(dry_run=False)
                duration = time.time() - start_time

                # Update statistics
                sync_stats["total_runs"] += 1
                sync_stats["last_sync_duration"] = duration
                sync_stats["last_sync_stats"] = stats

                if stats.get("failed_uploads", 0) == 0:
                    sync_stats["successful_runs"] += 1
                    logging.info(f"Scheduled sync completed successfully in {duration:.1f}s")
                else:
                    sync_stats["failed_runs"] += 1
                    logging.warning(f"Scheduled sync completed with failures in {duration:.1f}s")

                sync_running = False

        except Exception as e:
            sync_stats["failed_runs"] += 1
            sync_running = False
            logging.error(f"Error in periodic sync: {e}", exc_info=True)

        # Wait for next interval
        await asyncio.sleep(interval_seconds)

@app.on_event("startup")
async def startup_event():
    """Start the periodic sync task when the app starts"""
    logging.info("Upload Scheduler API starting up...")
    logging.info("Starting periodic sync task (runs every 5 minutes)")

    # Start the periodic sync task
    asyncio.create_task(periodic_sync(interval_seconds=300))  # 5 minutes

@app.get("/")
async def root():
    """Root endpoint - status check"""
    return {
        "status": "Upload Scheduler API running",
        "timestamp": datetime.now().isoformat(),
        "sync_running": sync_running,
        "last_sync": last_sync_time.isoformat() if last_sync_time else None
    }

@app.get("/status")
async def get_status():
    """Get detailed sync statistics"""
    return {
        "sync_status": {
            "running": sync_running,
            "last_sync_time": last_sync_time.isoformat() if last_sync_time else None,
            "total_runs": sync_stats["total_runs"],
            "successful_runs": sync_stats["successful_runs"],
            "failed_runs": sync_stats["failed_runs"],
            "success_rate": f"{(sync_stats['successful_runs'] / sync_stats['total_runs'] * 100):.1f}%" if sync_stats["total_runs"] > 0 else "0%"
        },
        "last_sync_details": {
            "duration_seconds": f"{sync_stats['last_sync_duration']:.1f}",
            "stats": sync_stats["last_sync_stats"]
        },
        "configuration": {
            "metadata_dir": "call_metadata",
            "batch_size": 10,
            "sync_interval": "5 minutes"
        }
    }

@app.get("/force-sync")
async def force_sync(background_tasks: BackgroundTasks):
    """Manually trigger an upload sync"""
    global sync_running

    if sync_running:
        return {
            "error": "Sync already running",
            "message": "Please wait for the current sync to complete"
        }

    # Add sync task to background
    background_tasks.add_task(run_manual_sync)

    return {
        "message": "Manual sync started in background",
        "timestamp": datetime.now().isoformat()
    }

async def run_manual_sync():
    """Run a manual sync (called from force-sync endpoint)"""
    global sync_running, last_sync_time, sync_stats

    try:
        sync_running = True
        last_sync_time = datetime.now()

        logging.info(f"[{last_sync_time.strftime('%H:%M:%S')}] Starting manual upload sync...")

        # Run the upload cron
        start_time = time.time()
        stats = upload_cron.run_scan_and_upload(dry_run=False)
        duration = time.time() - start_time

        # Update statistics
        sync_stats["total_runs"] += 1
        sync_stats["last_sync_duration"] = duration
        sync_stats["last_sync_stats"] = stats

        if stats.get("failed_uploads", 0) == 0:
            sync_stats["successful_runs"] += 1
            logging.info(f"Manual sync completed successfully in {duration:.1f}s")
        else:
            sync_stats["failed_runs"] += 1
            logging.warning(f"Manual sync completed with failures in {duration:.1f}s")

    except Exception as e:
        sync_stats["failed_runs"] += 1
        logging.error(f"Error in manual sync: {e}", exc_info=True)
    finally:
        sync_running = False

@app.get("/dry-run")
async def dry_run():
    """Run a dry-run sync to see what would be uploaded"""
    try:
        logging.info("Starting dry-run sync...")

        # Create a temporary cron instance for dry run
        dry_run_cron = CentralMetadataUploadCron(
            metadata_dir="call_metadata",
            batch_size=10
        )

        stats = dry_run_cron.run_scan_and_upload(dry_run=True)

        return {
            "message": "Dry-run completed",
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }

    except Exception as e:
        logging.error(f"Error in dry-run: {e}", exc_info=True)
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Setup logging when run directly
    setup_logging(verbose=True)
    logging.info("Starting Upload Scheduler API...")