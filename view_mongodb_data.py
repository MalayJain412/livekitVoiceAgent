#!/usr/bin/env python3
"""
Quick MongoDB Data Viewer for Friday AI
Display current leads, conversations, and stats
"""

import logging
from datetime import datetime
from mongodb_queries import (
    get_lead_stats, get_recent_leads, get_conversation_stats,
    LeadQueries, ConversationQueries, TranscriptQueries,
    ReportGenerator
)
from db_config import test_connection

def display_section(title: str, data: dict = None):
    """Display a section with formatting"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    
    if data:
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                print(f"{key}: {len(value) if isinstance(value, list) else 'dict'}")
            else:
                print(f"{key}: {value}")

def main():
    """Main function to display MongoDB data"""
    print("Friday AI - MongoDB Data Viewer")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test connection first
    if not test_connection():
        print("❌ MongoDB connection failed!")
        return
    
    print("✅ MongoDB connection successful!")
    
    try:
        # Lead Statistics
        print("\n📊 LEAD STATISTICS")
        lead_stats = get_lead_stats()
        if lead_stats:
            print(f"Total Leads: {lead_stats.get('total_leads', 0)}")
            print(f"Recent Leads (7 days): {lead_stats.get('recent_leads_7_days', 0)}")
            print(f"Status Distribution: {lead_stats.get('status_distribution', {})}")
            
            if lead_stats.get('top_companies'):
                print("\nTop Companies:")
                for company in lead_stats['top_companies'][:5]:
                    print(f"  - {company['_id']}: {company['count']} leads")
            
            if lead_stats.get('top_interests'):
                print("\nTop Interests:")
                for interest in lead_stats['top_interests'][:5]:
                    print(f"  - {interest['_id']}: {interest['count']} leads")
        
        # Recent Leads
        print("\n📋 RECENT LEADS (Last 10)")
        recent_leads = get_recent_leads(days=30)
        if recent_leads:
            for i, lead in enumerate(recent_leads[:10], 1):
                created = lead.get('created_at', lead.get('timestamp', 'Unknown'))
                print(f"  {i}. {lead.get('name', 'N/A')} ({lead.get('email', 'N/A')}) - {lead.get('company', 'N/A')}")
                print(f"     Interest: {lead.get('interest', 'N/A')} | Status: {lead.get('status', 'new')}")
        else:
            print("No recent leads found")
        
        # Conversation Statistics
        print("\n💬 CONVERSATION STATISTICS")
        conv_stats = get_conversation_stats()
        if conv_stats:
            print(f"Total Sessions: {conv_stats.get('total_sessions', 0)}")
            print(f"Sessions with Leads: {conv_stats.get('sessions_with_leads', 0)}")
            print(f"Lead Conversion Rate: {conv_stats.get('lead_conversion_rate', 0):.1f}%")
            print(f"Average Session Duration: {conv_stats.get('average_duration_seconds', 0):.1f} seconds")
            print(f"Recent Sessions (7 days): {conv_stats.get('recent_sessions_7_days', 0)}")
        
        # Recent Sessions
        print("\n📞 RECENT CONVERSATION SESSIONS (Last 5)")
        recent_sessions = ConversationQueries.get_recent_sessions(days=7, limit=5)
        if recent_sessions:
            for i, session in enumerate(recent_sessions, 1):
                start_time = session.get('start_time', 'Unknown')
                duration = session.get('duration_seconds', 0)
                items = session.get('total_items', 0)
                lead_gen = "✅" if session.get('lead_generated') else "❌"
                print(f"  {i}. Session: {session.get('session_id', 'N/A')[:20]}...")
                print(f"     Start: {start_time} | Duration: {duration}s | Items: {items} | Lead: {lead_gen}")
        else:
            print("No recent sessions found")
        
        # Transcript Statistics
        print("\n📝 TRANSCRIPT STATISTICS")
        transcript_stats = TranscriptQueries.get_transcript_stats()
        if transcript_stats:
            print(f"Total Events: {transcript_stats.get('total_events', 0)}")
            print(f"Recent Events (24h): {transcript_stats.get('recent_events_24h', 0)}")
            print(f"Unique Sessions: {transcript_stats.get('unique_sessions', 0)}")
            print(f"Events by Role: {transcript_stats.get('events_by_role', {})}")
        
        # Weekly Summary
        print("\n📈 WEEKLY SUMMARY REPORT")
        weekly_summary = ReportGenerator.generate_weekly_summary()
        if weekly_summary and 'summary' in weekly_summary:
            summary = weekly_summary['summary']
            print(f"Period: {weekly_summary.get('period', 'Unknown')}")
            print(f"Total Leads: {summary.get('total_leads', 0)}")
            print(f"Total Sessions: {summary.get('total_sessions', 0)}")
            print(f"Conversion Rate: {summary.get('lead_conversion_rate', 0):.1f}%")
            print(f"Avg Session Duration: {summary.get('average_session_duration_minutes', 0):.1f} minutes")
        
        print(f"\n{'='*60}")
        print(" MongoDB Data Display Complete ✅")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Error displaying data: {e}")
        logging.error(f"Error in main display function: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    main()