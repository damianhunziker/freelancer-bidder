-- Create education and education_tags tables for storing education/training data
USE domain_analysis;

-- Drop tables if they exist (in correct order due to foreign keys)
DROP TABLE IF EXISTS `education_tags`;
DROP TABLE IF EXISTS `education`;

-- Create education table for storing training/education data
CREATE TABLE `education` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `institution` varchar(255) DEFAULT NULL,
  `start_date` varchar(50) NOT NULL,
  `end_date` varchar(50) DEFAULT NULL,
  `duration` varchar(100) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `type` enum('course', 'certification', 'workshop', 'seminar', 'degree', 'training') DEFAULT 'course',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_start_date` (`start_date`),
  KEY `idx_institution` (`institution`),
  KEY `idx_type` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Create education_tags assignment table
CREATE TABLE `education_tags` (
  `education_id` int NOT NULL,
  `tag_id` int NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`education_id`, `tag_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `education_tags_ibfk_1` FOREIGN KEY (`education_id`) REFERENCES `education` (`id`) ON DELETE CASCADE,
  CONSTRAINT `education_tags_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tags` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; 