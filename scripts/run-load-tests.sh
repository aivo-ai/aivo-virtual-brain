#!/bin/bash
# K6 Load Testing Runner Script
# Usage: ./run-load-tests.sh [test-type] [service] [environment]

set -e

# Default values
TEST_TYPE=${1:-smoke}
SERVICE=${2:-all}
ENVIRONMENT=${3:-local}

# Configuration
K6_VERSION="0.47.0"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$BASE_DIR/tests/load/k6"
RESULTS_DIR="$BASE_DIR/test-results/$(date +%Y%m%d_%H%M%S)"

# Environment URLs
case $ENVIRONMENT in
  local)
    BASE_URL="http://localhost:8080"
    ;;
  staging)
    BASE_URL="https://api-staging.aivo.ai"
    ;;
  production)
    BASE_URL="https://api.aivo.ai"
    ;;
  *)
    BASE_URL="$ENVIRONMENT"
    ;;
esac

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
  log_info "Checking prerequisites..."
  
  # Check if k6 is installed
  if ! command -v k6 &> /dev/null; then
    log_warning "k6 not found. Installing k6 v$K6_VERSION..."
    
    # Detect OS
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    case $ARCH in
      x86_64) ARCH="amd64" ;;
      arm64|aarch64) ARCH="arm64" ;;
    esac
    
    # Download and install k6
    K6_URL="https://github.com/grafana/k6/releases/download/v$K6_VERSION/k6-v$K6_VERSION-$OS-$ARCH.tar.gz"
    
    curl -L "$K6_URL" | tar xz
    sudo mv "k6-v$K6_VERSION-$OS-$ARCH/k6" /usr/local/bin/
    rm -rf "k6-v$K6_VERSION-$OS-$ARCH"
    
    log_success "k6 installed successfully"
  else
    log_success "k6 is already installed"
  fi
  
  # Check if jq is installed (for result parsing)
  if ! command -v jq &> /dev/null; then
    log_warning "jq not found. Please install jq for result parsing."
    log_info "Ubuntu/Debian: sudo apt-get install jq"
    log_info "macOS: brew install jq"
  fi
  
  # Create results directory
  mkdir -p "$RESULTS_DIR"
  log_info "Results will be saved to: $RESULTS_DIR"
}

# Check service health
check_service_health() {
  local service_name=$1
  local endpoint=$2
  
  log_info "Checking $service_name health..."
  
  if curl -f -s "$BASE_URL$endpoint" > /dev/null; then
    log_success "$service_name is healthy"
    return 0
  else
    log_error "$service_name is not responding at $BASE_URL$endpoint"
    return 1
  fi
}

# Run k6 test
run_k6_test() {
  local test_file=$1
  local service_name=$2
  
  log_info "Running $service_name load test..."
  log_info "Test type: $TEST_TYPE"
  log_info "Environment: $BASE_URL"
  
  # Set environment variables for k6
  export BASE_URL
  export TEST_TYPE
  export API_KEY="${API_KEY:-test-api-key}"
  export TENANT_ID="${TENANT_ID:-test-tenant}"
  export LEARNER_ID="${LEARNER_ID:-test-learner}"
  
  # Run the test
  cd "$TESTS_DIR"
  
  local output_file="$RESULTS_DIR/${service_name}-results.json"
  local summary_file="$RESULTS_DIR/${service_name}-summary.json"
  
  if k6 run \
    --out "json=$output_file" \
    --summary-export="$summary_file" \
    "$test_file"; then
    
    log_success "$service_name test completed successfully"
    
    # Parse and display SLO results if jq is available
    if command -v jq &> /dev/null && [ -f "$summary_file" ]; then
      parse_slo_results "$service_name" "$summary_file"
    fi
    
    return 0
  else
    log_error "$service_name test failed"
    return 1
  fi
}

# Parse SLO results
parse_slo_results() {
  local service_name=$1
  local summary_file=$2
  
  log_info "Parsing SLO results for $service_name..."
  
  case $service_name in
    gateway)
      local generate_p95=$(jq '.metrics.generate_duration.values["p(95)"]' "$summary_file" 2>/dev/null || echo "0")
      local embeddings_p95=$(jq '.metrics.embeddings_duration.values["p(95)"]' "$summary_file" 2>/dev/null || echo "0")
      local error_rate=$(jq '.metrics.errors.values.rate' "$summary_file" 2>/dev/null || echo "0")
      
      check_slo "Generate p95" "$generate_p95" "300" "ms"
      check_slo "Embeddings p95" "$embeddings_p95" "200" "ms"
      check_slo "Error rate" "$error_rate" "0.01" "%"
      ;;
      
    assessment)
      local answer_p95=$(jq '.metrics.assessment_answer_duration.values["p(95)"]' "$summary_file" 2>/dev/null || echo "0")
      local error_rate=$(jq '.metrics.assessment_errors.values.rate' "$summary_file" 2>/dev/null || echo "0")
      
      check_slo "Answer p95" "$answer_p95" "150" "ms"
      check_slo "Error rate" "$error_rate" "0.01" "%"
      ;;
      
    search)
      local suggest_p95=$(jq '.metrics.search_suggest_duration.values["p(95)"]' "$summary_file" 2>/dev/null || echo "0")
      local search_p95=$(jq '.metrics.search_query_duration.values["p(95)"]' "$summary_file" 2>/dev/null || echo "0")
      local error_rate=$(jq '.metrics.search_errors.values.rate' "$summary_file" 2>/dev/null || echo "0")
      
      check_slo "Suggest p95" "$suggest_p95" "120" "ms"
      check_slo "Search p95" "$search_p95" "200" "ms"
      check_slo "Error rate" "$error_rate" "0.01" "%"
      ;;
  esac
}

