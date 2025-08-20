#!/bin/bash
#
# MinIO Backup and Sync Script
# Encrypted sync to remote S3 bucket with KMS
#

set -euo pipefail

# Configuration
SOURCE_ENDPOINT="${MINIO_SOURCE_ENDPOINT:-http://minio.aivo.svc.cluster.local:9000}"
SOURCE_ACCESS_KEY="${MINIO_SOURCE_ACCESS_KEY}"
SOURCE_SECRET_KEY="${MINIO_SOURCE_SECRET_KEY}"
TARGET_BUCKET="${BACKUP_TARGET_BUCKET:-aivo-backup-minio}"
TARGET_PREFIX="${BACKUP_TARGET_PREFIX:-minio-data}"
KMS_KEY_ID="${KMS_KEY_ID}"
BACKUP_TAG="$(date +%Y%m%d_%H%M%S)"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
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
    
    command -v mc >/dev/null || error "MinIO client (mc) not found"
    command -v aws >/dev/null || error "AWS CLI not found"
    command -v jq >/dev/null || error "jq not found"
    
    # Test MinIO source connection
    mc config host add source "$SOURCE_ENDPOINT" "$SOURCE_ACCESS_KEY" "$SOURCE_SECRET_KEY" || error "Failed to configure MinIO source"
    mc admin info source >/dev/null || error "Cannot connect to MinIO source"
    
    # Test S3 target access
    aws s3 ls "s3://$TARGET_BUCKET" >/dev/null || error "Cannot access target S3 bucket: $TARGET_BUCKET"
    
    log "Prerequisites check passed"
}

# List source buckets
list_source_buckets() {
    mc ls source | awk '{print $5}' | grep -v '^$'
}

# Backup single bucket
backup_bucket() {
    local bucket="$1"
    local backup_path="s3://${TARGET_BUCKET}/${TARGET_PREFIX}/${BACKUP_TAG}/${bucket}"
    
    log "Backing up bucket: $bucket to $backup_path"
    
    # Create temporary directory for staging
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" RETURN
    
    # Download bucket contents
    log "Downloading bucket contents..."
    if ! mc mirror "source/$bucket" "$temp_dir/$bucket" --overwrite; then
        error "Failed to download bucket: $bucket"
    fi
    
    # Calculate checksums
    log "Calculating checksums..."
    find "$temp_dir/$bucket" -type f -exec sha256sum {} \; > "$temp_dir/${bucket}_checksums.txt"
    
    # Create backup metadata
    local objects_count
    local total_size
    objects_count=$(find "$temp_dir/$bucket" -type f | wc -l)
    total_size=$(du -sb "$temp_dir/$bucket" | cut -f1)
    
    cat > "$temp_dir/${bucket}_metadata.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "bucket": "$bucket",
    "backup_tag": "$BACKUP_TAG",
    "objects_count": $objects_count,
    "total_size_bytes": $total_size,
    "source_endpoint": "$SOURCE_ENDPOINT",
    "target_path": "$backup_path"
}
EOF
    
    # Upload to S3 with encryption
    log "Uploading to S3 with KMS encryption..."
    aws s3 sync "$temp_dir/$bucket" "$backup_path/" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID" \
        --storage-class STANDARD_IA \
        --metadata backup_tag="$BACKUP_TAG",source_bucket="$bucket"
    
    # Upload metadata and checksums
    aws s3 cp "$temp_dir/${bucket}_metadata.json" "s3://${TARGET_BUCKET}/metadata/minio/${BACKUP_TAG}/${bucket}_metadata.json" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID"
    
    aws s3 cp "$temp_dir/${bucket}_checksums.txt" "s3://${TARGET_BUCKET}/metadata/minio/${BACKUP_TAG}/${bucket}_checksums.txt" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID"
    
    log "Backup completed for bucket: $bucket"
}

