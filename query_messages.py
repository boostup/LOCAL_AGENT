#!/usr/bin/env python3
"""Utility to query logged Telegram messages from the SQLite database."""
import sqlite3
import sys
import os
from pathlib import Path

db_path = Path(os.environ.get("LOCAL_AI_DB_PATH", "data/agent.sqlite"))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Query Telegram message logs")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Number of messages to show")
    parser.add_argument("-u", "--user", type=str, help="Filter by username")
    parser.add_argument("-t", "--text", type=str, help="Filter by text (partial match)")
    args = parser.parse_args()

    if not db_path.exists():
        print("Database not found. The bot has not logged any messages yet.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM telegram_messages"
    conditions = []
    params = []

    if args.user:
        conditions.append("username = ?")
        params.append(args.user)
    if args.text:
        conditions.append("text LIKE ?")
        params.append(f"%{args.text}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(args.limit)

    for row in conn.execute(query, params):
        print(f"[{row['id']}] {row['username'] or row['user_id']} @ {row['created_at']}")
        print(f"  Text: {row['text']}")
        resp = row['skill_response'] or "(no response)"
        print(f"  Response: {resp[:100]}...")
        print()

if __name__ == "__main__":
    main()