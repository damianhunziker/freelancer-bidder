import mysql.connector
from mysql.connector import Error
import sys
from typing import List, Tuple
from mysql_config import MYSQL_CONFIG

def connect_db():
    """Connect to the MySQL database."""
    try:
        return mysql.connector.connect(**MYSQL_CONFIG)
    except Error as e:
        print(f"❌ Error connecting to MySQL database: {e}")
        return None

def show_top_domains(limit: int = 20):
    """Show top domains by mentions."""
    connection = connect_db()
    if not connection:
        return
        
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT domain, fl_mentions_count, fl_message_count, fl_thread_count,
               skype_mentions_count, skype_message_count, skype_thread_count,
               (fl_mentions_count + skype_mentions_count) as total_mentions,
               is_online
        FROM messages_raw_domains 
        WHERE fl_mentions_count > 0 OR skype_mentions_count > 0
        ORDER BY total_mentions DESC 
        LIMIT %s
    """, (limit,))
    
    print(f"🏆 TOP {limit} DOMAINS BY TOTAL MENTIONS:")
    print("=" * 100)
    print(f"{'Status':6} | {'Domain':30} | {'FL Men':6} | {'FL Msg':6} | {'FL Thr':6} | {'SKY Men':7} | {'SKY Msg':7} | {'SKY Conv':8} | {'Total':5}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        domain, fl_men, fl_msg, fl_thr, sky_men, sky_msg, sky_conv, total_men, is_online = row
        status = "🟢 ON" if is_online else "🔴 OFF"
        print(f"{status:6} | {domain[:30]:30} | {fl_men:6} | {fl_msg:6} | {fl_thr:6} | {sky_men:7} | {sky_msg:7} | {sky_conv:8} | {total_men:5}")
    
    cursor.close()
    connection.close()

def show_online_domains():
    """Show only online domains."""
    connection = connect_db()
    if not connection:
        return
        
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT domain, fl_mentions_count, skype_mentions_count,
               (fl_mentions_count + skype_mentions_count) as total_mentions
        FROM messages_raw_domains 
        WHERE is_online = 1 AND (fl_mentions_count > 0 OR skype_mentions_count > 0)
        ORDER BY total_mentions DESC
    """)
    
    print("🟢 ONLINE DOMAINS:")
    print("=" * 80)
    print(f"{'Domain':50} | {'FL':4} | {'SKY':4} | {'Total':5}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        domain, fl_men, sky_men, total = row
        print(f"🟢 {domain[:50]:50} | {fl_men:4} | {sky_men:4} | {total:5}")
    
    cursor.close()
    connection.close()

def show_offline_domains():
    """Show only offline domains."""
    connection = connect_db()
    if not connection:
        return
        
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT domain, fl_mentions_count, skype_mentions_count,
               (fl_mentions_count + skype_mentions_count) as total_mentions
        FROM messages_raw_domains 
        WHERE is_online = 0 AND (fl_mentions_count > 0 OR skype_mentions_count > 0)
        ORDER BY total_mentions DESC
    """)
    
    print("🔴 OFFLINE DOMAINS:")
    print("=" * 80)
    print(f"{'Domain':50} | {'FL':4} | {'SKY':4} | {'Total':5}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        domain, fl_men, sky_men, total = row
        print(f"🔴 {domain[:50]:50} | {fl_men:4} | {sky_men:4} | {total:5}")
    
    cursor.close()
    connection.close()

def search_domain(search_term: str):
    """Search for domains containing the search term."""
    connection = connect_db()
    if not connection:
        return
        
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT domain, fl_mentions_count, skype_mentions_count,
               (fl_mentions_count + skype_mentions_count) as total_mentions,
               is_online
        FROM messages_raw_domains 
        WHERE domain LIKE %s AND (fl_mentions_count > 0 OR skype_mentions_count > 0)
        ORDER BY total_mentions DESC
    """, (f"%{search_term}%",))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"❌ No domains found containing '{search_term}'")
        cursor.close()
        connection.close()
        return
    
    print(f"🔍 DOMAINS CONTAINING '{search_term}' ({len(results)} found):")
    print("=" * 80)
    print(f"{'Status':6} | {'Domain':40} | {'FL':4} | {'SKY':4} | {'Total':5}")
    print("-" * 80)
    
    for row in results:
        domain, fl_men, sky_men, total, is_online = row
        status = "🟢" if is_online else "🔴"
        print(f"{status:6} | {domain[:40]:40} | {fl_men:4} | {sky_men:4} | {total:5}")
    
    cursor.close()
    connection.close()

