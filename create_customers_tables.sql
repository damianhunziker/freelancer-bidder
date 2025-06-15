-- Contacts table (Kontakte)
CREATE TABLE IF NOT EXISTS contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Contact phone numbers table (each contact can have multiple phone numbers)
CREATE TABLE IF NOT EXISTS contact_phone_numbers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contact_id INT NOT NULL,
    phone_number VARCHAR(50) NOT NULL,
    phone_type ENUM('mobile', 'work', 'home', 'fax', 'other') DEFAULT 'mobile',
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);

-- Customers table (modified to reference contacts)
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    primary_contact_id INT,
    email VARCHAR(255),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    tax_id VARCHAR(50),
    website VARCHAR(255),
    notes TEXT,
    status ENUM('active', 'inactive', 'potential') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (primary_contact_id) REFERENCES contacts(id) ON SET NULL
);

-- Add customer_id to projects table
ALTER TABLE projects ADD COLUMN customer_id INT;
ALTER TABLE projects ADD FOREIGN KEY (customer_id) REFERENCES customers(id);

-- Create indexes for better performance
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_name ON contacts(last_name, first_name);
CREATE INDEX idx_contact_phones_contact ON contact_phone_numbers(contact_id);
CREATE INDEX idx_contact_phones_primary ON contact_phone_numbers(is_primary);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_company ON customers(company_name);
CREATE INDEX idx_customers_status ON customers(status);
CREATE INDEX idx_customers_contact ON customers(primary_contact_id);
CREATE INDEX idx_projects_customer ON projects(customer_id); 