# Check individual SLO
check_slo() {
  local metric_name=$1
  local actual_value=$2
  local threshold=$3
  local unit=$4
  
  if (( $(echo "$actual_value <= $threshold" | bc -l) )); then
    log_success "✅ $metric_name: ${actual_value}${unit} ≤ ${threshold}${unit}"
  else
    log_error "❌ $metric_name: ${actual_value}${unit} > ${threshold}${unit}"
  fi
}

# Generate report
generate_report() {
  local report_file="$RESULTS_DIR/load-test-report.md"
  
  log_info "Generating load test report..."
  
  cat > "$report_file" << EOF
# Load Test Report

**Test Type:** $TEST_TYPE
**Environment:** $BASE_URL
**Timestamp:** $(date -u)
**Results Directory:** $RESULTS_DIR

## Test Summary

EOF

  # Add service-specific results
  for service in gateway assessment search; do
    local summary_file="$RESULTS_DIR/${service}-summary.json"
    if [ -f "$summary_file" ]; then
      echo "### $service Service" >> "$report_file"
      echo "" >> "$report_file"
      
      # Extract key metrics
      local total_requests=$(jq '.metrics.http_reqs.values.count' "$summary_file" 2>/dev/null || echo "N/A")
      local avg_duration=$(jq '.metrics.http_req_duration.values.avg' "$summary_file" 2>/dev/null || echo "N/A")
      local p95_duration=$(jq '.metrics.http_req_duration.values["p(95)"]' "$summary_file" 2>/dev/null || echo "N/A")
      local error_count=$(jq '.metrics.http_req_failed.values.count' "$summary_file" 2>/dev/null || echo "N/A")
      
      echo "- **Total Requests:** $total_requests" >> "$report_file"
      echo "- **Average Duration:** ${avg_duration}ms" >> "$report_file"
      echo "- **P95 Duration:** ${p95_duration}ms" >> "$report_file"
      echo "- **Error Count:** $error_count" >> "$report_file"
      echo "" >> "$report_file"
    fi
  done
  
  echo "## Files Generated" >> "$report_file"
  echo "" >> "$report_file"
  ls -la "$RESULTS_DIR" | awk 'NR>1 {print "- " $9}' >> "$report_file"
  
  log_success "Report generated: $report_file"
}

# Main execution
main() {
  log_info "Starting K6 Load Testing"
  log_info "Test Type: $TEST_TYPE"
  log_info "Service: $SERVICE"
  log_info "Environment: $ENVIRONMENT"
  
  check_prerequisites
  
  # Health checks for local environment
  if [ "$ENVIRONMENT" = "local" ]; then
    log_info "Performing health checks..."
    
    if ! check_service_health "Gateway" "/health"; then
      log_error "Gateway service health check failed. Is the service running?"
      exit 1
    fi
  fi
  
  # Run tests based on service selection
  case $SERVICE in
    gateway)
      run_k6_test "gateway-generate.js" "gateway"
      ;;
    assessment)
      run_k6_test "assessment.js" "assessment"
      ;;
    search)
      run_k6_test "search.js" "search"
      ;;
    all)
      log_info "Running all service tests..."
      run_k6_test "gateway-generate.js" "gateway"
      run_k6_test "assessment.js" "assessment"
      run_k6_test "search.js" "search"
      ;;
    *)
      log_error "Unknown service: $SERVICE"
      log_info "Available services: gateway, assessment, search, all"
      exit 1
      ;;
  esac
  
  generate_report
  
  log_success "Load testing completed!"
  log_info "Results saved to: $RESULTS_DIR"
}

# Script usage
usage() {
  cat << EOF
Usage: $0 [test-type] [service] [environment]

Arguments:
  test-type    Type of test to run (smoke, load, stress) [default: smoke]
  service      Service to test (gateway, assessment, search, all) [default: all]
  environment  Environment to test (local, staging, production, or URL) [default: local]

Examples:
  $0                          # Run smoke tests on all services locally
  $0 load gateway staging     # Run load test on gateway in staging
  $0 stress all production    # Run stress test on all services in production
  $0 smoke search http://custom-url:8080  # Custom environment URL

Environment Variables:
  API_KEY      API key for authentication [default: test-api-key]
  TENANT_ID    Tenant ID for testing [default: test-tenant]
  LEARNER_ID   Learner ID for testing [default: test-learner]

EOF
}

# Handle help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  usage
  exit 0
fi

# Run main function
main "$@"
