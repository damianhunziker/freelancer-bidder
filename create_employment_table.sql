-- Create employment table for storing CV data
USE domain_analysis;

DROP TABLE IF EXISTS `employment`;

CREATE TABLE `employment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `company_name` varchar(255) NOT NULL,
  `position` varchar(255) NOT NULL,
  `start_date` varchar(50) NOT NULL,
  `end_date` varchar(50) DEFAULT NULL,
  `description` text NOT NULL,
  `is_self_employed` boolean NOT NULL DEFAULT FALSE,
  `location` varchar(255) DEFAULT NULL,
  `technologies` text DEFAULT NULL,
  `achievements` text DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_start_date` (`start_date`),
  KEY `idx_company` (`company_name`),
  KEY `idx_self_employed` (`is_self_employed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci; 