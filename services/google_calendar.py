# -*- coding: utf-8 -*-
"""
services/google_calendar.py — Google Calendar 事件建立 / 讀取
僅限工作帳號（meeting context）
"""
from datetime import datetime, timedelta
from typing import Optional
from googleapiclient.errors import HttpError

from config.settings import ACCOUNTS
from services.google_auth import get_calendar_service


def list_calendars(account: str = "work") -> list:
    """列出帳號下所有可見行事曆（含他人分享給你的）"""
    svc = get_calendar_service(account)
    try:
        result = svc.calendarList().list().execute()
        return result.get("items", [])
    except HttpError:
        return []


def list_events_from_calendars(
    calendar_ids: list,
    start_dt: datetime,
    end_dt: datetime,
    account: str = "work",
) -> list:
    """從多個行事曆讀取指定時間範圍的事件"""
    svc = get_calendar_service(account)
    all_events = []
    for cal_id in calendar_ids:
        try:
            result = svc.events().list(
                calendarId=cal_id,
                timeMin=start_dt.isoformat() + "Z",
                timeMax=end_dt.isoformat() + "Z",
                maxResults=250,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            items = result.get("items", [])
            for item in items:
                item["_calendarId"] = cal_id
            all_events.extend(items)
        except HttpError:
            pass
    all_events.sort(key=lambda e: e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")))
    return all_events


def create_meeting_event(
    title: str,
    date_str: str,           # "YYYY-MM-DD"
    start_time: str = "09:00",
    duration_hours: int = 1,
    attendees: Optional[list] = None,
    description: str = "",
    account: str = "work",
) -> dict:
    """
    在 Google Calendar 建立會議事件。
    回傳含 htmlLink 的事件物件。
    """
    svc = get_calendar_service(account)
    cal_id = ACCOUNTS[account]["calendar_id"]

    start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(hours=duration_hours)

    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Taipei"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Asia/Taipei"},
    }

    if attendees:
        event_body["attendees"] = [{"email": e} for e in attendees if e]

    event = svc.events().insert(calendarId=cal_id, body=event_body).execute()
    return event


def list_upcoming_events(days: int = 14, account: str = "work") -> list:
    """列出未來 N 天的行事曆事件"""
    svc = get_calendar_service(account)
    cal_id = ACCOUNTS[account]["calendar_id"]

    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

    try:
        result = svc.events().list(
            calendarId=cal_id,
            timeMin=now,
            timeMax=end,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return result.get("items", [])
    except HttpError:
        return []


def create_action_item_reminder(
    task: str,
    owner: str,
    deadline: str,           # "YYYY-MM-DD"
    account: str = "work",
) -> dict:
    """為會議追蹤事項建立全天提醒事件"""
    svc = get_calendar_service(account)
    cal_id = ACCOUNTS[account]["calendar_id"]

    event_body = {
        "summary": f"📌 [{owner}] {task}",
        "start": {"date": deadline},
        "end":   {"date": deadline},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "email", "minutes": 1440}],
        },
    }
    return svc.events().insert(calendarId=cal_id, body=event_body).execute()
