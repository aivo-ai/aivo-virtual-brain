#!/usr/bin/env python3
"""
Mock Health Server for AIVO Services
Provides health endpoints and mock responses for testing Grafana dashboards.
"""

import time
import random
import json
from flask import Flask, request, jsonify, Response
import threading
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['service', 'method', 'route', 'status_code'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['service', 'method', 'route'])
AI_INFERENCE_COUNT = Counter('ai_inference_requests_total', 'Total AI inference requests', ['service'])
AI_INFERENCE_DURATION = Histogram('ai_inference_duration_seconds', 'AI inference duration', ['service'])
AI_SCORING_COUNT = Counter('ai_scoring_requests_total', 'Total AI scoring requests', ['service'])
AI_SCORING_DURATION = Histogram('ai_scoring_duration_seconds', 'AI scoring duration', ['service'])
AI_IEP_GENERATION_COUNT = Counter('ai_iep_generation_requests_total', 'Total IEP generation requests', ['service'])
AI_IEP_GENERATION_DURATION = Histogram('ai_iep_generation_duration_seconds', 'IEP generation duration', ['service'])

# Payment metrics
PAYMENT_TRANSACTIONS = Counter('payment_transactions_total', 'Total payment transactions', ['service', 'status'])
PAYMENT_REVENUE = Counter('payment_revenue_total', 'Total payment revenue', ['service'])
PAYMENT_PROCESSING_COST = Counter('payment_processing_cost_total', 'Total payment processing costs', ['service'])

# Assessment metrics
ASSESSMENT_STARTED = Counter('assessment_started_total', 'Total assessments started', ['service'])
ASSESSMENT_COMPLETED = Counter('assessment_completed_total', 'Total assessments completed', ['service'])
ASSESSMENT_SCORE = Gauge('assessment_score', 'Assessment score', ['service', 'assessment_id'])

# IEP metrics
IEP_GENERATED = Counter('iep_generated_total', 'Total IEPs generated', ['service'])
IEP_MODIFIED = Counter('iep_modified_total', 'Total IEPs modified', ['service'])
IEP_APPROVED = Counter('iep_approved_total', 'Total IEPs approved', ['service'])
IEP_COMPLIANCE_SCORE = Gauge('iep_compliance_score', 'IEP compliance score', ['service'])

# Infrastructure cost metrics (placeholder)
INFRASTRUCTURE_COST = Counter('infrastructure_cost_total', 'Total infrastructure costs', ['service'])

# Database metrics
DB_POOL_ACTIVE = Gauge('db_pool_active_connections', 'Active database connections', ['service'])
DB_POOL_IDLE = Gauge('db_pool_idle_connections', 'Idle database connections', ['service'])
DB_POOL_MAX = Gauge('db_pool_max_connections', 'Max database connections', ['service'])

class MockMetricsUpdater:
    """Updates metrics in background to simulate real service behavior"""
    
    def __init__(self):
        self.running = True
        self.services = ['auth-svc', 'user-svc', 'learner-svc', 'payment-svc', 'assessment-svc', 'iep-svc']
        
    def update_background_metrics(self):
        """Update metrics in background"""
        while self.running:
            try:
                # Update database pool metrics
                for service in self.services:
                    DB_POOL_ACTIVE.labels(service=service).set(random.randint(5, 15))
                    DB_POOL_IDLE.labels(service=service).set(random.randint(2, 8))
                    DB_POOL_MAX.labels(service=service).set(20)
                
                # Update infrastructure costs (small increments)
                for service in self.services:
                    cost_increment = random.uniform(0.001, 0.01)  # $0.001 to $0.01 per update
                    INFRASTRUCTURE_COST.labels(service=service)._value._value += cost_increment
                
                # Update compliance scores
                IEP_COMPLIANCE_SCORE.labels(service='iep-svc').set(random.uniform(85, 98))
                
                time.sleep(10)  # Update every 10 seconds
            except Exception as e:
                logger.error(f"Error updating background metrics: {e}")

def get_service_from_path(path: str) -> str:
    """Extract service name from request path"""
    if path.startswith('/auth'):
        return 'auth-svc'
    elif path.startswith('/users'):
        return 'user-svc'
    elif path.startswith('/learners'):
        return 'learner-svc'
    elif path.startswith('/payments'):
        return 'payment-svc'
    elif path.startswith('/assessments'):
        return 'assessment-svc'
    elif path.startswith('/iep'):
        return 'iep-svc'
    else:
        return 'unknown-svc'

def simulate_response_delay(scenario: str):
    """Simulate different response scenarios"""
    if scenario == "slow":
        time.sleep(random.uniform(2.0, 5.0))  # 2-5 second delay
    elif scenario == "error_5xx":
        time.sleep(random.uniform(0.1, 0.5))  # Short delay before error
    else:
        time.sleep(random.uniform(0.01, 0.1))  # Normal response time

