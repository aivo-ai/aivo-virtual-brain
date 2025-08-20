#!/bin/bash
#
# PostgreSQL Backup with pgBackRest
# Encrypted, incremental backups with KMS integration
#

set -euo pipefail

# Configuration
BACKUP_TYPE="${BACKUP_TYPE:-incr}"  # full, diff, incr
STANZA="${PGBACKREST_STANZA:-aivo-postgres}"
RETENTION_FULL="${RETENTION_FULL:-7}"
RETENTION_DIFF="${RETENTION_DIFF:-14}"
ENCRYPTION_KEY_CMD="${ENCRYPTION_KEY_CMD:-aws kms decrypt --ciphertext-blob fileb://key.enc --output text --query Plaintext | base64 -d}"
BACKUP_TAG="$(date +%Y%m%d_%H%M%S)"
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
    log "Checking prerequisites..."
    
    command -v pgbackrest >/dev/null || error "pgBackRest not found"
    command -v aws >/dev/null || error "AWS CLI not found"
    
    # Check if PostgreSQL is accessible
    pgbackrest --stanza="$STANZA" check || error "pgBackRest check failed"
    
    # Test KMS access
    eval "$ENCRYPTION_KEY_CMD" >/dev/null || error "KMS key decryption failed"
    
    log "Prerequisites check passed"
}

# Perform backup
backup() {
    local backup_type="$1"
    
    log "Starting $backup_type backup for stanza: $STANZA"
    
    # Set backup-specific options
    local backup_opts=(
        --stanza="$STANZA"
        --type="$backup_type"
        --log-level-console="$LOG_LEVEL"
        --process-max=4
        --compress-type=lz4
        --compress-level=3
    )
    
    # Add encryption options
    backup_opts+=(
        --repo-cipher-type=aes-256-cbc
        --repo-cipher-pass-command="$ENCRYPTION_KEY_CMD"
    )
    
    # Execute backup
    if pgbackrest backup "${backup_opts[@]}"; then
        log "Backup completed successfully"
        
        # Record backup metadata
        record_backup_metadata "$backup_type"
        
        # Verify backup integrity
        verify_backup
        
        # Clean up old backups
        expire_backups
        
        return 0
    else
        error "Backup failed"
    fi
}

# Record backup metadata
record_backup_metadata() {
    local backup_type="$1"
    local metadata_file="/tmp/backup_metadata_${BACKUP_TAG}.json"
    
    cat > "$metadata_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "backup_type": "$backup_type",
    "stanza": "$STANZA",
    "tag": "$BACKUP_TAG",
    "hostname": "$(hostname)",
    "size_bytes": $(pgbackrest info --stanza="$STANZA" --output=json | jq -r '.[-1].backup[-1].info.size // 0'),
    "repo_total_size_bytes": $(pgbackrest info --stanza="$STANZA" --output=json | jq -r '.[-1].backup[-1].info.repository.size // 0'),
    "database_size_bytes": $(pgbackrest info --stanza="$STANZA" --output=json | jq -r '.[-1].backup[-1].info.database.size // 0')
}
EOF
    
    # Upload metadata to S3
    aws s3 cp "$metadata_file" "s3://${BACKUP_BUCKET}/metadata/postgres/${BACKUP_TAG}.json" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID"
    
    rm -f "$metadata_file"
    log "Backup metadata recorded"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    if pgbackrest check --stanza="$STANZA"; then
        log "Backup verification passed"
    else
        error "Backup verification failed"
    fi
}

# Expire old backups
expire_backups() {
    log "Expiring old backups..."
    
    pgbackrest expire \
        --stanza="$STANZA" \
        --repo-retention-full="$RETENTION_FULL" \
        --repo-retention-diff="$RETENTION_DIFF" \
        --log-level-console="$LOG_LEVEL"
    
    log "Backup expiration completed"
}

# Main execution
main() {
    log "Starting PostgreSQL backup process"
    
    check_prerequisites
    backup "$BACKUP_TYPE"
    
    log "PostgreSQL backup process completed successfully"
}

# Handle script termination
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log "Script failed with exit code: $exit_code"
        
        # Send alert
        if command -v curl >/dev/null && [[ -n "${ALERT_WEBHOOK:-}" ]]; then
            curl -X POST "$ALERT_WEBHOOK" \
                -H "Content-Type: application/json" \
                -d "{\"text\":\"PostgreSQL backup failed on $(hostname): exit code $exit_code\"}"
        fi
    fi
}

trap cleanup EXIT

# Execute main function
main "$@"
