# Cloudflare WAF and Edge Security Configuration for AIVO Platform
terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

# Variables
variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for aivo.dev"
  type        = string
}

variable "cloudflare_api_token" {
  description = "Cloudflare API Token"
  type        = string
  sensitive   = true
}

variable "allowed_countries" {
  description = "List of allowed country codes for sensitive routes"
  type        = list(string)
  default     = ["US", "CA", "GB", "DE", "FR", "AU", "JP", "SG"]
}

variable "blocked_countries" {
  description = "List of blocked country codes"
  type        = list(string)
  default     = ["CN", "RU", "KP", "IR"]
}

# Provider configuration
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Zone settings for enhanced security
resource "cloudflare_zone_settings_override" "aivo_security" {
  zone_id = var.cloudflare_zone_id
  
  settings {
    # Security settings
    security_level         = "medium"
    challenge_ttl         = 1800
    browser_check         = "on"
    hotlink_protection    = "on"
    server_side_exclude   = "on"
    
    # Bot management
    bot_management {
      enable_js             = true
      fight_mode           = true
      optimize_wordpress   = false
      suppress_session_score = false
    }
    
    # DDoS protection
    ddos_protection = "on"
    
    # SSL/TLS settings
    ssl                = "strict"
    tls_1_3           = "on"
    automatic_https_rewrites = "on"
    always_use_https  = "on"
    min_tls_version   = "1.2"
    
    # Performance and caching
    browser_cache_ttl = 14400
    cache_level      = "aggressive"
    
    # Security headers
    security_header {
      enabled = true
    }
  }
}

# WAF Custom Rules for Common Attacks
resource "cloudflare_ruleset" "waf_custom_rules" {
  zone_id     = var.cloudflare_zone_id
  name        = "AIVO WAF Custom Rules"
  description = "Custom WAF rules for AIVO platform protection"
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  # SQL Injection Protection
  rule {
    action = "block"
    description = "Block SQL injection attempts"
    expression = "(http.request.uri.query contains \"union select\") or (http.request.uri.query contains \"drop table\") or (http.request.uri.query contains \"insert into\") or (http.request.uri.query contains \"delete from\") or (http.request.body contains \"union select\") or (http.request.body contains \"' or 1=1\") or (http.request.body contains \"'; drop table\")"
    enabled = true
  }

  # XSS Protection
  rule {
    action = "block"
    description = "Block XSS attempts"
    expression = "(http.request.uri.query contains \"<script\") or (http.request.uri.query contains \"javascript:\") or (http.request.uri.query contains \"onload=\") or (http.request.uri.query contains \"onerror=\") or (http.request.body contains \"<script\") or (http.request.body contains \"javascript:\")"
    enabled = true
  }

  # Command Injection Protection
  rule {
    action = "block"
    description = "Block command injection attempts"
    expression = "(http.request.uri.query contains \"../../../\") or (http.request.uri.query contains \"/etc/passwd\") or (http.request.uri.query contains \"cmd.exe\") or (http.request.uri.query contains \"/bin/bash\") or (http.request.body contains \"../../../\") or (http.request.body contains \"/etc/passwd\")"
    enabled = true
  }

  # Authentication Spray Protection
  rule {
    action = "challenge"
    description = "Challenge rapid authentication attempts"
    expression = "(http.request.uri.path eq \"/api/auth/login\") and (http.request.method eq \"POST\") and (rate(1m) > 10)"
    enabled = true
  }

  # Brute Force Protection for Admin Routes
  rule {
    action = "block"
    description = "Block brute force on admin routes"
    expression = "(http.request.uri.path contains \"/admin\") and (http.request.method eq \"POST\") and (rate(5m) > 20)"
    enabled = true
  }

  # Bot Score Protection
  rule {
    action = "challenge"
    description = "Challenge low bot score requests"
    expression = "(cf.bot_management.score lt 30) and not (cf.bot_management.verified_bot)"
    enabled = true
  }

  # Block Known Bad User Agents
  rule {
    action = "block"
    description = "Block malicious user agents"
    expression = "(http.user_agent contains \"sqlmap\") or (http.user_agent contains \"nikto\") or (http.user_agent contains \"nessus\") or (http.user_agent contains \"openvas\") or (http.user_agent contains \"masscan\") or (http.user_agent contains \"zmap\")"
    enabled = true
  }

  # File Upload Protection
  rule {
    action = "block"
    description = "Block suspicious file uploads"
    expression = "(http.request.uri.path contains \"/upload\") and ((http.request.body contains \".php\") or (http.request.body contains \".jsp\") or (http.request.body contains \".asp\") or (http.request.body contains \".exe\"))"
    enabled = true
  }
}

# Geo-blocking Rules for Sensitive Routes
resource "cloudflare_ruleset" "geo_blocking" {
  zone_id     = var.cloudflare_zone_id
  name        = "AIVO Geo-blocking Rules"
  description = "Geographic access controls for sensitive routes"
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  # Block access from restricted countries to admin routes
  rule {
    action = "block"
    description = "Block admin access from restricted countries"
    expression = "(http.request.uri.path contains \"/admin\") and (ip.geoip.country in {${join(" ", formatlist("\"%s\"", var.blocked_countries))}})"
    enabled = true
  }

  # Block access from restricted countries to auth endpoints
  rule {
    action = "block"
    description = "Block auth access from restricted countries"
    expression = "(http.request.uri.path contains \"/api/auth\") and (ip.geoip.country in {${join(" ", formatlist("\"%s\"", var.blocked_countries))}})"
    enabled = true
  }

  # Challenge access to sensitive inference endpoints from non-allowed countries
  rule {
    action = "challenge"
    description = "Challenge inference access from non-allowed countries"
    expression = "(http.request.uri.path contains \"/api/inference\") and not (ip.geoip.country in {${join(" ", formatlist("\"%s\"", var.allowed_countries))}})"
    enabled = true
  }

  # Block payment endpoints from high-risk countries
  rule {
    action = "block"
    description = "Block payment access from high-risk countries"
    expression = "(http.request.uri.path contains \"/api/payment\") and (ip.geoip.country in {${join(" ", formatlist("\"%s\"", var.blocked_countries))}})"
    enabled = true
  }
}

