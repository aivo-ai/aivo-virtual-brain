#!/bin/bash
#
# OpenSearch Snapshots and Backup Script
# Encrypted snapshots with KMS integration
#

set -euo pipefail

# Configuration
OS_ENDPOINT="${OPENSEARCH_ENDPOINT:-https://opensearch.aivo.svc.cluster.local:9200}"
OS_USERNAME="${OPENSEARCH_USERNAME:-admin}"
OS_PASSWORD="${OPENSEARCH_PASSWORD}"
SNAPSHOT_REPO="${SNAPSHOT_REPO:-aivo-snapshots}"
SNAPSHOT_BUCKET="${SNAPSHOT_BUCKET:-aivo-backup-opensearch}"
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

# OpenSearch API wrapper
os_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"
    
    local curl_opts=(
        -s
        -X "$method"
        -u "$OS_USERNAME:$OS_PASSWORD"
        -H "Content-Type: application/json"
        --insecure
    )
    
    if [[ -n "$data" ]]; then
        curl_opts+=(-d "$data")
    fi
    
    curl "${curl_opts[@]}" "$OS_ENDPOINT$path"
}

# Verify prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    command -v curl >/dev/null || error "curl not found"
    command -v aws >/dev/null || error "AWS CLI not found"
    command -v jq >/dev/null || error "jq not found"
    
    # Test OpenSearch connection
    if ! os_api GET "/_cluster/health" | jq -e '.status' >/dev/null; then
        error "Cannot connect to OpenSearch cluster"
    fi
    
    # Test S3 bucket access
    aws s3 ls "s3://$SNAPSHOT_BUCKET" >/dev/null || error "Cannot access snapshot S3 bucket: $SNAPSHOT_BUCKET"
    
    log "Prerequisites check passed"
}

# Setup snapshot repository
setup_snapshot_repository() {
    log "Setting up snapshot repository: $SNAPSHOT_REPO"
    
    # Check if repository exists
    if os_api GET "/_snapshot/$SNAPSHOT_REPO" | jq -e '.error' >/dev/null 2>&1; then
        log "Creating new snapshot repository"
        
        local repo_config
        repo_config=$(cat << EOF
{
    "type": "s3",
    "settings": {
        "bucket": "$SNAPSHOT_BUCKET",
        "base_path": "snapshots",
        "region": "${AWS_DEFAULT_REGION:-us-east-1}",
        "server_side_encryption": true,
        "kms_key_id": "$KMS_KEY_ID",
        "storage_class": "standard_ia",
        "compress": true,
        "chunk_size": "1gb",
        "max_restore_bytes_per_sec": "100mb",
        "max_snapshot_bytes_per_sec": "100mb"
    }
}
EOF
        )
        
        if ! os_api PUT "/_snapshot/$SNAPSHOT_REPO" "$repo_config" | jq -e '.acknowledged' >/dev/null; then
            error "Failed to create snapshot repository"
        fi
    else
        log "Snapshot repository already exists"
    fi
    
    # Verify repository
    if ! os_api POST "/_snapshot/$SNAPSHOT_REPO/_verify" | jq -e '.nodes | length' >/dev/null; then
        error "Snapshot repository verification failed"
    fi
    
    log "Snapshot repository setup completed"
}

# Get list of indices to backup
get_indices_to_backup() {
    local exclude_patterns="\..*|apm-.*|security-.*|opendistro-.*|opensearch-.*"
    
    os_api GET "/_cat/indices?format=json" | \
        jq -r ".[] | select(.index | test(\"$exclude_patterns\") | not) | .index" | \
        sort
}

