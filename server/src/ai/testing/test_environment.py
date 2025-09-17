"""
Environment Test Script
Validates that all required services and dependencies are properly configured
before running AI system tests.
"""

import sys
import os
import json
from datetime import datetime

# Add the project root directory to the Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.append(PROJECT_ROOT)

def test_mongodb():
    """Test MongoDB connection."""
    print("🔍 Testing MongoDB connection...")
    try:
        import pymongo
        client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        
        # Test database access
        db = client['algofinance']
        test_collection = db['test_connection']
        test_doc = {'test': 'connection', 'timestamp': datetime.now()}
        result = test_collection.insert_one(test_doc)
        test_collection.delete_one({'_id': result.inserted_id})
        
        print("   ✅ MongoDB: Connected and writable")
        return True
    except Exception as e:
        print(f"   ❌ MongoDB: Connection failed - {e}")
        print("   💡 Solution: Start MongoDB service with 'net start MongoDB'")
        return False

def test_rabbitmq():
    """Test RabbitMQ connection."""
    print("🔍 Testing RabbitMQ connection...")
    try:
        import pika
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost', heartbeat=10, blocked_connection_timeout=5)
        )
        channel = connection.channel()
        
        # Test queue operations
        test_queue = 'test_connection_queue'
        channel.queue_declare(queue=test_queue, durable=False)
        channel.basic_publish(exchange='', routing_key=test_queue, body='test message')
        
        # Cleanup
        channel.queue_delete(queue=test_queue)
        connection.close()
        
        print("   ✅ RabbitMQ: Connected and operational")
        return True
    except Exception as e:
        print(f"   ⚠️ RabbitMQ: Connection failed - {e}")
        print("   💡 Note: System will work in degraded mode without RabbitMQ")
        print("   💡 To enable full features: Start RabbitMQ service with 'net start RabbitMQ'")
        return False

def test_angel_one_config():
    """Test Angel One API configuration."""
    print("🔍 Testing Angel One API configuration...")
    try:
        from server.src.config import settings
        
        # Check if essential credentials are configured
        required_vars = ['API_KEY', 'SECRET_KEY', 'CLIENT_ID', 'PASSWORD', 'TOTP_SECRET']
        missing_vars = []
        
        for var in required_vars:
            if not hasattr(settings, var) or not getattr(settings, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"   ❌ Angel One API: Missing configuration - {', '.join(missing_vars)}")
            print("   💡 Solution: Configure missing variables in .env file")
            return False
        
        print("   ✅ Angel One API: Configuration complete")
        return True
    except Exception as e:
        print(f"   ❌ Angel One API: Configuration error - {e}")
        return False

def test_angel_one_connection():
    """Test Angel One API connection."""
    print("🔍 Testing Angel One API connection...")
    try:
        from server.src.core.connections import ConnectionManager
        
        # Try to get SmartAPI client
        client = ConnectionManager.get_smartapi_client()
        if client:
            print("   ✅ Angel One API: Connection successful")
            return True
        else:
            print("   ❌ Angel One API: Connection failed")
            return False
    except Exception as e:
        print(f"   ❌ Angel One API: Connection error - {e}")
        print("   💡 Solution: Check API credentials and network connectivity")
        return False

def test_python_dependencies():
    """Test required Python packages."""
    print("🔍 Testing Python dependencies...")
    
    required_packages = [
        ('numpy', 'Scientific computing'),
        ('pandas', 'Data manipulation'),
        ('pymongo', 'MongoDB driver'),
        ('pika', 'RabbitMQ client'),
    ]
    
    optional_packages = [
        ('sklearn', 'Machine learning - scikit-learn'),
        ('xgboost', 'Gradient boosting'),
        ('arch', 'GARCH volatility models'),
        ('statsmodels', 'Time series analysis'),
    ]
    
    missing_required = []
    missing_optional = []
    
    # Test required packages
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}: Available")
        except ImportError:
            missing_required.append((package, description))
            print(f"   ❌ {package}: Missing - {description}")
    
    # Test optional packages
    for package, description in optional_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}: Available")
        except ImportError:
            missing_optional.append((package, description))
            print(f"   ⚠️ {package}: Missing - {description} (optional)")
    
    if missing_required:
        print(f"\n   💡 Install missing required packages:")
        for package, desc in missing_required:
            print(f"      pip install {package}")
        return False
    
    if missing_optional:
        print(f"\n   💡 For enhanced AI features, install optional packages:")
        for package, desc in missing_optional:
            print(f"      pip install {package}")
    
    return True