# Rate Limiting Rules
resource "cloudflare_ruleset" "rate_limiting" {
  zone_id     = var.cloudflare_zone_id
  name        = "AIVO Rate Limiting Rules"
  description = "Rate limiting rules for AIVO platform"
  kind        = "zone"
  phase       = "http_ratelimit"

  # Login endpoint rate limiting
  rule {
    action = "block"
    description = "Rate limit login attempts per IP"
    expression = "(http.request.uri.path eq \"/api/auth/login\")"
    enabled = true
    
    ratelimit {
      characteristics = ["ip.src"]
      period         = 60
      requests_per_period = 5
      mitigation_timeout = 600
    }
  }

  # Generate endpoint rate limiting
  rule {
    action = "block"
    description = "Rate limit inference generation per IP"
    expression = "(http.request.uri.path contains \"/api/inference/generate\")"
    enabled = true
    
    ratelimit {
      characteristics = ["ip.src"]
      period         = 60
      requests_per_period = 10
      mitigation_timeout = 300
    }
  }

  # API general rate limiting
  rule {
    action = "block"
    description = "General API rate limiting per IP"
    expression = "(http.request.uri.path contains \"/api/\")"
    enabled = true
    
    ratelimit {
      characteristics = ["ip.src"]
      period         = 60
      requests_per_period = 100
      mitigation_timeout = 60
    }
  }

  # User-specific rate limiting (using JWT claims)
  rule {
    action = "block"
    description = "Rate limit per authenticated user"
    expression = "(http.request.uri.path contains \"/api/\") and (http.request.headers[\"authorization\"][0] contains \"Bearer\")"
    enabled = true
    
    ratelimit {
      characteristics = ["http.request.headers[\"x-user-id\"][0]"]
      period         = 300
      requests_per_period = 1000
      mitigation_timeout = 300
    }
  }
}

# Page Rules for Enhanced Security
resource "cloudflare_page_rule" "admin_security" {
  zone_id  = var.cloudflare_zone_id
  target   = "admin.aivo.dev/*"
  priority = 1
  status   = "active"

  actions {
    security_level = "high"
    cache_level   = "bypass"
    disable_apps  = true
  }
}

resource "cloudflare_page_rule" "api_security" {
  zone_id  = var.cloudflare_zone_id
  target   = "api.aivo.dev/*"
  priority = 2
  status   = "active"

  actions {
    security_level = "medium"
    cache_level   = "bypass"
    browser_check = "on"
  }
}

# Access Application for Admin Routes
resource "cloudflare_access_application" "admin_access" {
  zone_id          = var.cloudflare_zone_id
  name             = "AIVO Admin Access"
  domain           = "admin.aivo.dev"
  type             = "self_hosted"
  session_duration = "24h"
  
  cors_headers {
    allowed_methods = ["GET", "POST", "PUT", "DELETE"]
    allowed_origins = ["https://aivo.dev", "https://app.aivo.dev"]
    allow_credentials = true
    max_age = 86400
  }
}

# Access Policy for Admin Routes
resource "cloudflare_access_policy" "admin_policy" {
  application_id = cloudflare_access_application.admin_access.id
  zone_id        = var.cloudflare_zone_id
  name           = "AIVO Admin Policy"
  precedence     = 1
  decision       = "allow"

  include {
    email_domain = ["aivo.dev"]
  }
  
  require {
    geo = var.allowed_countries
  }
}

# DNS Records with Security Features
resource "cloudflare_record" "api" {
  zone_id = var.cloudflare_zone_id
  name    = "api"
  value   = "api.aivo.dev"
  type    = "CNAME"
  proxied = true
  comment = "API endpoint with WAF protection"
}

resource "cloudflare_record" "admin" {
  zone_id = var.cloudflare_zone_id
  name    = "admin"
  value   = "admin.aivo.dev"
  type    = "CNAME"
  proxied = true
  comment = "Admin endpoint with Access protection"
}

# Security Analytics and Monitoring
resource "cloudflare_logpush_job" "security_events" {
  zone_id         = var.cloudflare_zone_id
  name            = "AIVO Security Events"
  destination_conf = "s3://aivo-security-logs/cloudflare/?region=us-east-1"
  dataset         = "firewall_events"
  enabled         = true
  frequency       = "high"
  
  output_options {
    field_names = [
      "ClientIP",
      "ClientCountry", 
      "RayID",
      "Datetime",
      "Action",
      "Source",
      "RuleID",
      "Description"
    ]
    output_type = "ndjson"
  }
}

# Outputs
output "zone_id" {
  description = "Cloudflare Zone ID"
  value       = var.cloudflare_zone_id
}

output "waf_rules_count" {
  description = "Number of WAF rules configured"
  value       = length(cloudflare_ruleset.waf_custom_rules.rule)
}

output "rate_limit_rules_count" {
  description = "Number of rate limiting rules configured"
  value       = length(cloudflare_ruleset.rate_limiting.rule)
}
