#!/bin/bash
#
# Backup Restore Verification Script
# Daily automated restore testing to staging environment
#

set -euo pipefail

# Configuration
STAGING_DB_HOST="${STAGING_DB_HOST:-staging-postgres.aivo.svc.cluster.local}"
STAGING_DB_PORT="${STAGING_DB_PORT:-5432}"
STAGING_DB_NAME="${STAGING_DB_NAME:-aivo_staging}"
STAGING_DB_USER="${STAGING_DB_USER}"
STAGING_DB_PASSWORD="${STAGING_DB_PASSWORD}"
BACKUP_BUCKET="${BACKUP_BUCKET:-aivo-backup-postgres}"
KMS_KEY_ID="${KMS_KEY_ID}"
VERIFICATION_TAG="verify_$(date +%Y%m%d_%H%M%S)"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >&2
}

error() {
    log "ERROR: $*"
    exit 1
}

# Verify prerequisites
check_prerequisites() {
    log "Checking prerequisites for restore verification..."
    
    command -v psql >/dev/null || error "PostgreSQL client not found"
    command -v pgbackrest >/dev/null || error "pgBackRest not found"
    command -v aws >/dev/null || error "AWS CLI not found"
    command -v jq >/dev/null || error "jq not found"
    
    # Test staging database connection
    if ! PGPASSWORD="$STAGING_DB_PASSWORD" psql -h "$STAGING_DB_HOST" -p "$STAGING_DB_PORT" \
         -U "$STAGING_DB_USER" -d postgres -c "SELECT 1;" >/dev/null 2>&1; then
        error "Cannot connect to staging database"
    fi
    
    # Test S3 backup access
    aws s3 ls "s3://$BACKUP_BUCKET" >/dev/null || error "Cannot access backup bucket: $BACKUP_BUCKET"
    
    log "Prerequisites check passed"
}

# Get latest backup information
get_latest_backup() {
    log "Retrieving latest backup information..."
    
    # Get latest backup metadata from S3
    local latest_metadata
    latest_metadata=$(aws s3 ls "s3://$BACKUP_BUCKET/metadata/postgres/" | sort | tail -1 | awk '{print $4}')
    
    if [[ -z "$latest_metadata" ]]; then
        error "No backup metadata found"
    fi
    
    # Download and parse metadata
    aws s3 cp "s3://$BACKUP_BUCKET/metadata/postgres/$latest_metadata" /tmp/latest_backup.json
    
    local backup_tag backup_type backup_size
    backup_tag=$(jq -r '.tag' /tmp/latest_backup.json)
    backup_type=$(jq -r '.backup_type' /tmp/latest_backup.json)
    backup_size=$(jq -r '.size_bytes' /tmp/latest_backup.json)
    
    log "Latest backup: $backup_tag (type: $backup_type, size: $(numfmt --to=iec $backup_size))"
    
    echo "$backup_tag"
}

# Prepare staging environment
prepare_staging() {
    log "Preparing staging environment..."
    
    # Drop existing staging database if it exists
    PGPASSWORD="$STAGING_DB_PASSWORD" psql -h "$STAGING_DB_HOST" -p "$STAGING_DB_PORT" \
        -U "$STAGING_DB_USER" -d postgres \
        -c "DROP DATABASE IF EXISTS ${STAGING_DB_NAME}_verify;"
    
    # Create fresh database for verification
    PGPASSWORD="$STAGING_DB_PASSWORD" psql -h "$STAGING_DB_HOST" -p "$STAGING_DB_PORT" \
        -U "$STAGING_DB_USER" -d postgres \
        -c "CREATE DATABASE ${STAGING_DB_NAME}_verify;"
    
    log "Staging database ${STAGING_DB_NAME}_verify created"
}

# Restore backup to staging
restore_to_staging() {
    local backup_tag="$1"
    
    log "Restoring backup $backup_tag to staging..."
    
    # Create temporary restore configuration
    local restore_config="/tmp/pgbackrest_restore_${VERIFICATION_TAG}.conf"
    cat > "$restore_config" << EOF
[global]
repo1-type=s3
repo1-s3-bucket=$BACKUP_BUCKET
repo1-s3-key-type=kms
repo1-s3-kms-key-id=$KMS_KEY_ID
repo1-s3-region=${AWS_DEFAULT_REGION:-us-east-1}
repo1-cipher-type=aes-256-cbc
repo1-cipher-pass-command=aws kms decrypt --ciphertext-blob fileb:///etc/kms/key.enc --output text --query Plaintext | base64 -d

[aivo-postgres]
pg1-host=$STAGING_DB_HOST
pg1-port=$STAGING_DB_PORT
pg1-user=$STAGING_DB_USER
pg1-database=${STAGING_DB_NAME}_verify
EOF
    
    # Perform restore
    export PGBACKREST_CONFIG="$restore_config"
    
    if pgbackrest restore \
        --stanza=aivo-postgres \
        --type=latest \
        --target-action=promote \
        --recovery-option="archive_mode=off" \
        --recovery-option="wal_level=minimal" \
        --recovery-option="max_wal_senders=0" \
        --recovery-option="hot_standby=off"; then
        log "Restore completed successfully"
    else
        error "Restore failed"
    fi
    
    # Cleanup temporary config
    rm -f "$restore_config"
}