def test_ai_components():
    """Test AI components basic functionality."""
    print("🔍 Testing AI components basic functionality...")
    
    try:
        # Test imports
        from server.src.ai.risk_management.ai_risk_engine import AIRiskEngine
        from server.src.ai.volatility_analysis.volatility_analyzer import AdvancedVolatilityAnalyzer
        from server.src.ai.central_ai_engine import CentralAIEngine
        from server.src.core.message_broker import get_message_broker
        
        print("   ✅ AI components: All imports successful")
        
        # Test basic initialization
        risk_engine = AIRiskEngine()
        vol_analyzer = AdvancedVolatilityAnalyzer() 
        central_ai = CentralAIEngine()
        message_broker = get_message_broker()
        
        print("   ✅ AI components: All initializations successful")
        return True
        
    except Exception as e:
        print(f"   ❌ AI components: Initialization failed - {e}")
        return False

def test_file_permissions():
    """Test file system permissions."""
    print("🔍 Testing file system permissions...")
    
    try:
        # Test write permission in logs directory
        log_dir = os.path.join(PROJECT_ROOT, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        test_file = os.path.join(log_dir, 'test_permissions.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        
        # Test read permission
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Cleanup
        os.remove(test_file)
        
        print("   ✅ File system: Read/write permissions OK")
        return True
        
    except Exception as e:
        print(f"   ❌ File system: Permission error - {e}")
        return False

def generate_system_report():
    """Generate comprehensive system report."""
    print("\n" + "="*60)
    print("📊 SYSTEM ENVIRONMENT REPORT")
    print("="*60)
    
    results = {
        'MongoDB': test_mongodb(),
        'RabbitMQ': test_rabbitmq(),
        'Angel One Config': test_angel_one_config(),
        'Angel One Connection': test_angel_one_connection(),
        'Python Dependencies': test_python_dependencies(),
        'AI Components': test_ai_components(),
        'File Permissions': test_file_permissions()
    }
    
    print(f"\n📋 SUMMARY:")
    passed = sum(results.values())
    total = len(results)
    
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {component}")
    
    print(f"\n🎯 OVERALL STATUS: {passed}/{total} components ready")
    
    if passed == total:
        print("🎉 SYSTEM READY FOR AI TESTING!")
        return True
    else:
        print("⚠️  SYSTEM NEEDS ATTENTION BEFORE TESTING")
        
        # Critical vs optional issues
        critical_issues = []
        if not results['MongoDB']:
            critical_issues.append("MongoDB")
        if not results['Python Dependencies']:
            critical_issues.append("Python Dependencies")
        if not results['AI Components']:
            critical_issues.append("AI Components")
        
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES (must fix): {', '.join(critical_issues)}")
        
        optional_issues = []
        if not results['RabbitMQ']:
            optional_issues.append("RabbitMQ (system works without)")
        if not results['Angel One Connection']:
            optional_issues.append("Angel One API (for live data)")
        
        if optional_issues:
            print(f"\n⚠️  OPTIONAL ISSUES: {', '.join(optional_issues)}")
        
        return False

def main():
    """Main environment testing function."""
    print("🧪 AI SYSTEM ENVIRONMENT TESTING")
    print("="*60)
    print("This script validates all dependencies and services")
    print("required for the AI trading system.\n")
    
    # Run comprehensive test
    success = generate_system_report()
    
    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n🚀 Ready to proceed with AI system testing!")
        print("\n📝 Next steps:")
        print("   1. Run basic AI tests: python server/src/ai/testing/test_ai_components.py")
        print("   2. Run integration tests: python server/src/ai/testing/integration_tests/test_full_system.py")
        print("   3. Run performance tests: python server/src/ai/testing/performance_tests/test_performance.py")
    else:
        print("\n🛠️  Please fix the issues above before proceeding with AI tests.")
    
    return success

if __name__ == '__main__':
    main()




