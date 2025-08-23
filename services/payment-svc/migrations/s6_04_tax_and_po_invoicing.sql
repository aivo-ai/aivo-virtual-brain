"""
Database schema updates for S6-04 Tax/VAT + District PO Invoicing
SQL migrations to support tax profiles and PO invoice management
"""

# Tax Profile table for customer tax information
CREATE_TAX_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS tax_profiles (
    tenant_id VARCHAR(255) PRIMARY KEY,
    tax_id VARCHAR(50),
    tax_id_type VARCHAR(20),
    tax_exempt BOOLEAN DEFAULT FALSE,
    exemption_certificate VARCHAR(100),
    billing_address_line1 VARCHAR(255) NOT NULL,
    billing_address_line2 VARCHAR(255),
    billing_address_city VARCHAR(100) NOT NULL,
    billing_address_state VARCHAR(50),
    billing_address_postal_code VARCHAR(20) NOT NULL,
    billing_address_country VARCHAR(2) NOT NULL DEFAULT 'US',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_tax_profiles_tenant_id (tenant_id),
    INDEX idx_tax_profiles_tax_id (tax_id),
    INDEX idx_tax_profiles_country (billing_address_country)
);
"""

# PO Invoices table for district invoicing
CREATE_PO_INVOICES_TABLE = """
CREATE TABLE IF NOT EXISTS po_invoices (
    invoice_id VARCHAR(36) PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    po_number VARCHAR(100),
    status ENUM('draft', 'sent', 'pending', 'paid', 'overdue', 'cancelled') DEFAULT 'draft',
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    payment_terms ENUM('net_15', 'net_30', 'net_60', 'net_90') DEFAULT 'net_30',
    
    -- Financial totals
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    tax_total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_payments DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    remaining_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    
    -- Billing contact information
    billing_contact_name VARCHAR(255) NOT NULL,
    billing_contact_email VARCHAR(255) NOT NULL,
    billing_contact_phone VARCHAR(50),
    billing_contact_title VARCHAR(100),
    
    -- Billing address
    billing_address_line1 VARCHAR(255) NOT NULL,
    billing_address_line2 VARCHAR(255),
    billing_address_city VARCHAR(100) NOT NULL,
    billing_address_state VARCHAR(50),
    billing_address_postal_code VARCHAR(20) NOT NULL,
    billing_address_country VARCHAR(2) NOT NULL DEFAULT 'US',
    
    -- Additional fields
    notes TEXT,
    stripe_invoice_id VARCHAR(100),
    pdf_url VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_po_invoices_tenant_id (tenant_id),
    INDEX idx_po_invoices_status (status),
    INDEX idx_po_invoices_due_date (due_date),
    INDEX idx_po_invoices_po_number (po_number),
    INDEX idx_po_invoices_issue_date (issue_date),
    INDEX idx_po_invoices_remaining_balance (remaining_balance)
);
"""

# Invoice line items table
CREATE_INVOICE_LINE_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS invoice_line_items (
    line_item_id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) NOT NULL,
    description TEXT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    tax_rate DECIMAL(5,4),
    tax_amount DECIMAL(10,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (invoice_id) REFERENCES po_invoices(invoice_id) ON DELETE CASCADE,
    INDEX idx_line_items_invoice_id (invoice_id)
);
"""

# Invoice payments table
CREATE_INVOICE_PAYMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS invoice_payments (
    payment_id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) NOT NULL,
    payment_amount DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method ENUM('check', 'wire_transfer', 'ach', 'credit_card', 'cash') NOT NULL,
    reference_number VARCHAR(100),
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (invoice_id) REFERENCES po_invoices(invoice_id) ON DELETE CASCADE,
    INDEX idx_payments_invoice_id (invoice_id),
    INDEX idx_payments_payment_date (payment_date),
    INDEX idx_payments_payment_method (payment_method)
);
"""

# Dunning reminders table for tracking overdue notices
CREATE_DUNNING_REMINDERS_TABLE = """
CREATE TABLE IF NOT EXISTS dunning_reminders (
    reminder_id VARCHAR(36) PRIMARY KEY,
    invoice_id VARCHAR(36) NOT NULL,
    reminder_type ENUM('gentle', 'firm', 'final', 'legal') NOT NULL,
    sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_to_email VARCHAR(255) NOT NULL,
    custom_message TEXT,
    
    FOREIGN KEY (invoice_id) REFERENCES po_invoices(invoice_id) ON DELETE CASCADE,
    INDEX idx_dunning_invoice_id (invoice_id),
    INDEX idx_dunning_sent_date (sent_date),
    INDEX idx_dunning_type (reminder_type)
);
"""

# Tax calculation cache for performance
CREATE_TAX_CALCULATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS tax_calculations (
    calculation_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(255),
    calculation_hash VARCHAR(64) NOT NULL,
    stripe_calculation_id VARCHAR(100),
    subtotal DECIMAL(10,2) NOT NULL,
    total_tax DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    tax_breakdown JSON,
    expires_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_tax_calc_tenant_id (tenant_id),
    INDEX idx_tax_calc_hash (calculation_hash),
    INDEX idx_tax_calc_expires (expires_at)
);
"""

