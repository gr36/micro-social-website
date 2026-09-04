#!/usr/bin/env python3
"""Checks feed.json before it is published: valid JSON, the shapes the app
expects, and dates the app can parse. Run: python3 editorial/validate.py editorial/feed.json"""
import json, sys
from datetime import datetime

def iso(value, where):
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        fail(f"{where}: '{value}' is not an ISO 8601 date like 2026-09-04T06:00:00Z")

def fail(message):
    print(f"feed.json: {message}")
    sys.exit(1)

def expect(condition, message):
    if not condition:
        fail(message)

def check_list(feed, key, item_check):
    items = feed.get(key)
    if items is None:
        return
    expect(isinstance(items, list), f"'{key}' must be a list")
    for index, item in enumerate(items):
        expect(isinstance(item, dict), f"{key}[{index}] must be an object")
        item_check(item, f"{key}[{index}]")

def person(item, where):
    expect(isinstance(item.get("username"), str) and item["username"], f"{where}: 'username' is required")

def book(item, where):
    expect(isinstance(item.get("title"), str) and item["title"], f"{where}: 'title' is required")
    if "authors" in item:
        expect(isinstance(item["authors"], list), f"{where}: 'authors' must be a list of names")

def event(item, where):
    for key in ("id", "title"):
        expect(isinstance(item.get(key), str) and item[key], f"{where}: '{key}' is required")
    for key in ("starts", "ends"):
        if key in item:
            iso(item[key], f"{where}.{key}")

def pick(item, where):
    expect(isinstance(item.get("title"), str) and item["title"], f"{where}: 'title' is required")

path = sys.argv[1] if len(sys.argv) > 1 else "editorial/feed.json"
try:
    with open(path) as handle:
        feed = json.load(handle)
except json.JSONDecodeError as error:
    fail(f"not valid JSON ({error})")

expect(isinstance(feed, dict), "top level must be an object")
expect(feed.get("version") == 1, "'version' must be 1")
if "updated" in feed:
    iso(feed["updated"], "updated")
check_list(feed, "people", person)
check_list(feed, "books", book)
check_list(feed, "events", event)
def issue(item, where):
    for key in ("id", "title", "date"):
        expect(isinstance(item.get(key), str) and item[key], f"{where}: '{key}' is required")
    iso(item["date"], f"{where}.date")
    check_list(item, "books", book)
    check_list(item, "people", person)
    if item.get("tip") is not None:
        expect(isinstance(item["tip"], dict), f"{where}.tip must be an object")
        event(item["tip"], f"{where}.tip")
    if item.get("activity") is not None:
        for key in ("watching", "playing", "listening"):
            check_list(item["activity"], key, pick)

check_list(feed, "issues", issue)
activity = feed.get("activity")
if activity is not None:
    expect(isinstance(activity, dict), "'activity' must be an object")
    for key in ("watching", "playing", "listening"):
        check_list(activity, key, pick)
    for key in activity:
        expect(key in ("watching", "playing", "listening"), f"activity.{key} is not a section the app knows")
print(f"{path}: ok")