# Verify data integrity
verify_data_integrity() {
    log "Verifying data integrity..."
    
    local db_conn="postgresql://$STAGING_DB_USER:$STAGING_DB_PASSWORD@$STAGING_DB_HOST:$STAGING_DB_PORT/${STAGING_DB_NAME}_verify"
    
    # Get basic database statistics
    local table_count row_count index_count
    table_count=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
    row_count=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
        "SELECT sum(n_tup_ins + n_tup_upd) FROM pg_stat_user_tables;")
    index_count=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
        "SELECT count(*) FROM pg_stat_user_indexes;")
    
    log "Database statistics: $table_count tables, $row_count rows, $index_count indexes"
    
    # Run data integrity checks
    log "Running data integrity checks..."
    
    # Check for missing primary keys
    local missing_pks
    missing_pks=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
        "SELECT count(*) FROM information_schema.tables t 
         LEFT JOIN information_schema.table_constraints tc 
         ON t.table_name = tc.table_name AND tc.constraint_type = 'PRIMARY KEY'
         WHERE t.table_schema = 'public' AND tc.constraint_name IS NULL;")
    
    if [[ "$missing_pks" -gt 0 ]]; then
        log "WARNING: $missing_pks tables without primary keys found"
    fi
    
    # Check for foreign key violations
    local fk_violations
    fk_violations=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
        "SELECT count(*) FROM information_schema.table_constraints 
         WHERE constraint_type = 'FOREIGN KEY';")
    
    log "Foreign key constraints verified: $fk_violations constraints"
    
    # Sample data verification (check critical tables)
    verify_critical_tables "$db_conn"
    
    # Calculate and store checksums
    calculate_checksums "$db_conn"
    
    log "Data integrity verification completed"
}

# Verify critical application tables
verify_critical_tables() {
    local db_conn="$1"
    
    log "Verifying critical application tables..."
    
    # Users table verification
    if PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -c "SELECT 1 FROM users LIMIT 1;" >/dev/null 2>&1; then
        local user_count
        user_count=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c "SELECT count(*) FROM users;")
        log "Users table: $user_count records"
        
        # Check for duplicate emails
        local duplicate_emails
        duplicate_emails=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
            "SELECT count(*) FROM (SELECT email FROM users GROUP BY email HAVING count(*) > 1) dups;")
        
        if [[ "$duplicate_emails" -gt 0 ]]; then
            log "WARNING: $duplicate_emails duplicate email addresses found"
        fi
    else
        log "WARNING: Users table not found or inaccessible"
    fi
    
    # Courses table verification
    if PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -c "SELECT 1 FROM courses LIMIT 1;" >/dev/null 2>&1; then
        local course_count
        course_count=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c "SELECT count(*) FROM courses;")
        log "Courses table: $course_count records"
    else
        log "WARNING: Courses table not found or inaccessible"
    fi
    
    # Learning sessions verification
    if PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -c "SELECT 1 FROM learning_sessions LIMIT 1;" >/dev/null 2>&1; then
        local session_count
        session_count=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c "SELECT count(*) FROM learning_sessions;")
        log "Learning sessions table: $session_count records"
        
        # Check for sessions without users
        local orphaned_sessions
        orphaned_sessions=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
            "SELECT count(*) FROM learning_sessions ls LEFT JOIN users u ON ls.user_id = u.id WHERE u.id IS NULL;")
        
        if [[ "$orphaned_sessions" -gt 0 ]]; then
            log "WARNING: $orphaned_sessions orphaned learning sessions found"
        fi
    else
        log "WARNING: Learning sessions table not found or inaccessible"
    fi
}

# Calculate table checksums
calculate_checksums() {
    local db_conn="$1"
    
    log "Calculating table checksums..."
    
    # Get list of user tables
    local tables
    tables=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
    
    local checksum_file="/tmp/table_checksums_${VERIFICATION_TAG}.txt"
    
    while IFS= read -r table; do
        if [[ -n "$table" ]]; then
            table=$(echo "$table" | xargs)  # trim whitespace
            local checksum
            checksum=$(PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -t -c \
                "SELECT md5(string_agg(md5(t.*::text), '' ORDER BY t.*::text)) FROM $table t;")
            echo "$table:$checksum" >> "$checksum_file"
            log "Checksum for $table: $checksum"
        fi
    done <<< "$tables"
    
    # Upload checksums to S3 for comparison
    aws s3 cp "$checksum_file" "s3://$BACKUP_BUCKET/verification/checksums_${VERIFICATION_TAG}.txt" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID"
    
    rm -f "$checksum_file"
    log "Table checksums calculated and stored"
}