@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    # Get service and scenario from headers
    service = request.headers.get('X-Service', get_service_from_path(request.path))
    scenario = request.headers.get('X-Scenario', 'success')
    
    # Calculate duration
    duration = time.time() - getattr(request, 'start_time', time.time())
    
    # Determine status code based on scenario
    if scenario == "error_4xx":
        response.status_code = random.choice([400, 401, 403, 404])
    elif scenario == "error_5xx" or request.headers.get('X-Force-Error') == '5xx':
        response.status_code = random.choice([500, 502, 503, 504])
    
    # Update Prometheus metrics
    REQUEST_COUNT.labels(
        service=service,
        method=request.method,
        route=request.path,
        status_code=str(response.status_code)
    ).inc()
    
    REQUEST_DURATION.labels(
        service=service,
        method=request.method,
        route=request.path
    ).observe(duration)
    
    return response

# Health endpoints for all services
@app.route('/health')
@app.route('/auth/health')
@app.route('/users/health') 
@app.route('/learners/health')
@app.route('/payments/health')
@app.route('/assessments/health')
@app.route('/iep/health')
def health():
    return jsonify({"status": "healthy", "timestamp": int(time.time())})

# Mock service endpoints
@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def auth_service(path):
    scenario = request.headers.get('X-Scenario', 'success')
    simulate_response_delay(scenario)
    return jsonify({"service": "auth", "path": path, "method": request.method})

@app.route('/users/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def user_service(path):
    scenario = request.headers.get('X-Scenario', 'success')
    simulate_response_delay(scenario)
    return jsonify({"service": "user", "path": path, "method": request.method})

@app.route('/learners/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def learner_service(path):
    scenario = request.headers.get('X-Scenario', 'success')
    simulate_response_delay(scenario)
    
    # Simulate AI inference for learner service
    if 'persona' in path or 'inference' in path:
        start_time = time.time()
        time.sleep(random.uniform(0.1, 0.5))  # AI inference delay
        duration = time.time() - start_time
        
        AI_INFERENCE_COUNT.labels(service='learner-svc').inc()
        AI_INFERENCE_DURATION.labels(service='learner-svc').observe(duration)
    
    return jsonify({"service": "learner", "path": path, "method": request.method})

@app.route('/payments/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def payment_service(path):
    scenario = request.headers.get('X-Scenario', 'success')
    simulate_response_delay(scenario)
    
    # Simulate payment transactions
    if request.method == 'POST' and 'process' in path:
        success = random.random() > 0.05  # 95% success rate
        status = 'success' if success else 'failed'
        
        PAYMENT_TRANSACTIONS.labels(service='payment-svc', status=status).inc()
        
        if success:
            amount = random.uniform(10.0, 500.0)
            PAYMENT_REVENUE.labels(service='payment-svc')._value._value += amount
            PAYMENT_PROCESSING_COST.labels(service='payment-svc')._value._value += amount * 0.029  # 2.9% processing fee
    
    return jsonify({"service": "payment", "path": path, "method": request.method})

@app.route('/assessments/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def assessment_service(path):
    scenario = request.headers.get('X-Scenario', 'success')
    simulate_response_delay(scenario)
    
    # Simulate assessment lifecycle
    if request.method == 'GET' and path == '':
        ASSESSMENT_STARTED.labels(service='assessment-svc').inc()
    elif request.method == 'POST' and 'submit' in path:
        ASSESSMENT_COMPLETED.labels(service='assessment-svc').inc()
        score = random.randint(60, 100)
        assessment_id = path.split('/')[0]
        ASSESSMENT_SCORE.labels(service='assessment-svc', assessment_id=assessment_id).set(score)
    elif 'score' in path:
        # AI scoring simulation
        start_time = time.time()
        time.sleep(random.uniform(0.2, 1.0))  # AI scoring delay
        duration = time.time() - start_time
        
        AI_SCORING_COUNT.labels(service='assessment-svc').inc()
        AI_SCORING_DURATION.labels(service='assessment-svc').observe(duration)
    
    return jsonify({"service": "assessment", "path": path, "method": request.method})

@app.route('/iep/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def iep_service(path):
    scenario = request.headers.get('X-Scenario', 'success')
    simulate_response_delay(scenario)
    
    # Simulate IEP lifecycle
    if request.method == 'POST' and 'generate' in path:
        # AI IEP generation simulation
        start_time = time.time()
        time.sleep(random.uniform(1.0, 3.0))  # AI generation delay
        duration = time.time() - start_time
        
        AI_IEP_GENERATION_COUNT.labels(service='iep-svc').inc()
        AI_IEP_GENERATION_DURATION.labels(service='iep-svc').observe(duration)
        IEP_GENERATED.labels(service='iep-svc').inc()
    elif request.method == 'PUT':
        IEP_MODIFIED.labels(service='iep-svc').inc()
        if 'approve' in path:
            IEP_APPROVED.labels(service='iep-svc').inc()
    
    return jsonify({"service": "iep", "path": path, "method": request.method})

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

if __name__ == '__main__':
    # Start background metrics updater
    metrics_updater = MockMetricsUpdater()
    metrics_thread = threading.Thread(target=metrics_updater.update_background_metrics, daemon=True)
    metrics_thread.start()
    
    logger.info("Starting AIVO Mock Health Server on port 8000")
    logger.info("Available endpoints:")
    logger.info("  - Health: /health, /auth/health, /users/health, etc.")
    logger.info("  - Metrics: /metrics")
    logger.info("  - Services: /auth/*, /users/*, /learners/*, /payments/*, /assessments/*, /iep/*")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
