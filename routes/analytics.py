from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from dependencies import get_db
import models
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

router = APIRouter()

def get_current_time():
    """Get current time in IST"""
    return datetime.now()  # Assuming the server is already set to the correct timezone

def validate_date_range(start_date: Optional[datetime], end_date: Optional[datetime]) -> tuple:
    """Validate and convert date range to UTC"""
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
    institution_id: Optional[int] = None,
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
        if institution_id:
            base_filters.append(models.User.institution_id == institution_id)
        if user_id:
            base_filters.append(models.FinalRecords.user_id == user_id)

        # Initialize statistics containers
        stats = {
            'hourly_stats': defaultdict(int),
            'verification_stats': {
                'total_attempts': 0,
                'face_success': 0,
                'qr_success': 0,
                'both_success': 0,
                'failures': 0
            },
            'entry_types': defaultdict(int),
            'daily_stats': defaultdict(lambda: {
                'entries': 0,
                'successes': 0,
                'unique_users': set(),
            }),
            'completion_times': [],
            'duration_stats': [],
        }

        # Process records
        records = db.query(models.FinalRecords).filter(*base_filters).order_by(
            models.FinalRecords.entry_date.desc()
        ).all()

        for record in records:
            for log in record.time_logs:
                # Basic time processing
                arrival_time = datetime.fromisoformat(log['arrival'])
                hour = arrival_time.hour
                date_str = arrival_time.date().isoformat()

                # Track entry type
                entry_type = log.get('entry_type', 'normal')
                stats['entry_types'][entry_type] += 1

                # Track hourly distribution
                stats['hourly_stats'][hour] += 1

                # Process verification stats
                stats['verification_stats']['total_attempts'] += 1
                is_success = False

                # Check face verification
                if log.get('face_verified') is True:
                    stats['verification_stats']['face_success'] += 1

                # Check QR verification
                if log.get('qr_verified') is True:
                    stats['verification_stats']['qr_success'] += 1

                # Determine overall success
                if log.get('face_verified') is True and log.get('qr_verified') is True:
                    is_success = True
                    stats['verification_stats']['both_success'] += 1

                # Update success counters
                if is_success:
                    stats['daily_stats'][date_str]['successes'] += 1
                else:
                    stats['verification_stats']['failures'] += 1

                # Update daily statistics
                stats['daily_stats'][date_str]['entries'] += 1
                stats['daily_stats'][date_str]['unique_users'].add(record.user_id)

                # Calculate duration if available
                if log.get('arrival') and log.get('departure'):
                    arrival = datetime.fromisoformat(log['arrival'])
                    departure = datetime.fromisoformat(log['departure'])
                    duration = (departure - arrival).total_seconds() / 60
                    if duration > 0:
                        stats['duration_stats'].append(duration)

        # Calculate derived metrics
        total_entries = stats['verification_stats']['total_attempts']
        total_success = stats['verification_stats']['both_success']

        return {
            "time_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timezone": "Asia/Kolkata (UTC+5:30)"  # Assuming this is the server's timezone
            },
            "traffic_analysis": {
                "peak_hours": [
                    hour for hour, count in stats['hourly_stats'].items()
                    if count >= max(stats['hourly_stats'].values()) * 0.8
                ],
                "hourly_distribution": dict(stats['hourly_stats']),
                "busiest_periods": sorted(
                    [(hour, count) for hour, count in stats['hourly_stats'].items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
            },
            "performance_metrics": {
                "success_rate": round(
                    (total_success / total_entries * 100) if total_entries > 0 else 0, 2
                ),
                "face_verification_rate": round(
                    (stats['verification_stats']['face_success'] / total_entries * 100) if total_entries > 0 else 0, 2
                ),
                "qr_verification_rate": round(
                    (stats['verification_stats']['qr_success'] / total_entries * 100) if total_entries > 0 else 0, 2
                ),
            },
            "entry_statistics": {
                "total_entries": total_entries,
                "entry_types": dict(stats['entry_types']),
                "average_duration_minutes": round(
                    sum(stats['duration_stats']) / len(stats['duration_stats']) if stats['duration_stats'] else 0, 2
                ),
                "daily_patterns": {
                    date: {
                        "total_entries": data['entries'],
                        "successful_entries": data['successes'],
                        "unique_users": len(data['unique_users']),
                        "success_rate": round(
                            (data['successes'] / data['entries'] * 100) if data['entries'] > 0 else 0, 2
                        )
                    }
                    for date, data in stats['daily_stats'].items()
                },
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")
