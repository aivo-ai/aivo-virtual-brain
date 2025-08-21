"""
Simple validation test for S4-16 Search Implementation
Tests basic functionality without requiring OpenSearch cluster
"""

import pytest
import json
from pathlib import Path

# Test configuration file parsing
def test_analyzer_configs():
    """Test that all analyzer configuration files are valid JSON"""
    opensearch_dir = Path("opensearch")
    
    # Test all analyzer files
    for locale in ["en", "es", "fr", "ar", "zh-Hans", "hi", "pt", "ig", "yo", "ha", "efi", "sw", "xh", "ki"]:
        analyzer_file = opensearch_dir / f"analyzers-{locale}.json"
        
        assert analyzer_file.exists(), f"Analyzer file for {locale} not found"
        
        with open(analyzer_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Validate structure
        assert "settings" in config
        assert "mappings" in config
        assert "analysis" in config["settings"]
        assert "analyzer" in config["settings"]["analysis"]
        
        # Check for language-specific analyzer
        locale_mapping = {
            "en": "english",
            "es": "spanish", 
            "fr": "french",
            "ar": "arabic",
            "zh-Hans": "chinese",
            "hi": "hindi",
            "pt": "portuguese",
            "ig": "igbo",
            "yo": "yoruba",
            "ha": "hausa",
            "efi": "efik",
            "sw": "swahili",
            "xh": "xhosa",
            "ki": "kikuyu"
        }
        
        analyzer_key = f"aivo_{locale_mapping[locale]}"
        assert analyzer_key in config["settings"]["analysis"]["analyzer"]
        
        print(f"✅ {locale} analyzer config valid")

def test_synonym_files():
    """Test that all synonym files exist and have content"""
    opensearch_dir = Path("opensearch")
    
    for locale in ["en", "es", "fr", "ar", "zh-Hans", "hi", "pt", "ig", "yo", "ha", "efi", "sw", "xh", "ki"]:
        synonym_file = opensearch_dir / f"synonyms-{locale}.txt"
        
        assert synonym_file.exists(), f"Synonym file for {locale} not found"
        
        with open(synonym_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        assert len(content) > 0, f"Synonym file for {locale} is empty"
        
        # Check for educational content
        content_lower = content.lower()
        
        # Define language-specific math terms
        math_terms_by_locale = {
            "en": ["math", "mathematics", "algebra", "number", "calculation"],
            "es": ["matemáticas", "mates", "álgebra", "número", "suma"],
            "fr": ["mathématiques", "maths", "algèbre", "nombre", "calcul"],
            "ar": ["رياضيات", "حساب", "جبر", "رقم", "عدد"],
            "zh-Hans": ["数学", "算术", "代数", "数字", "计算"],
            "hi": ["गणित", "अंकगणित", "बीजगणित", "संख्या", "गणना"],
            "pt": ["matemática", "álgebra", "número", "cálculo", "soma"],
            "ig": ["mgbako", "ọnụọgụgụ", "algebra", "namba", "ịgbakọ"],
            "yo": ["isiro", "eka", "algebra", "nọmba", "isiro"],
            "ha": ["lissafi", "algebra", "lamba", "kididdiga", "tara"],
            "efi": ["nkpo", "algebra", "namba", "ukara", "tua"],
            "sw": ["hisabati", "algebra", "nambari", "hesabu", "kujumlisha"],
            "xh": ["imathematika", "algebra", "inani", "ukudibanisa", "amanani"],
            "ki": ["mabataro", "algebra", "namba", "kuongera", "kididdiga"]
        }
        
        # Use appropriate terms for the locale
        math_terms = math_terms_by_locale.get(locale, ["math", "mathematics", "algebra"])
        has_math = any(term in content_lower for term in math_terms)
        assert has_math, f"No math terms found in {locale} synonyms. Searched for: {math_terms}"
        
        print(f"✅ {locale} synonym file valid")

def test_supported_locales():
    """Test that we support all expected locales"""
    expected_locales = {
        "en", "es", "fr", "ar", "zh-Hans", "hi", "pt", 
        "ig", "yo", "ha", "efi", "sw", "xh", "ki"
    }
    
    opensearch_dir = Path("opensearch")
    
    # Check analyzer files
    analyzer_files = list(opensearch_dir.glob("analyzers-*.json"))
    analyzer_locales = {f.stem.replace("analyzers-", "") for f in analyzer_files}
    
    assert analyzer_locales == expected_locales, f"Missing analyzer locales: {expected_locales - analyzer_locales}"
    
    # Check synonym files  
    synonym_files = list(opensearch_dir.glob("synonyms-*.txt"))
    synonym_locales = {f.stem.replace("synonyms-", "") for f in synonym_files}
    
    assert synonym_locales == expected_locales, f"Missing synonym locales: {expected_locales - synonym_locales}"
    
    print(f"✅ All {len(expected_locales)} locales supported")

def test_docker_compose_config():
    """Test Docker Compose configuration"""
    docker_compose_file = Path("docker-compose.yml")
    
    assert docker_compose_file.exists(), "docker-compose.yml not found"
    
    with open(docker_compose_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check for required services
    assert "search-svc:" in content
    assert "opensearch:" in content
    assert "opensearch-dashboards:" in content
    
    # Check for port mappings
    assert "8082:8082" in content  # Search service
    assert "9200:9200" in content  # OpenSearch
    assert "5601:5601" in content  # Dashboards
    
    print("✅ Docker Compose configuration valid")

def test_dockerfile():
    """Test Dockerfile configuration"""
    dockerfile = Path("Dockerfile")
    
    assert dockerfile.exists(), "Dockerfile not found"
    
    with open(dockerfile, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check for required components
    assert "FROM python:" in content
    assert "COPY requirements.txt" in content
    assert "pip install" in content
    assert "EXPOSE 8082" in content
    assert "HEALTHCHECK" in content
    
    print("✅ Dockerfile configuration valid")

def test_requirements_file():
    """Test requirements.txt has necessary dependencies"""
    requirements_file = Path("requirements.txt")
    
    assert requirements_file.exists(), "requirements.txt not found"
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check for key dependencies
    required_packages = [
        "fastapi",
        "uvicorn", 
        "opensearch-py",
        "pydantic",
        "pytest",
        "aiohttp"
    ]
    
    for package in required_packages:
        assert package in content, f"Missing required package: {package}"
        
    print("✅ Requirements file has all necessary dependencies")

if __name__ == "__main__":
    print("🧪 Running S4-16 Search Implementation Validation Tests...")
    
    test_analyzer_configs()
    test_synonym_files() 
    test_supported_locales()
    test_docker_compose_config()
    test_dockerfile()
    test_requirements_file()
    
    print("\n🎉 All validation tests passed!")
    print("✅ S4-16 Search Relevance & Multilingual Synonyms implementation is ready!")
