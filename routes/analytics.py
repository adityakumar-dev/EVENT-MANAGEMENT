from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, and_
from dependencies import get_db
import models
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
import pytz

router = APIRouter()

def get_current_time():
    """Get current time in IST"""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> tuple:
    """Validate and convert date range to IST"""
    if not end_date:
        end_date = get_current_time()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Normalize time ranges
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    return start_date, end_date

@router.get("/analytics")
def get_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    group_name: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        # Initialize date range
        start_date, end_date = validate_date_range(start_date, end_date)

        # Build base query filters
        base_filters = [
            models.FinalRecords.entry_date.between(start_date.date(), end_date.date())
        ]
        
        if group_name:
            base_filters.append(models.User.group_name == group_name)
        if user_id:
            base_filters.append(models.FinalRecords.user_id == user_id)

        # Initialize statistics containers
        stats = {
            'hourly_stats': defaultdict(int),
            'entry_stats': {
                'total_entries': 0,
                'unique_users': set(),
                'total_duration_minutes': 0,
                'completed_visits': 0  # visits with both entry and exit
            },
            'group_stats': defaultdict(lambda: {
                'total_entries': 0,
                'unique_users': set(),
                'total_duration': 0
            }),
            'daily_stats': defaultdict(lambda: {
                'entries': 0,
                'unique_users': set(),
                'total_duration': 0,
                'groups': defaultdict(set)  # group_name -> set of user_ids
            })
        }

        # Join with User table to get group information
        records = db.query(models.FinalRecords, models.User).join(
            models.User,
            models.FinalRecords.user_id == models.User.user_id
        ).filter(*base_filters).all()

        for record, user in records:
            for log in record.time_logs:
                # Process arrival time
                arrival_time = datetime.fromisoformat(log['arrival'])
                date_str = arrival_time.date().isoformat()
                hour = arrival_time.hour

                # Update basic stats
                stats['hourly_stats'][hour] += 1
                stats['entry_stats']['total_entries'] += 1
                stats['entry_stats']['unique_users'].add(record.user_id)

                # Update group stats
                if user.group_name:
                    stats['group_stats'][user.group_name]['total_entries'] += 1
                    stats['group_stats'][user.group_name]['unique_users'].add(record.user_id)

                # Update daily stats
                stats['daily_stats'][date_str]['entries'] += 1
                stats['daily_stats'][date_str]['unique_users'].add(record.user_id)
                if user.group_name:
                    stats['daily_stats'][date_str]['groups'][user.group_name].add(record.user_id)

                # Calculate duration if available
                if log.get('arrival') and log.get('departure'):
                    arrival = datetime.fromisoformat(log['arrival'])
                    departure = datetime.fromisoformat(log['departure'])
                    duration = (departure - arrival).total_seconds() / 60
                    if duration > 0:
                        stats['entry_stats']['total_duration_minutes'] += duration
                        stats['entry_stats']['completed_visits'] += 1
                        if user.group_name:
                            stats['group_stats'][user.group_name]['total_duration'] += duration
                        stats['daily_stats'][date_str]['total_duration'] += duration

        # Calculate averages and prepare response
        total_entries = stats['entry_stats']['total_entries']
        total_duration = stats['entry_stats']['total_duration_minutes']
        completed_visits = stats['entry_stats']['completed_visits']

        return {
            "time_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timezone": "Asia/Kolkata"
            },
            "overall_statistics": {
                "total_entries": total_entries,
                "unique_users": len(stats['entry_stats']['unique_users']),
                "average_duration_minutes": round(total_duration / completed_visits if completed_visits > 0 else 0, 2),
                "completion_rate": round((completed_visits / total_entries * 100) if total_entries > 0 else 0, 2)
            },
            "traffic_analysis": {
                "hourly_distribution": dict(stats['hourly_stats']),
                "peak_hours": [
                    hour for hour, count in stats['hourly_stats'].items()
                    if count >= max(stats['hourly_stats'].values()) * 0.8
                ],
                "busiest_periods": sorted(
                    [(hour, count) for hour, count in stats['hourly_stats'].items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
            },
            "group_analysis": {
                group_name: {
                    "total_entries": data['total_entries'],
                    "unique_users": len(data['unique_users']),
                    "average_duration_minutes": round(
                        data['total_duration'] / data['total_entries'] if data['total_entries'] > 0 else 0, 2
                    )
                }
                for group_name, data in stats['group_stats'].items()
            },
            "daily_patterns": {
                date: {
                    "total_entries": data['entries'],
                    "unique_users": len(data['unique_users']),
                    "average_duration_minutes": round(
                        data['total_duration'] / data['entries'] if data['entries'] > 0 else 0, 2
                    ),
                    "group_distribution": {
                        group: len(users) for group, users in data['groups'].items()
                    }
                }
                for date, data in stats['daily_stats'].items()
            }
        }

    except Exception as e:
        print(f"Analytics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")
