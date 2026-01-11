#!/usr/bin/env python3
"""
MyBB User Extractor - Split Date & Time
Extracts username, email, created date, created time, last IP (decimal), password hash
from MyBB SQL dump (INSERT INTO mybb_users VALUES ...)

Usage:
    python extract_mybb_users.py dump.sql                # print to console
    python extract_mybb_users.py dump.sql users.csv      # save to CSV
"""

import re
import sys
import time
import csv
from pathlib import Path
from typing import List, Optional, Tuple


def parse_values_line(line: str) -> Optional[List[str]]:
    """Extract and split fields from VALUES(...); respecting quoted commas"""
    match = re.search(r'VALUES\s*\((.*)\);?\s*$', line, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    values_str = match.group(1)
    fields = []
    current = ''
    in_quote = False

    for char in values_str:
        if char == "'":
            in_quote = not in_quote
        if char == ',' and not in_quote:
            fields.append(current.strip())
            current = ''
        else:
            current += char

    if current:
        fields.append(current.strip())

    # Remove outer single quotes if present
    fields = [
        f[1:-1] if f.startswith("'") and f.endswith("'") else f
        for f in fields
    ]

    return fields


def process_user(fields: List[str]) -> Tuple[Optional[dict], str]:
    """Extract required fields + convert IP & split date/time"""
    try:
        username = fields[1]
        email    = fields[5]
        regdate  = fields[15]
        lastip   = fields[64]
        pwhash   = fields[2]
    except IndexError:
        return None, "Not enough fields"

    # Split human readable date/time
    created_date = "(invalid)"
    created_time = "(invalid)"
    try:
        ts = int(float(regdate))
        dt = time.localtime(ts)
        created_date = time.strftime('%Y-%m-%d', dt)
        created_time = time.strftime('%H:%M:%S', dt)
    except (ValueError, TypeError):
        pass

    # Convert hex IP to decimal
    ip_final = lastip
    if lastip.lower().startswith('0x'):
        try:
            hex_ip = lastip[2:]
            ip_final = '.'.join(
                str(int(hex_ip[i:i+2], 16)) for i in range(0, len(hex_ip), 2)
            )
        except (ValueError, IndexError):
            ip_final = f"(bad hex: {lastip})"

    return {
        'username': username,
        'email': email,
        'created_date': created_date,
        'created_time': created_time,
        'last_ip': ip_final,
        'password_hash': pwhash
    }, None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not input_file.is_file():
        print(f"Error: File not found: {input_file}", file=sys.stderr)
        return 1

    print(f"Input file: {input_file}")
    print("Processing... (this may take a while depending on file size)\n")

    processed = 0
    valid_users = 0

    csv_file = None
    csv_writer = None

    if output_file:
        print(f"Writing results to: {output_file}")
        csv_file = open(output_file, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        csv_writer.writerow([
            "Username",
            "Email",
            "Created_Date",
            "Created_Time",
            "Last_IP",
            "Password_Hash"
        ])
    else:
        print("No output file specified → printing to console\n")

    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or '@' not in line:
                continue

            fields = parse_values_line(line)
            if not fields or len(fields) <= 64:
                continue

            user_data, error = process_user(fields)
            if error:
                continue

            valid_users += 1

            if csv_writer:
                csv_writer.writerow([
                    user_data['username'],
                    user_data['email'],
                    user_data['created_date'],
                    user_data['created_time'],
                    user_data['last_ip'],
                    user_data['password_hash']
                ])
            else:
                print(f"{'-'*70}")
                print(f"Username      : {user_data['username']}")
                print(f"Email         : {user_data['email']}")
                print(f"Created Date  : {user_data['created_date']}")
                print(f"Created Time  : {user_data['created_time']}")
                print(f"Last IP       : {user_data['last_ip']}")
                print(f"Password Hash : {user_data['password_hash']}")

            processed += 1
            if processed % 500 == 0 and not csv_writer:
                print(f"\nProcessed {processed} lines... ({valid_users} valid users so far)")

    if csv_file:
        csv_file.close()

    print("\n" + "="*70)
    print("Finished!")
    print(f"Lines processed:     {processed:,}")
    print(f"Valid users found:   {valid_users:,}")
    
    if output_file:
        print(f"Results saved to:    {output_file}")
    else:
        print("Results printed above (no output file specified)")


if __name__ == "__main__":
    sys.exit(main() or 0)
