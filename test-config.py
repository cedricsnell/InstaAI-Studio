#!/usr/bin/env python3
"""
InstaAI Studio - Configuration Test Script
Tests all service connections and validates setup
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def print_header(text):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_test(name, status, message=""):
    """Print test result."""
    icon = "✅" if status else "❌"
    print(f"{icon} {name:<40} {message}")


def test_database():
    """Test Supabase PostgreSQL connection."""
    print("\n🔍 Testing Database Connection...")
    try:
        from sqlalchemy import create_engine, text

        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print_test("Database URL", False, "Not configured")
            return False

        engine = create_engine(db_url, pool_pre_ping=True)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]

        print_test("Database Connection", True, "Connected")
        print(f"   PostgreSQL Version: {version[:50]}...")
        return True

    except Exception as e:
        print_test("Database Connection", False, str(e)[:60])
        return False


def test_redis():
    """Test Upstash Redis connection."""
    print("\n🔍 Testing Redis Connection...")
    try:
        import redis

        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            print_test("Redis URL", False, "Not configured")
            return False

        r = redis.from_url(redis_url, socket_timeout=5)
        r.ping()

        # Test set/get
        r.set('test_key', 'test_value', ex=10)
        value = r.get('test_key')
        r.delete('test_key')

        print_test("Redis Connection", True, "Connected")
        print_test("Redis Operations", value == b'test_value', "Set/Get works")
        return True

    except Exception as e:
        print_test("Redis Connection", False, str(e)[:60])
        return False


def test_storage():
    """Test cloud storage configuration."""
    print("\n🔍 Testing Cloud Storage...")
    try:
        from src.storage.cloud_storage import get_storage

        storage = get_storage()
        provider = storage.provider.value

        print_test("Storage Provider", True, f"Using: {provider}")

        if provider == 'r2':
            r2_account = os.getenv('R2_ACCOUNT_ID')
            r2_bucket = os.getenv('R2_BUCKET_NAME')
            print(f"   Account: {r2_account}")
            print(f"   Bucket: {r2_bucket}")

        elif provider == 'supabase':
            supabase_url = os.getenv('SUPABASE_URL')
            print(f"   URL: {supabase_url}")

        return True

    except Exception as e:
        print_test("Storage Configuration", False, str(e)[:60])
        return False


def test_instagram_api():
    """Test Instagram API configuration."""
    print("\n🔍 Testing Instagram API Config...")

    app_id = os.getenv('INSTAGRAM_APP_ID')
    app_secret = os.getenv('INSTAGRAM_APP_SECRET')
    redirect_uri = os.getenv('INSTAGRAM_REDIRECT_URI')

    if not app_id or app_id == 'YOUR_FACEBOOK_APP_ID_HERE':
        print_test("Instagram App ID", False, "Not configured")
        return False

    if not app_secret or app_secret == 'YOUR_FACEBOOK_APP_SECRET_HERE':
        print_test("Instagram App Secret", False, "Not configured")
        return False

    print_test("Instagram App ID", True, app_id)
    print_test("Instagram App Secret", True, f"{app_secret[:10]}...")
    print_test("Redirect URI", bool(redirect_uri), redirect_uri)

    return True


def test_ai_services():
    """Test AI service configuration."""
    print("\n🔍 Testing AI Services...")

    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    ai_provider = os.getenv('AI_PROVIDER', 'anthropic')

    has_anthropic = anthropic_key and anthropic_key.startswith('sk-ant-')
    has_openai = openai_key and openai_key.startswith('sk-')

    print_test("Anthropic API Key", has_anthropic,
               f"{anthropic_key[:15]}..." if has_anthropic else "Not configured")
    print_test("OpenAI API Key", has_openai,
               f"{openai_key[:15]}..." if has_openai else "Not configured")
    print_test("Active AI Provider", True, ai_provider)

    if ai_provider == 'anthropic' and not has_anthropic:
        print("   ⚠️  Anthropic selected but key not configured")
        return False

    if ai_provider == 'openai' and not has_openai:
        print("   ⚠️  OpenAI selected but key not configured")
        return False

    return True


def test_environment():
    """Test general environment configuration."""
    print("\n🔍 Testing Environment Configuration...")

    env = os.getenv('ENVIRONMENT', 'development')
    api_url = os.getenv('API_BASE_URL', 'http://localhost:8000')
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:19006')
    secret_key = os.getenv('SECRET_KEY')

    print_test("Environment", True, env)
    print_test("API Base URL", bool(api_url), api_url)
    print_test("Frontend URL", bool(frontend_url), frontend_url)
    print_test("Secret Key", bool(secret_key and len(secret_key) >= 32),
               f"{len(secret_key) if secret_key else 0} characters")

    if not secret_key or len(secret_key) < 32:
        print("   ⚠️  Secret key should be at least 32 characters")
        return False

    return True


def test_monitoring():
    """Test monitoring service configuration."""
    print("\n🔍 Testing Monitoring Services...")

    sentry_dsn = os.getenv('SENTRY_DSN')

    if sentry_dsn and sentry_dsn.startswith('https://'):
        print_test("Sentry DSN", True, "Configured")
    else:
        print_test("Sentry DSN", False, "Not configured (optional)")

    return True


def check_dependencies():
    """Check if all required packages are installed."""
    print("\n🔍 Checking Dependencies...")

    required_packages = {
        'sqlalchemy': 'Database ORM',
        'psycopg2': 'PostgreSQL driver',
        'redis': 'Redis client',
        'boto3': 'S3/R2 client',
        'fastapi': 'Web framework',
        'uvicorn': 'ASGI server',
        'alembic': 'Database migrations',
        'celery': 'Background jobs',
        'anthropic': 'AI service',
    }

    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print_test(f"{package:<20}", True, description)
        except ImportError:
            print_test(f"{package:<20}", False, f"MISSING - {description}")
            missing.append(package)

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False

    return True


def main():
    """Run all configuration tests."""
    print_header("InstaAI Studio - Configuration Test")

    print("Testing your enterprise infrastructure setup...")
    print(f"Environment file: {os.path.join(os.getcwd(), '.env')}")

    if not os.path.exists('.env'):
        print("\n❌ .env file not found!")
        print("\nRun the setup wizard:")
        print("   python setup-wizard.py")
        sys.exit(1)

    results = {}

    # Run all tests
    results['dependencies'] = check_dependencies()
    results['environment'] = test_environment()
    results['database'] = test_database()
    results['redis'] = test_redis()
    results['storage'] = test_storage()
    results['instagram'] = test_instagram_api()
    results['ai'] = test_ai_services()
    results['monitoring'] = test_monitoring()

    # Summary
    print_header("Test Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name.capitalize():<20} {'PASS' if result else 'FAIL'}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Your configuration is ready.")
        print("\nNext steps:")
        print("1. Initialize database: alembic upgrade head")
        print("2. Start API: uvicorn src.api.main:app --reload")
        print("3. Visit: http://localhost:8000/health")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nRefer to SETUP-GUIDE.md for detailed instructions.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