def show_domain_details(domain: str):
    """Show detailed information about a specific domain."""
    connection = connect_db()
    if not connection:
        return
        
    cursor = connection.cursor()
    
    # Get domain info
    cursor.execute("""
        SELECT * FROM messages_raw_domains WHERE domain = %s
    """, (domain,))
    
    domain_info = cursor.fetchone()
    if not domain_info:
        print(f"❌ Domain '{domain}' not found")
        cursor.close()
        connection.close()
        return
    
    # Unpack domain info
    (id, domain_name, is_online, fl_mentions_count, fl_message_count, fl_thread_count,
     skype_mentions_count, skype_message_count, skype_thread_count,
     first_seen, last_seen, last_checked, created_at, updated_at) = domain_info
    
    total_mentions = fl_mentions_count + skype_mentions_count
    total_messages = fl_message_count + skype_message_count
    total_threads = fl_thread_count + skype_thread_count
    
    print(f"📋 DOMAIN DETAILS: {domain_name}")
    print("=" * 60)
    print(f"Status:        {'🟢 ONLINE' if is_online else '🔴 OFFLINE'}")
    print(f"")
    print(f"FREELANCER DATA:")
    print(f"  Mentions:    {fl_mentions_count}")
    print(f"  Messages:    {fl_message_count}")
    print(f"  Threads:     {fl_thread_count}")
    print(f"")
    print(f"SKYPE DATA:")
    print(f"  Mentions:    {skype_mentions_count}")
    print(f"  Messages:    {skype_message_count}")
    print(f"  Conversations: {skype_thread_count}")
    print(f"")
    print(f"TOTALS:")
    print(f"  Mentions:    {total_mentions}")
    print(f"  Messages:    {total_messages}")
    print(f"  Threads/Conv: {total_threads}")
    print(f"")
    print(f"First seen:    {first_seen or 'Unknown'}")
    print(f"Last seen:     {last_seen or 'Unknown'}")
    print(f"Last checked:  {last_checked or 'Unknown'}")
    
    # Get FL mentions
    cursor.execute("""
        SELECT message_id, thread_id, from_user, mention_context, time_created
        FROM fl_domain_mentions 
        WHERE domain_id = %s
        ORDER BY time_created DESC
        LIMIT 5
    """, (id,))
    
    fl_mentions = cursor.fetchall()
    if fl_mentions:
        print(f"\n📝 RECENT FL MENTIONS (showing latest 5 of {fl_mentions_count}):")
        print("-" * 60)
        for mention in fl_mentions:
            msg_id, thread_id, user, context, time_created = mention
            context_preview = (context[:50] + "...") if len(context) > 50 else context
            print(f"👤 {user:15} | 📅 {time_created or 'Unknown':19} | 💬 {context_preview}")
    
    # Get Skype mentions
    cursor.execute("""
        SELECT message_id, conversation_id, from_user, mention_context, time_created
        FROM skype_domain_mentions 
        WHERE domain_id = %s
        ORDER BY time_created DESC  
        LIMIT 5
    """, (id,))
    
    skype_mentions = cursor.fetchall()
    if skype_mentions:
        print(f"\n📝 RECENT SKYPE MENTIONS (showing latest 5 of {skype_mentions_count}):")
        print("-" * 60)
        for mention in skype_mentions:
            msg_id, conv_id, user, context, time_created = mention
            context_preview = (context[:50] + "...") if len(context) > 50 else context
            print(f"👤 {user:15} | 📅 {time_created or 'Unknown':19} | 💬 {context_preview}")
    
    cursor.close()
    connection.close()

def show_statistics():
    """Show database statistics."""
    connection = connect_db()
    if not connection:
        return
        
    cursor = connection.cursor()
    
    print("📊 DATABASE STATISTICS:")
    print("=" * 50)
    
    # Total counts
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
    
    cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM fl_domain_mentions")
    unique_fl_threads = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT message_id) FROM fl_domain_mentions")
    unique_fl_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT conversation_id) FROM skype_domain_mentions")
    unique_skype_conversations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT message_id) FROM skype_domain_mentions")
    unique_skype_messages = cursor.fetchone()[0]
    
    offline_count = total_domains - online_count
    total_mentions = total_fl_mentions + total_skype_mentions
    
    print(f"Total domains:        {total_domains:4d}")
    print(f"🟢 Online:            {online_count:4d} ({online_count/total_domains*100:.1f}%)")
    print(f"🔴 Offline:           {offline_count:4d} ({offline_count/total_domains*100:.1f}%)")
    print(f"Total mentions:       {total_mentions:4d}")
    print(f"")
    print(f"📱 FREELANCER DATA:")
    print(f"Domains with FL:      {domains_with_fl:4d}")
    print(f"FL mentions:          {total_fl_mentions:4d}")
    print(f"FL unique threads:    {unique_fl_threads:4d}")
    print(f"FL unique messages:   {unique_fl_messages:4d}")
    print(f"")
    print(f"💬 SKYPE DATA:")
    print(f"Domains with Skype:   {domains_with_skype:4d}")
    print(f"Skype mentions:       {total_skype_mentions:4d}")
    print(f"Skype conversations:  {unique_skype_conversations:4d}")
    print(f"Skype unique msgs:    {unique_skype_messages:4d}")
    
    cursor.close()
    connection.close()

def show_help():
    """Show available commands."""
    print("🔧 DOMAIN DATABASE QUERY TOOL (MySQL)")
    print("=" * 40)
    print("Available commands:")
    print("  python query_domains_db.py top [N]       - Show top N domains (default: 20)")
    print("  python query_domains_db.py online        - Show online domains only")
    print("  python query_domains_db.py offline       - Show offline domains only")
    print("  python query_domains_db.py search TERM   - Search domains containing TERM")
    print("  python query_domains_db.py details DOMAIN - Show detailed info for DOMAIN")
    print("  python query_domains_db.py stats         - Show database statistics")
    print("  python query_domains_db.py help          - Show this help")

def main():
    """Main query function."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "top":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            show_top_domains(limit)
        
        elif command == "online":
            show_online_domains()
        
        elif command == "offline":
            show_offline_domains()
        
        elif command == "search":
            if len(sys.argv) < 3:
                print("❌ Please provide a search term")
                return
            search_term = sys.argv[2]
            search_domain(search_term)
        
        elif command == "details":
            if len(sys.argv) < 3:
                print("❌ Please provide a domain name")
                return
            domain = sys.argv[2]
            show_domain_details(domain)
        
        elif command == "stats":
            show_statistics()
        
        elif command == "help":
            show_help()
        
        else:
            print(f"❌ Unknown command: {command}")
            show_help()
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 