# Verify backup integrity
verify_backup() {
    local bucket="$1"
    local backup_path="s3://${TARGET_BUCKET}/${TARGET_PREFIX}/${BACKUP_TAG}/${bucket}"
    local checksums_path="s3://${TARGET_BUCKET}/metadata/minio/${BACKUP_TAG}/${bucket}_checksums.txt"
    
    log "Verifying backup integrity for bucket: $bucket"
    
    # Create temporary directory for verification
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" RETURN
    
    # Download checksums
    aws s3 cp "$checksums_path" "$temp_dir/checksums.txt"
    
    # Download and verify a sample of files (first 10)
    local sample_files
    sample_files=$(head -10 "$temp_dir/checksums.txt" | awk '{print $2}' | sed "s|$temp_dir/$bucket/||")
    
    for file in $sample_files; do
        if [[ -n "$file" ]]; then
            # Download file from backup
            aws s3 cp "$backup_path/$file" "$temp_dir/verify_$file" >/dev/null 2>&1 || continue
            
            # Calculate checksum
            local actual_checksum
            actual_checksum=$(sha256sum "$temp_dir/verify_$file" | awk '{print $1}')
            
            # Get expected checksum
            local expected_checksum
            expected_checksum=$(grep "$file" "$temp_dir/checksums.txt" | awk '{print $1}')
            
            if [[ "$actual_checksum" == "$expected_checksum" ]]; then
                log "Checksum verified for: $file"
            else
                error "Checksum mismatch for: $file"
            fi
        fi
    done
    
    log "Backup verification completed for bucket: $bucket"
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local cutoff_date
    cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
    
    # List and delete old backup directories
    aws s3 ls "s3://${TARGET_BUCKET}/${TARGET_PREFIX}/" | while read -r line; do
        local dir_date
        dir_date=$(echo "$line" | awk '{print $2}' | cut -d'_' -f1 | tr -d '/')
        
        if [[ -n "$dir_date" && "$dir_date" < "$cutoff_date" ]]; then
            local old_backup_path="s3://${TARGET_BUCKET}/${TARGET_PREFIX}/${dir_date}_*"
            log "Deleting old backup: $old_backup_path"
            aws s3 rm "$old_backup_path" --recursive
        fi
    done
    
    # Clean up old metadata
    aws s3 ls "s3://${TARGET_BUCKET}/metadata/minio/" | while read -r line; do
        local dir_date
        dir_date=$(echo "$line" | awk '{print $2}' | cut -d'_' -f1 | tr -d '/')
        
        if [[ -n "$dir_date" && "$dir_date" < "$cutoff_date" ]]; then
            local old_metadata_path="s3://${TARGET_BUCKET}/metadata/minio/${dir_date}_*"
            log "Deleting old metadata: $old_metadata_path"
            aws s3 rm "$old_metadata_path" --recursive
        fi
    done
    
    log "Cleanup completed"
}

# Main backup process
main() {
    log "Starting MinIO backup process"
    
    check_prerequisites
    
    # Get list of buckets to backup
    local buckets
    buckets=$(list_source_buckets)
    
    if [[ -z "$buckets" ]]; then
        log "No buckets found to backup"
        return 0
    fi
    
    log "Found buckets to backup: $buckets"
    
    # Backup each bucket
    for bucket in $buckets; do
        backup_bucket "$bucket"
        verify_backup "$bucket"
    done
    
    # Clean up old backups
    cleanup_old_backups
    
    # Record overall backup completion
    cat > "/tmp/minio_backup_${BACKUP_TAG}.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "backup_tag": "$BACKUP_TAG",
    "buckets_backed_up": [$(echo "$buckets" | sed 's/^/"/' | sed 's/$/"/' | tr '\n' ',' | sed 's/,$//')],
    "status": "completed"
}
EOF
    
    aws s3 cp "/tmp/minio_backup_${BACKUP_TAG}.json" "s3://${TARGET_BUCKET}/metadata/minio/${BACKUP_TAG}_summary.json" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID"
    
    rm -f "/tmp/minio_backup_${BACKUP_TAG}.json"
    
    log "MinIO backup process completed successfully"
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
                -d "{\"text\":\"MinIO backup failed on $(hostname): exit code $exit_code\"}"
        fi
    fi
}

trap cleanup EXIT

# Execute main function
main "$@"
