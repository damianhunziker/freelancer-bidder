-- Create tables for domain analysis from messages in MySQL
-- Use database domain_analysis
-- Stores domain information with availability, counts, and references
-- Separate fields for Freelancer (fl_) and Skype (skype_) data

USE domain_analysis;

CREATE TABLE IF NOT EXISTS messages_raw_domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain VARCHAR(255) NOT NULL UNIQUE,
    is_online BOOLEAN NOT NULL DEFAULT 0,
    fl_mentions_count INT NOT NULL DEFAULT 0,
    fl_message_count INT NOT NULL DEFAULT 0,
    fl_thread_count INT NOT NULL DEFAULT 0,
    skype_mentions_count INT NOT NULL DEFAULT 0,
    skype_message_count INT NOT NULL DEFAULT 0,
    skype_thread_count INT NOT NULL DEFAULT 0,
    first_seen DATETIME,
    last_seen DATETIME,
    last_checked DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_domain ON messages_raw_domains(domain);
CREATE INDEX IF NOT EXISTS idx_online ON messages_raw_domains(is_online);
CREATE INDEX IF NOT EXISTS idx_fl_mentions ON messages_raw_domains(fl_mentions_count);
CREATE INDEX IF NOT EXISTS idx_skype_mentions ON messages_raw_domains(skype_mentions_count);

-- Create table for individual domain mentions/references from Freelancer
CREATE TABLE IF NOT EXISTS fl_domain_mentions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain_id INT NOT NULL,
    message_id VARCHAR(50),
    thread_id VARCHAR(50),
    from_user VARCHAR(100),
    mention_context TEXT, -- Preview of the message containing the domain
    time_created DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES messages_raw_domains(id) ON DELETE CASCADE
);

-- Create table for individual domain mentions/references from Skype  
CREATE TABLE IF NOT EXISTS skype_domain_mentions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain_id INT NOT NULL,
    message_id VARCHAR(50),
    conversation_id VARCHAR(50),
    from_user VARCHAR(100),
    mention_context TEXT, -- Preview of the message containing the domain
    time_created DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES messages_raw_domains(id) ON DELETE CASCADE
);

-- Create indexes for fl_domain_mentions
CREATE INDEX IF NOT EXISTS idx_fl_domain_id ON fl_domain_mentions(domain_id);
CREATE INDEX IF NOT EXISTS idx_fl_message_id ON fl_domain_mentions(message_id);
CREATE INDEX IF NOT EXISTS idx_fl_thread_id ON fl_domain_mentions(thread_id);

-- Create indexes for skype_domain_mentions
CREATE INDEX IF NOT EXISTS idx_skype_domain_id ON skype_domain_mentions(domain_id);
CREATE INDEX IF NOT EXISTS idx_skype_message_id ON skype_domain_mentions(message_id);
CREATE INDEX IF NOT EXISTS idx_skype_conversation_id ON skype_domain_mentions(conversation_id);

-- Create view for easy domain overview with combined data
CREATE OR REPLACE VIEW domain_overview AS
SELECT 
    d.domain,
    d.is_online,
    d.fl_mentions_count,
    d.fl_message_count,
    d.fl_thread_count,
    d.skype_mentions_count,
    d.skype_message_count,
    d.skype_thread_count,
    (d.fl_mentions_count + d.skype_mentions_count) as total_mentions,
    (d.fl_message_count + d.skype_message_count) as total_messages,
    (d.fl_thread_count + d.skype_thread_count) as total_threads,
    d.first_seen,
    d.last_seen,
    d.last_checked,
    COUNT(DISTINCT fm.thread_id) as actual_fl_thread_count,
    COUNT(DISTINCT fm.message_id) as actual_fl_message_count,
    COUNT(fm.id) as actual_fl_mentions_count,
    COUNT(DISTINCT sm.conversation_id) as actual_skype_conversation_count,
    COUNT(DISTINCT sm.message_id) as actual_skype_message_count,
    COUNT(sm.id) as actual_skype_mentions_count
FROM messages_raw_domains d
LEFT JOIN fl_domain_mentions fm ON d.id = fm.domain_id
LEFT JOIN skype_domain_mentions sm ON d.id = sm.domain_id
GROUP BY d.id, d.domain
ORDER BY total_mentions DESC; 