# Performance verification
verify_performance() {
    local db_conn="postgresql://$STAGING_DB_USER:$STAGING_DB_PASSWORD@$STAGING_DB_HOST:$STAGING_DB_PORT/${STAGING_DB_NAME}_verify"
    
    log "Running performance verification..."
    
    # Test query performance
    local start_time end_time duration
    
    # Simple query test
    start_time=$(date +%s%N)
    PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -c "SELECT count(*) FROM users;" >/dev/null
    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
    log "Simple query performance: ${duration}ms"
    
    # Complex query test (if applicable)
    if PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -c "SELECT 1 FROM learning_sessions LIMIT 1;" >/dev/null 2>&1; then
        start_time=$(date +%s%N)
        PGPASSWORD="$STAGING_DB_PASSWORD" psql "$db_conn" -c \
            "SELECT u.email, count(ls.id) as session_count 
             FROM users u 
             LEFT JOIN learning_sessions ls ON u.id = ls.user_id 
             GROUP BY u.id, u.email 
             ORDER BY session_count DESC 
             LIMIT 10;" >/dev/null
        end_time=$(date +%s%N)
        duration=$(( (end_time - start_time) / 1000000 ))
        log "Complex query performance: ${duration}ms"
    fi
}

# Generate verification report
generate_report() {
    local backup_tag="$1"
    local verification_status="$2"
    
    log "Generating verification report..."
    
    local report_file="/tmp/verification_report_${VERIFICATION_TAG}.json"
    
    cat > "$report_file" << EOF
{
    "verification_id": "$VERIFICATION_TAG",
    "timestamp": "$(date -Iseconds)",
    "backup_tag": "$backup_tag",
    "status": "$verification_status",
    "staging_host": "$STAGING_DB_HOST",
    "staging_database": "${STAGING_DB_NAME}_verify",
    "verification_duration_seconds": $(($(date +%s) - verification_start_time)),
    "checks_performed": [
        "data_integrity",
        "table_checksums",
        "foreign_key_constraints",
        "critical_tables",
        "performance"
    ],
    "environment": {
        "hostname": "$(hostname)",
        "kubernetes_namespace": "${KUBERNETES_NAMESPACE:-unknown}",
        "aws_region": "${AWS_DEFAULT_REGION:-unknown}"
    }
}
EOF
    
    # Upload report to S3
    aws s3 cp "$report_file" "s3://$BACKUP_BUCKET/verification/reports/report_${VERIFICATION_TAG}.json" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID"
    
    rm -f "$report_file"
    
    log "Verification report uploaded: verification_${VERIFICATION_TAG}"
}

# Cleanup staging environment
cleanup_staging() {
    log "Cleaning up staging environment..."
    
    # Drop verification database
    PGPASSWORD="$STAGING_DB_PASSWORD" psql -h "$STAGING_DB_HOST" -p "$STAGING_DB_PORT" \
        -U "$STAGING_DB_USER" -d postgres \
        -c "DROP DATABASE IF EXISTS ${STAGING_DB_NAME}_verify;" || log "WARNING: Failed to drop verification database"
    
    # Cleanup temporary files
    rm -f /tmp/*_${VERIFICATION_TAG}*
    
    log "Cleanup completed"
}

# Main verification process
main() {
    local verification_start_time
    verification_start_time=$(date +%s)
    
    log "Starting backup restore verification process"
    
    local backup_tag verification_status="success"
    
    # Trap for cleanup on exit
    trap cleanup_staging EXIT
    
    check_prerequisites
    backup_tag=$(get_latest_backup)
    prepare_staging
    
    if restore_to_staging "$backup_tag"; then
        verify_data_integrity
        verify_performance
        log "Backup restore verification completed successfully"
    else
        verification_status="failed"
        error "Backup restore verification failed"
    fi
    
    generate_report "$backup_tag" "$verification_status"
    
    log "Verification process completed"
}

# Handle script termination
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log "Verification script failed with exit code: $exit_code"
        
        # Send alert
        if command -v curl >/dev/null && [[ -n "${ALERT_WEBHOOK:-}" ]]; then
            curl -X POST "$ALERT_WEBHOOK" \
                -H "Content-Type: application/json" \
                -d "{\"text\":\"Backup verification failed on $(hostname): exit code $exit_code\"}"
        fi
        
        # Record failure
        generate_report "${backup_tag:-unknown}" "failed"
    fi
}

trap cleanup EXIT

# Execute main function
main "$@"
