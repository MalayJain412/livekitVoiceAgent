"""
MongoDB Query Utilities for Friday AI
Provides helper functions for querying leads, conversations, and transcripts
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from db_config import get_collection, LeadsDB, ConversationDB, TranscriptDB

class LeadQueries:
    """Advanced query functions for leads collection"""
    
    @staticmethod
    def get_recent_leads(days: int = 30, limit: int = 100) -> List[Dict[str, Any]]:
        """Get leads from the last N days"""
        try:
            collection = get_collection("leads")
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            return list(collection.find({
                "timestamp": {"$gte": cutoff_date}
            }).sort("timestamp", -1).limit(limit))
            
        except Exception as e:
            logging.error(f"Error getting recent leads: {e}")
            return []
    
    @staticmethod
    def get_leads_by_company(company: str) -> List[Dict[str, Any]]:
        """Get all leads from a specific company"""
        try:
            collection = get_collection("leads")
            return list(collection.find({
                "company": {"$regex": company, "$options": "i"}
            }).sort("timestamp", -1))
            
        except Exception as e:
            logging.error(f"Error getting leads by company: {e}")
            return []
    
    @staticmethod
    def get_leads_by_interest(interest: str) -> List[Dict[str, Any]]:
        """Get leads interested in specific products/services"""
        try:
            collection = get_collection("leads")
            return list(collection.find({
                "interest": {"$regex": interest, "$options": "i"}
            }).sort("timestamp", -1))
            
        except Exception as e:
            logging.error(f"Error getting leads by interest: {e}")
            return []
    
    @staticmethod
    def get_leads_stats() -> Dict[str, Any]:
        """Get lead statistics"""
        try:
            collection = get_collection("leads")
            
            # Total counts by status
            pipeline = [
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            status_counts = {item["_id"]: item["count"] for item in collection.aggregate(pipeline)}
            
            # Total leads
            total_leads = collection.count_documents({})
            
            # Recent leads (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_leads = collection.count_documents({
                "timestamp": {"$gte": week_ago}
            })
            
            # Top companies
            company_pipeline = [
                {"$group": {
                    "_id": "$company",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            top_companies = list(collection.aggregate(company_pipeline))
            
            # Top interests
            interest_pipeline = [
                {"$group": {
                    "_id": "$interest",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            top_interests = list(collection.aggregate(interest_pipeline))
            
            return {
                "total_leads": total_leads,
                "recent_leads_7_days": recent_leads,
                "status_distribution": status_counts,
                "top_companies": top_companies,
                "top_interests": top_interests
            }
            
        except Exception as e:
            logging.error(f"Error getting lead stats: {e}")
            return {}
    
    @staticmethod
    def search_leads(query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search leads by name, email, or company"""
        try:
            collection = get_collection("leads")
            
            # Create text search across multiple fields
            search_filter = {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"email": {"$regex": query, "$options": "i"}}, 
                    {"company": {"$regex": query, "$options": "i"}},
                    {"interest": {"$regex": query, "$options": "i"}}
                ]
            }
            
            return list(collection.find(search_filter).sort("timestamp", -1).limit(limit))
            
        except Exception as e:
            logging.error(f"Error searching leads: {e}")
            return []

