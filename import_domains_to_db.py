import mysql.connector
from mysql.connector import Error
import json
import os
import glob
from datetime import datetime
from typing import List, Dict, Any
from mysql_config import MYSQL_CONFIG

# Output directory
FL_MESSAGES_DIR = "fl_messages"

def create_database():
    """Create the database tables if they don't exist."""
    try:
        with open('create_messages_domains_table.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Connect to MySQL
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = connection.cursor()
        
        # Split SQL script into individual statements (MySQL doesn't support executescript)
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement:
                cursor.execute(statement)
        
        connection.commit()
        cursor.close()
        connection.close()
        print("✅ Database tables created successfully")
        
    except Error as e:
        print(f"❌ Error creating database: {e}")
        raise

def load_latest_domain_data():
    """Load the latest domain findings from JSON files."""
    
    # Find the most recent domain findings file
    domain_files = glob.glob(os.path.join(FL_MESSAGES_DIR, "*_freelancer_domains_found.json"))
    reachability_files = glob.glob(os.path.join(FL_MESSAGES_DIR, "*_freelancer_domain_reachability.json"))
    
    if not domain_files:
        print("❌ No domain findings files found")
        return None, None
    
    # Get the largest files (most comprehensive data)
    latest_domain_file = max(domain_files, key=os.path.getsize)
    latest_reachability_file = max(reachability_files, key=os.path.getsize) if reachability_files else None
    
    print(f"📁 Loading domain data from: {os.path.basename(latest_domain_file)}")
    
    # Load domain findings
    with open(latest_domain_file, 'r', encoding='utf-8') as f:
        domain_findings = json.load(f)
    
    # Load reachability data if available
    reachability_data = {}
    if latest_reachability_file:
        print(f"📁 Loading reachability data from: {os.path.basename(latest_reachability_file)}")
        with open(latest_reachability_file, 'r', encoding='utf-8') as f:
            reachability = json.load(f)
            
            # Create lookup dictionaries
            for domain in reachability.get('online_domains', {}).get('domains', []):
                reachability_data[domain] = True
            for domain in reachability.get('offline_domains', {}).get('domains', []):
                reachability_data[domain] = False
    
    return domain_findings, reachability_data

def analyze_domain_data(domain_findings: List[Dict]) -> Dict[str, Dict]:
    """Analyze domain data to calculate counts and statistics."""
    domain_stats = {}
    
    for finding in domain_findings:
        domain = finding['domain']
        
        if domain not in domain_stats:
            domain_stats[domain] = {
                'mentions_count': 0,
                'message_ids': set(),
                'thread_ids': set(),
                'users': set(),
                'first_seen': None,
                'last_seen': None,
                'mentions': []
            }
        
        stats = domain_stats[domain]
        stats['mentions_count'] += 1
        stats['message_ids'].add(finding['message_id'])
        stats['thread_ids'].add(finding['thread_id'])
        stats['users'].add(finding['from_user'])
        stats['mentions'].append(finding)
        
        # Track first and last seen
        time_created = finding.get('time_created')
        if time_created:
            if stats['first_seen'] is None or time_created < stats['first_seen']:
                stats['first_seen'] = time_created
            if stats['last_seen'] is None or time_created > stats['last_seen']:
                stats['last_seen'] = time_created
    
    # Convert sets to counts
    for domain, stats in domain_stats.items():
        stats['message_count'] = len(stats['message_ids'])
        stats['thread_count'] = len(stats['thread_ids'])
        stats['user_count'] = len(stats['users'])
    
    return domain_stats

def import_to_database(domain_stats: Dict, reachability_data: Dict):
    """Import domain data to the MySQL database."""
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = connection.cursor()
        
        # Clear existing FL data
        cursor.execute("DELETE FROM fl_domain_mentions")
        cursor.execute("UPDATE messages_raw_domains SET fl_mentions_count = 0, fl_message_count = 0, fl_thread_count = 0")
        
        print(f"📊 Importing {len(domain_stats)} domains to database...")
        
        for domain, stats in domain_stats.items():
            # Determine if domain is online
            is_online = reachability_data.get(domain, False)
            
            # Check if domain already exists
            cursor.execute("SELECT id FROM messages_raw_domains WHERE domain = %s", (domain,))
            existing_domain = cursor.fetchone()
            
            if existing_domain:
                domain_id = existing_domain[0]
                # Update existing domain with FL data
                cursor.execute("""
                    UPDATE messages_raw_domains 
                    SET fl_mentions_count = %s, fl_message_count = %s, fl_thread_count = %s,
                        is_online = %s, last_checked = %s, updated_at = NOW()
                    WHERE id = %s
                """, (
                    stats['mentions_count'],
                    stats['message_count'],
                    stats['thread_count'],
                    is_online,
                    datetime.now(),
                    domain_id
                ))
            else:
                # Insert new domain with FL data
                cursor.execute("""
                    INSERT INTO messages_raw_domains 
                    (domain, is_online, fl_mentions_count, fl_message_count, fl_thread_count, 
                     first_seen, last_seen, last_checked)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    domain,
                    is_online,
                    stats['mentions_count'],
                    stats['message_count'],
                    stats['thread_count'],
                    stats['first_seen'],
                    stats['last_seen'],
                    datetime.now()
                ))
                domain_id = cursor.lastrowid
            
            # Insert individual FL mentions
            for mention in stats['mentions']:
                cursor.execute("""
                    INSERT INTO fl_domain_mentions
                    (domain_id, message_id, thread_id, from_user, mention_context, 
                     time_created)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    domain_id,
                    mention['message_id'],
                    mention['thread_id'],
                    mention['from_user'],
                    mention.get('message_preview', ''),
                    mention.get('time_created')
                ))
        
        connection.commit()
        
        # Print statistics
        cursor.execute("SELECT COUNT(*) FROM messages_raw_domains WHERE fl_mentions_count > 0")
        domain_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fl_domain_mentions")
        mention_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages_raw_domains WHERE fl_mentions_count > 0 AND is_online = 1")
        online_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(fl_mentions_count) FROM messages_raw_domains")
        total_fl_mentions = cursor.fetchone()[0] or 0
        
        print(f"✅ Import completed:")
        print(f"   📊 {domain_count} domains with FL data")
        print(f"   💬 {mention_count} FL mentions imported")
        print(f"   📈 {total_fl_mentions} total FL mentions counted")
        print(f"   🟢 {online_count} domains online")
        print(f"   🔴 {domain_count - online_count} domains offline")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"❌ Error importing data: {e}")
        if connection.is_connected():
            connection.rollback()
            cursor.close()
            connection.close()