# Create snapshot
create_snapshot() {
    local snapshot_name="snapshot_${BACKUP_TAG}"
    local indices
    indices=$(get_indices_to_backup | tr '\n' ',' | sed 's/,$//')
    
    if [[ -z "$indices" ]]; then
        log "No indices found to backup"
        return 0
    fi
    
    log "Creating snapshot: $snapshot_name for indices: $indices"
    
    local snapshot_config
    snapshot_config=$(cat << EOF
{
    "indices": "$indices",
    "ignore_unavailable": true,
    "include_global_state": false,
    "metadata": {
        "backup_tag": "$BACKUP_TAG",
        "created_by": "backup-script",
        "hostname": "$(hostname)",
        "timestamp": "$(date -Iseconds)"
    }
}
EOF
    )
    
    # Start snapshot
    local snapshot_response
    snapshot_response=$(os_api PUT "/_snapshot/$SNAPSHOT_REPO/$snapshot_name" "$snapshot_config")
    
    if ! echo "$snapshot_response" | jq -e '.accepted' >/dev/null; then
        error "Failed to start snapshot: $snapshot_response"
    fi
    
    log "Snapshot started, waiting for completion..."
    
    # Wait for snapshot completion
    local max_wait=3600  # 1 hour
    local elapsed=0
    local check_interval=30
    
    while [[ $elapsed -lt $max_wait ]]; do
        local status
        status=$(os_api GET "/_snapshot/$SNAPSHOT_REPO/$snapshot_name" | jq -r '.snapshots[0].state // "UNKNOWN"')
        
        case "$status" in
            "SUCCESS")
                log "Snapshot completed successfully"
                break
                ;;
            "FAILED"|"PARTIAL")
                error "Snapshot failed with status: $status"
                ;;
            "IN_PROGRESS")
                log "Snapshot in progress... (${elapsed}s elapsed)"
                sleep $check_interval
                elapsed=$((elapsed + check_interval))
                ;;
            *)
                log "Unknown snapshot status: $status, retrying..."
                sleep $check_interval
                elapsed=$((elapsed + check_interval))
                ;;
        esac
    done
    
    if [[ $elapsed -ge $max_wait ]]; then
        error "Snapshot timeout after ${max_wait}s"
    fi
    
    # Get snapshot details
    local snapshot_info
    snapshot_info=$(os_api GET "/_snapshot/$SNAPSHOT_REPO/$snapshot_name")
    
    # Record snapshot metadata
    echo "$snapshot_info" | jq '.snapshots[0]' > "/tmp/snapshot_${BACKUP_TAG}.json"
    
    aws s3 cp "/tmp/snapshot_${BACKUP_TAG}.json" "s3://${SNAPSHOT_BUCKET}/metadata/${BACKUP_TAG}.json" \
        --server-side-encryption aws:kms \
        --ssekms-key-id "$KMS_KEY_ID"
    
    rm -f "/tmp/snapshot_${BACKUP_TAG}.json"
    
    log "Snapshot metadata recorded"
}

# Verify snapshot integrity
verify_snapshot() {
    local snapshot_name="snapshot_${BACKUP_TAG}"
    
    log "Verifying snapshot integrity: $snapshot_name"
    
    # Get snapshot status
    local snapshot_status
    snapshot_status=$(os_api GET "/_snapshot/$SNAPSHOT_REPO/$snapshot_name" | jq -r '.snapshots[0]')
    
    local state
    local failed_shards
    local successful_shards
    
    state=$(echo "$snapshot_status" | jq -r '.state')
    failed_shards=$(echo "$snapshot_status" | jq -r '.shards.failed // 0')
    successful_shards=$(echo "$snapshot_status" | jq -r '.shards.successful // 0')
    
    if [[ "$state" != "SUCCESS" ]]; then
        error "Snapshot verification failed - state: $state"
    fi
    
    if [[ "$failed_shards" -gt 0 ]]; then
        error "Snapshot verification failed - failed shards: $failed_shards"
    fi
    
    if [[ "$successful_shards" -eq 0 ]]; then
        error "Snapshot verification failed - no successful shards"
    fi
    
    log "Snapshot verification passed - successful shards: $successful_shards"
}

# Clean up old snapshots
cleanup_old_snapshots() {
    log "Cleaning up snapshots older than $RETENTION_DAYS days..."
    
    local cutoff_timestamp
    cutoff_timestamp=$(date -d "$RETENTION_DAYS days ago" +%s)
    
    # Get list of snapshots
    local snapshots
    snapshots=$(os_api GET "/_snapshot/$SNAPSHOT_REPO/_all" | jq -r '.snapshots[] | "\(.snapshot)|\(.start_time_in_millis)"')
    
    while IFS='|' read -r snapshot_name start_time_millis; do
        if [[ -n "$snapshot_name" && -n "$start_time_millis" ]]; then
            local snapshot_timestamp=$((start_time_millis / 1000))
            
            if [[ $snapshot_timestamp -lt $cutoff_timestamp ]]; then
                log "Deleting old snapshot: $snapshot_name"
                
                if ! os_api DELETE "/_snapshot/$SNAPSHOT_REPO/$snapshot_name" | jq -e '.acknowledged' >/dev/null; then
                    log "WARNING: Failed to delete snapshot: $snapshot_name"
                fi
            fi
        fi
    done <<< "$snapshots"
    
    # Clean up old metadata
    local cutoff_date
    cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
    
    aws s3 ls "s3://${SNAPSHOT_BUCKET}/metadata/" | while read -r line; do
        local file_date
        file_date=$(echo "$line" | awk '{print $4}' | cut -d'_' -f1)
        
        if [[ -n "$file_date" && "$file_date" < "$cutoff_date" ]]; then
            local old_metadata="s3://${SNAPSHOT_BUCKET}/metadata/$(echo "$line" | awk '{print $4}')"
            log "Deleting old metadata: $old_metadata"
            aws s3 rm "$old_metadata"
        fi
    done
    
    log "Cleanup completed"
}

# Main backup process
main() {
    log "Starting OpenSearch snapshot process"
    
    check_prerequisites
    setup_snapshot_repository
    create_snapshot
    verify_snapshot
    cleanup_old_snapshots
    
    log "OpenSearch snapshot process completed successfully"
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
                -d "{\"text\":\"OpenSearch snapshot failed on $(hostname): exit code $exit_code\"}"
        fi
    fi
}

trap cleanup EXIT

# Execute main function
main "$@"