class ConversationQueries:
    """Advanced query functions for conversations collection"""
    
    @staticmethod
    def get_recent_sessions(days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent conversation sessions"""
        try:
            collection = get_collection("conversation_sessions")
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            return list(collection.find({
                "start_time": {"$gte": cutoff_date}
            }).sort("start_time", -1).limit(limit))
            
        except Exception as e:
            logging.error(f"Error getting recent sessions: {e}")
            return []
    
    @staticmethod
    def get_sessions_with_leads() -> List[Dict[str, Any]]:
        """Get sessions where leads were generated"""
        try:
            collection = get_collection("conversation_sessions")
            return list(collection.find({
                "lead_generated": True
            }).sort("start_time", -1))
            
        except Exception as e:
            logging.error(f"Error getting sessions with leads: {e}")
            return []
    
    @staticmethod
    def get_conversation_stats() -> Dict[str, Any]:
        """Get conversation statistics"""
        try:
            collection = get_collection("conversation_sessions")
            
            # Total sessions
            total_sessions = collection.count_documents({})
            
            # Sessions with leads
            lead_sessions = collection.count_documents({"lead_generated": True})
            
            # Recent sessions (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_sessions = collection.count_documents({
                "start_time": {"$gte": week_ago}
            })
            
            # Average session duration
            duration_pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_duration": {"$avg": "$duration_seconds"},
                    "max_duration": {"$max": "$duration_seconds"},
                    "min_duration": {"$min": "$duration_seconds"}
                }}
            ]
            duration_stats = list(collection.aggregate(duration_pipeline))
            duration_info = duration_stats[0] if duration_stats else {}
            
            # Sessions by hour (for pattern analysis)
            hourly_pipeline = [
                {"$project": {
                    "hour": {"$hour": "$start_time"}
                }},
                {"$group": {
                    "_id": "$hour",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ]
            hourly_distribution = list(collection.aggregate(hourly_pipeline))
            
            return {
                "total_sessions": total_sessions,
                "sessions_with_leads": lead_sessions,
                "recent_sessions_7_days": recent_sessions,
                "lead_conversion_rate": (lead_sessions / total_sessions * 100) if total_sessions > 0 else 0,
                "average_duration_seconds": duration_info.get("avg_duration", 0),
                "max_duration_seconds": duration_info.get("max_duration", 0),
                "min_duration_seconds": duration_info.get("min_duration", 0),
                "hourly_distribution": hourly_distribution
            }
            
        except Exception as e:
            logging.error(f"Error getting conversation stats: {e}")
            return {}
    
    @staticmethod
    def get_long_sessions(min_duration_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get sessions longer than specified duration"""
        try:
            collection = get_collection("conversation_sessions")
            min_seconds = min_duration_minutes * 60
            
            return list(collection.find({
                "duration_seconds": {"$gte": min_seconds}
            }).sort("duration_seconds", -1))
            
        except Exception as e:
            logging.error(f"Error getting long sessions: {e}")
            return []

class TranscriptQueries:
    """Advanced query functions for transcript events"""
    
    @staticmethod
    def get_session_transcript(session_id: str) -> List[Dict[str, Any]]:
        """Get all transcript events for a session"""
        try:
            collection = get_collection("transcript_events")
            return list(collection.find({
                "session_id": session_id
            }).sort("timestamp", 1))
            
        except Exception as e:
            logging.error(f"Error getting session transcript: {e}")
            return []
    
    @staticmethod
    def get_recent_events(hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent transcript events"""
        try:
            collection = get_collection("transcript_events")
            cutoff_date = datetime.utcnow() - timedelta(hours=hours)
            
            return list(collection.find({
                "timestamp": {"$gte": cutoff_date}
            }).sort("timestamp", -1).limit(limit))
            
        except Exception as e:
            logging.error(f"Error getting recent events: {e}")
            return []
    
    @staticmethod
    def search_transcript_content(query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search transcript content for specific text"""
        try:
            collection = get_collection("transcript_events")
            
            return list(collection.find({
                "content": {"$regex": query, "$options": "i"}
            }).sort("timestamp", -1).limit(limit))
            
        except Exception as e:
            logging.error(f"Error searching transcript content: {e}")
            return []
    
    @staticmethod
    def get_transcript_stats() -> Dict[str, Any]:
        """Get transcript statistics"""
        try:
            collection = get_collection("transcript_events")
            
            # Total events
            total_events = collection.count_documents({})
            
            # Events by role
            role_pipeline = [
                {"$group": {
                    "_id": "$role",
                    "count": {"$sum": 1}
                }}
            ]
            role_counts = {item["_id"]: item["count"] for item in collection.aggregate(role_pipeline)}
            
            # Recent events (last 24 hours)
            day_ago = datetime.utcnow() - timedelta(hours=24)
            recent_events = collection.count_documents({
                "timestamp": {"$gte": day_ago}
            })
            
            # Unique sessions
            unique_sessions = len(collection.distinct("session_id"))
            
            return {
                "total_events": total_events,
                "recent_events_24h": recent_events,
                "unique_sessions": unique_sessions,
                "events_by_role": role_counts
            }
            
        except Exception as e:
            logging.error(f"Error getting transcript stats: {e}")
            return {}

class ReportGenerator:
    """Generate comprehensive reports from MongoDB data"""
    
    @staticmethod
    def generate_daily_report(date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate daily activity report"""
        if date is None:
            date = datetime.utcnow()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        try:
            # Leads for the day
            leads_collection = get_collection("leads")
            daily_leads = list(leads_collection.find({
                "timestamp": {"$gte": start_of_day, "$lte": end_of_day}
            }))
            
            # Sessions for the day
            sessions_collection = get_collection("conversation_sessions")
            daily_sessions = list(sessions_collection.find({
                "start_time": {"$gte": start_of_day, "$lte": end_of_day}
            }))
            
            # Transcript events for the day
            events_collection = get_collection("transcript_events")
            daily_events_count = events_collection.count_documents({
                "timestamp": {"$gte": start_of_day, "$lte": end_of_day}
            })
            
            return {
                "date": date.strftime("%Y-%m-%d"),
                "leads_generated": len(daily_leads),
                "conversation_sessions": len(daily_sessions),
                "transcript_events": daily_events_count,
                "sessions_with_leads": sum(1 for s in daily_sessions if s.get("lead_generated")),
                "lead_details": daily_leads,
                "session_details": daily_sessions
            }
            
        except Exception as e:
            logging.error(f"Error generating daily report: {e}")
            return {}
    
    @staticmethod
    def generate_weekly_summary() -> Dict[str, Any]:
        """Generate weekly summary report"""
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            lead_stats = LeadQueries.get_leads_stats()
            conversation_stats = ConversationQueries.get_conversation_stats()
            transcript_stats = TranscriptQueries.get_transcript_stats()
            
            recent_leads = LeadQueries.get_recent_leads(days=7)
            recent_sessions = ConversationQueries.get_recent_sessions(days=7)
            
            return {
                "period": "Last 7 days",
                "summary": {
                    "total_leads": len(recent_leads),
                    "total_sessions": len(recent_sessions),
                    "lead_conversion_rate": conversation_stats.get("lead_conversion_rate", 0),
                    "average_session_duration_minutes": conversation_stats.get("average_duration_seconds", 0) / 60
                },
                "detailed_stats": {
                    "leads": lead_stats,
                    "conversations": conversation_stats,
                    "transcripts": transcript_stats
                }
            }
            
        except Exception as e:
            logging.error(f"Error generating weekly summary: {e}")
            return {}

# Export functions for easy importing
def get_lead_stats():
    """Convenience function to get lead statistics"""
    return LeadQueries.get_leads_stats()

def get_recent_leads(days: int = 30):
    """Convenience function to get recent leads"""
    return LeadQueries.get_recent_leads(days)

def get_conversation_stats():
    """Convenience function to get conversation statistics"""
    return ConversationQueries.get_conversation_stats()

def search_conversations(query: str):
    """Convenience function to search across all conversation data"""
    transcript_results = TranscriptQueries.search_transcript_content(query)
    lead_results = LeadQueries.search_leads(query)
    
    return {
        "transcript_matches": transcript_results,
        "lead_matches": lead_results
    }

def generate_report(report_type: str = "weekly"):
    """Generate various types of reports"""
    if report_type == "daily":
        return ReportGenerator.generate_daily_report()
    elif report_type == "weekly":
        return ReportGenerator.generate_weekly_summary()
    else:
        return {"error": f"Unknown report type: {report_type}"}