# Update triggers for automatic timestamp updates
CREATE_UPDATE_TRIGGERS = """
-- Tax profiles update trigger
CREATE TRIGGER update_tax_profiles_timestamp 
    BEFORE UPDATE ON tax_profiles 
    FOR EACH ROW 
    SET NEW.updated_at = CURRENT_TIMESTAMP;

-- PO invoices update trigger  
CREATE TRIGGER update_po_invoices_timestamp 
    BEFORE UPDATE ON po_invoices 
    FOR EACH ROW 
    SET NEW.updated_at = CURRENT_TIMESTAMP;
"""

# Views for common queries
CREATE_VIEWS = """
-- Overdue invoices view
CREATE VIEW overdue_invoices AS
SELECT 
    invoice_id,
    invoice_number,
    tenant_id,
    po_number,
    issue_date,
    due_date,
    total,
    remaining_balance,
    billing_contact_name,
    billing_contact_email,
    DATEDIFF(CURDATE(), due_date) as days_overdue
FROM po_invoices 
WHERE status IN ('sent', 'pending') 
  AND due_date < CURDATE() 
  AND remaining_balance > 0;

-- Monthly revenue summary view
CREATE VIEW monthly_revenue_summary AS
SELECT 
    DATE_FORMAT(issue_date, '%Y-%m') as month_year,
    COUNT(*) as invoice_count,
    SUM(subtotal) as total_subtotal,
    SUM(tax_total) as total_tax,
    SUM(total) as total_revenue,
    SUM(total_payments) as total_collected,
    SUM(remaining_balance) as total_outstanding
FROM po_invoices 
WHERE status != 'cancelled'
GROUP BY DATE_FORMAT(issue_date, '%Y-%m')
ORDER BY month_year DESC;

-- Payment method summary view
CREATE VIEW payment_method_summary AS
SELECT 
    payment_method,
    COUNT(*) as payment_count,
    SUM(payment_amount) as total_amount,
    AVG(payment_amount) as avg_amount
FROM invoice_payments 
GROUP BY payment_method
ORDER BY total_amount DESC;
"""

# Sample data for testing
SAMPLE_DATA = """
-- Sample tax profile
INSERT INTO tax_profiles (
    tenant_id, 
    tax_id, 
    tax_id_type, 
    tax_exempt,
    billing_address_line1,
    billing_address_city,
    billing_address_state,
    billing_address_postal_code,
    billing_address_country
) VALUES (
    'district_123',
    '12-3456789',
    'us_ein',
    TRUE,
    '123 School District Blvd',
    'Education City',
    'CA',
    '94105',
    'US'
);

-- Sample PO invoice
INSERT INTO po_invoices (
    invoice_id,
    invoice_number,
    tenant_id,
    po_number,
    issue_date,
    due_date,
    payment_terms,
    subtotal,
    tax_total,
    total,
    remaining_balance,
    billing_contact_name,
    billing_contact_email,
    billing_contact_phone,
    billing_contact_title,
    billing_address_line1,
    billing_address_city,
    billing_address_state,
    billing_address_postal_code,
    billing_address_country,
    notes
) VALUES (
    'inv_123456789',
    'PO-2025-001',
    'district_123',
    'PO-DIST-2025-001',
    CURDATE(),
    DATE_ADD(CURDATE(), INTERVAL 30 DAY),
    'net_30',
    5000.00,
    437.50,
    5437.50,
    5437.50,
    'John Smith',
    'billing@district.edu',
    '(555) 123-4567',
    'Finance Director',
    '123 School District Blvd',
    'Education City',
    'CA',
    '94105',
    'US',
    'Annual subscription for 2025-2026 school year'
);

-- Sample line item
INSERT INTO invoice_line_items (
    line_item_id,
    invoice_id,
    description,
    quantity,
    unit_price,
    total_price,
    tax_rate,
    tax_amount
) VALUES (
    'li_123456789',
    'inv_123456789',
    'AIVO Platform Subscription - 100 students',
    1,
    5000.00,
    5000.00,
    0.0875,
    437.50
);
"""

# All migration scripts
ALL_MIGRATIONS = [
    CREATE_TAX_PROFILES_TABLE,
    CREATE_PO_INVOICES_TABLE,
    CREATE_INVOICE_LINE_ITEMS_TABLE,
    CREATE_INVOICE_PAYMENTS_TABLE,
    CREATE_DUNNING_REMINDERS_TABLE,
    CREATE_TAX_CALCULATIONS_TABLE,
    CREATE_UPDATE_TRIGGERS,
    CREATE_VIEWS,
    SAMPLE_DATA
]

if __name__ == "__main__":
    print("S6-04 Database Schema for Tax/VAT + District PO Invoicing")
    print("=" * 60)
    
    for i, migration in enumerate(ALL_MIGRATIONS, 1):
        print(f"\n-- Migration {i} --")
        print(migration)
        print("\n" + "=" * 60)