def show_database_overview():
    """Show overview of imported data."""
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = connection.cursor()
        
        print(f"\n{'='*60}")
        print("DATABASE OVERVIEW")
        print(f"{'='*60}")
        
        # Top domains by total mentions
        cursor.execute("""
            SELECT domain, fl_mentions_count, fl_message_count, fl_thread_count, 
                   skype_mentions_count, skype_message_count, skype_thread_count,
                   (fl_mentions_count + skype_mentions_count) as total_mentions,
                   is_online
            FROM messages_raw_domains 
            WHERE fl_mentions_count > 0 OR skype_mentions_count > 0
            ORDER BY total_mentions DESC 
            LIMIT 10
        """)
        
        print("🏆 TOP 10 DOMAINS BY TOTAL MENTIONS:")
        print("-" * 80)
        print(f"{'Status':6} | {'Domain':25} | {'FL Men':6} | {'FL Msg':6} | {'FL Thr':6} | {'SKY Men':7} | {'SKY Msg':7} | {'SKY Conv':8} | {'Total':5}")
        print("-" * 80)
        
        for row in cursor.fetchall():
            domain, fl_men, fl_msg, fl_thr, sky_men, sky_msg, sky_thr, total_men, is_online = row
            status = "🟢 ON" if is_online else "🔴 OFF"
            print(f"{status:6} | {domain[:25]:25} | {fl_men:6} | {fl_msg:6} | {fl_thr:6} | {sky_men:7} | {sky_msg:7} | {sky_thr:8} | {total_men:5}")
        
        # Summary statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_domains,
                SUM(CASE WHEN is_online = 1 THEN 1 ELSE 0 END) as online_count,
                SUM(fl_mentions_count) as total_fl_mentions,
                SUM(skype_mentions_count) as total_skype_mentions,
                COUNT(CASE WHEN fl_mentions_count > 0 THEN 1 END) as domains_with_fl,
                COUNT(CASE WHEN skype_mentions_count > 0 THEN 1 END) as domains_with_skype
            FROM messages_raw_domains 
            WHERE fl_mentions_count > 0 OR skype_mentions_count > 0
        """)
        
        stats = cursor.fetchone()
        total_domains, online_count, total_fl_mentions, total_skype_mentions, domains_with_fl, domains_with_skype = stats
        offline_count = total_domains - online_count
        
        print(f"\n📊 SUMMARY STATISTICS:")
        print("-" * 50)
        print(f"Total domains:        {total_domains:4d}")
        print(f"🟢 Online:            {online_count:4d} ({online_count/total_domains*100:.1f}%)")
        print(f"🔴 Offline:           {offline_count:4d} ({offline_count/total_domains*100:.1f}%)")
        print(f"")
        print(f"Domains with FL data: {domains_with_fl:4d}")
        print(f"Total FL mentions:    {total_fl_mentions:4d}")
        print(f"")
        print(f"Domains with Skype:   {domains_with_skype:4d}")
        print(f"Total Skype mentions: {total_skype_mentions:4d}")
        
        cursor.close()
        connection.close()
        
    except Error as e:
        print(f"❌ Error showing overview: {e}")

def main():
    """Main import function."""
    print("🚀 Starting domain data import to MySQL database...")
    
    # Create database and tables
    create_database()
    
    # Load data from JSON files
    domain_findings, reachability_data = load_latest_domain_data()
    if not domain_findings:
        return
    
    # Analyze the data
    print("🔍 Analyzing domain data...")
    domain_stats = analyze_domain_data(domain_findings)
    
    # Import to database
    print("💾 Importing to MySQL database...")
    import_to_database(domain_stats, reachability_data)
    
    # Show overview
    show_database_overview()
    
    print(f"\n✅ Import completed successfully!")
    print(f"💡 Data imported to MySQL database: {MYSQL_CONFIG['database']}")

if __name__ == "__main__":
    main() 