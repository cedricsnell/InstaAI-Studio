#!/usr/bin/env python3
"""
InstaAI Studio - Interactive Setup Wizard
Guides you through collecting all credentials and generating .env file
"""

import os
import secrets
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(number, text):
    """Print a step number."""
    print(f"\n🔹 Step {number}: {text}")
    print("-" * 60)


def get_input(prompt, default="", required=True, secret=False):
    """Get user input with validation."""
    while True:
        if default:
            value = input(f"{prompt} [{default}]: ").strip() or default
        else:
            value = input(f"{prompt}: ").strip()

        if value or not required:
            return value

        if required:
            print("❌ This field is required. Please enter a value.")


def generate_secret_key():
    """Generate a secure random secret key."""
    return secrets.token_hex(32)


def main():
    print_header("InstaAI Studio - Enterprise Setup Wizard")
    print("This wizard will help you collect all credentials and generate your .env file.")
    print("\n📝 Have the following tabs open:")
    print("   - Supabase Dashboard: https://app.supabase.com")
    print("   - Upstash Console: https://console.upstash.com")
    print("   - Cloudflare R2: https://dash.cloudflare.com")
    print("   - Instagram Developers: https://developers.facebook.com/apps")

    proceed = input("\n✅ Ready to proceed? (yes/no): ").strip().lower()
    if proceed not in ['yes', 'y']:
        print("Setup cancelled. Run this script again when you're ready!")
        return

    config = {}

    # ============================================
    # 1. APPLICATION SETTINGS
    # ============================================
    print_step(1, "Application Settings")

    config['ENVIRONMENT'] = get_input(
        "Environment (development/staging/production)",
        default="development",
        required=False
    )

    config['API_BASE_URL'] = get_input(
        "API Base URL",
        default="http://localhost:8000",
        required=False
    )

    config['FRONTEND_URL'] = get_input(
        "Frontend URL",
        default="http://localhost:19006",
        required=False
    )

    # Generate secret key
    print("\n🔐 Generating secure SECRET_KEY...")
    config['SECRET_KEY'] = generate_secret_key()
    print(f"   Generated: {config['SECRET_KEY'][:20]}... (64 characters)")

    # ============================================
    # 2. SUPABASE (DATABASE)
    # ============================================
    print_step(2, "Supabase Database")
    print("📍 Location: Supabase Dashboard → Settings → Database")

    config['DATABASE_URL'] = get_input(
        "Database URL (Connection String - URI format)",
        default="postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres"
    )

    print("\n📍 Location: Supabase Dashboard → Settings → API")

    config['SUPABASE_URL'] = get_input(
        "Supabase Project URL",
        default="https://xxxxxxxxxxxx.supabase.co"
    )

    config['SUPABASE_ANON_KEY'] = get_input(
        "Supabase Anon Key (starts with eyJ...)"
    )

    config['SUPABASE_SERVICE_KEY'] = get_input(
        "Supabase Service Role Key (starts with eyJ...)"
    )

    # ============================================
    # 3. UPSTASH REDIS
    # ============================================
    print_step(3, "Upstash Redis")
    print("📍 Location: Upstash Console → Your Database → Details")

    config['REDIS_URL'] = get_input(
        "Redis URL (starts with rediss://)",
        default="rediss://default:[PASSWORD]@xxx.upstash.io:6379"
    )

    print("\n📍 Location: Upstash Console → REST API section")

    config['UPSTASH_REDIS_REST_URL'] = get_input(
        "Upstash REST URL",
        default="https://xxx.upstash.io"
    )

    config['UPSTASH_REDIS_REST_TOKEN'] = get_input(
        "Upstash REST Token (starts with AXXX...)"
    )

    # ============================================
    # 4. CLOUDFLARE R2
    # ============================================
    print_step(4, "Cloudflare R2 Storage")
    print("📍 Location: Cloudflare Dashboard → R2 → Manage R2 API Tokens")

    config['STORAGE_PROVIDER'] = 'r2'

    config['R2_ACCOUNT_ID'] = get_input(
        "Cloudflare Account ID (in R2 overview)"
    )

    config['R2_ACCESS_KEY_ID'] = get_input(
        "R2 Access Key ID"
    )

    config['R2_SECRET_ACCESS_KEY'] = get_input(
        "R2 Secret Access Key"
    )

    config['R2_BUCKET_NAME'] = get_input(
        "R2 Bucket Name",
        default="instaai-storage"
    )

    config['R2_PUBLIC_URL'] = get_input(
        "R2 Public URL",
        default=f"https://pub-{config['R2_ACCOUNT_ID'][:8]}.r2.dev",
        required=False
    )

    # ============================================
    # 5. CELERY (BACKGROUND JOBS)
    # ============================================
    print_step(5, "Celery Background Jobs")
    print("ℹ️  Using Redis as broker (configured above)")

    config['CELERY_BROKER_URL'] = config['REDIS_URL']
    config['CELERY_RESULT_BACKEND'] = config['REDIS_URL']
    config['CELERY_TASK_ALWAYS_EAGER'] = 'false'

    # ============================================
    # 6. INSTAGRAM API
    # ============================================
    print_step(6, "Instagram API")
    print("📍 Location: Facebook Developers → Your App → Settings → Basic")

    has_instagram = input("Have you created an Instagram/Facebook app yet? (yes/no): ").strip().lower()

    if has_instagram in ['yes', 'y']:
        config['INSTAGRAM_APP_ID'] = get_input("Facebook App ID")
        config['INSTAGRAM_APP_SECRET'] = get_input("Facebook App Secret")
        config['INSTAGRAM_REDIRECT_URI'] = get_input(
            "OAuth Redirect URI",
            default=f"{config['API_BASE_URL']}/api/oauth/callback"
        )
    else:
        print("\n⚠️  You'll need to create an Instagram app later.")
        print("   Follow Step 5 in SETUP-GUIDE.md")
        config['INSTAGRAM_APP_ID'] = 'YOUR_FACEBOOK_APP_ID_HERE'
        config['INSTAGRAM_APP_SECRET'] = 'YOUR_FACEBOOK_APP_SECRET_HERE'
        config['INSTAGRAM_REDIRECT_URI'] = f"{config['API_BASE_URL']}/api/oauth/callback"

    # ============================================
    # 7. AI SERVICES
    # ============================================
    print_step(7, "AI Services")

    has_anthropic = input("Do you have an Anthropic API key? (yes/no): ").strip().lower()
    if has_anthropic in ['yes', 'y']:
        config['ANTHROPIC_API_KEY'] = get_input(
            "Anthropic API Key (starts with sk-ant-...)"
        )
        config['AI_PROVIDER'] = 'anthropic'
    else:
        config['ANTHROPIC_API_KEY'] = 'sk-ant-your-key-here'

    has_openai = input("Do you have an OpenAI API key? (yes/no): ").strip().lower()
    if has_openai in ['yes', 'y']:
        config['OPENAI_API_KEY'] = get_input(
            "OpenAI API Key (starts with sk-...)"
        )
        if 'AI_PROVIDER' not in config:
            config['AI_PROVIDER'] = 'openai'
    else:
        config['OPENAI_API_KEY'] = 'sk-your-key-here'

    if 'AI_PROVIDER' not in config:
        config['AI_PROVIDER'] = 'anthropic'

    # ============================================
    # 8. MONITORING (OPTIONAL)
    # ============================================
    print_step(8, "Monitoring (Optional)")

    has_sentry = input("Do you have a Sentry DSN? (yes/no): ").strip().lower()
    if has_sentry in ['yes', 'y']:
        config['SENTRY_DSN'] = get_input(
            "Sentry DSN",
            required=False
        )
    else:
        print("ℹ️  You can add Sentry later for error tracking")
        config['SENTRY_DSN'] = ''

    # ============================================
    # GENERATE .ENV FILE
    # ============================================
    print_header("Generating .env File")

    env_content = f"""# InstaAI Studio - Enterprise Configuration
# Generated by setup-wizard.py on {os.popen('date').read().strip()}

# ====================
# APPLICATION SETTINGS
# ====================
ENVIRONMENT={config['ENVIRONMENT']}
API_BASE_URL={config['API_BASE_URL']}
FRONTEND_URL={config['FRONTEND_URL']}
SECRET_KEY={config['SECRET_KEY']}
LOG_LEVEL=INFO

# ====================
# DATABASE (Supabase)
# ====================
DATABASE_URL={config['DATABASE_URL']}
SUPABASE_URL={config['SUPABASE_URL']}
SUPABASE_ANON_KEY={config['SUPABASE_ANON_KEY']}
SUPABASE_SERVICE_KEY={config['SUPABASE_SERVICE_KEY']}

# ====================
# REDIS CACHE (Upstash)
# ====================
REDIS_URL={config['REDIS_URL']}
UPSTASH_REDIS_REST_URL={config['UPSTASH_REDIS_REST_URL']}
UPSTASH_REDIS_REST_TOKEN={config['UPSTASH_REDIS_REST_TOKEN']}

# ====================
# OBJECT STORAGE (Cloudflare R2)
# ====================
STORAGE_PROVIDER={config['STORAGE_PROVIDER']}
R2_ACCOUNT_ID={config['R2_ACCOUNT_ID']}
R2_ACCESS_KEY_ID={config['R2_ACCESS_KEY_ID']}
R2_SECRET_ACCESS_KEY={config['R2_SECRET_ACCESS_KEY']}
R2_BUCKET_NAME={config['R2_BUCKET_NAME']}
R2_PUBLIC_URL={config['R2_PUBLIC_URL']}

# ====================
# CELERY (Background Jobs)
# ====================
CELERY_BROKER_URL={config['CELERY_BROKER_URL']}
CELERY_RESULT_BACKEND={config['CELERY_RESULT_BACKEND']}
CELERY_TASK_ALWAYS_EAGER={config['CELERY_TASK_ALWAYS_EAGER']}

# ====================
# INSTAGRAM API
# ====================
INSTAGRAM_APP_ID={config['INSTAGRAM_APP_ID']}
INSTAGRAM_APP_SECRET={config['INSTAGRAM_APP_SECRET']}
INSTAGRAM_REDIRECT_URI={config['INSTAGRAM_REDIRECT_URI']}

# ====================
# AI SERVICES
# ====================
ANTHROPIC_API_KEY={config['ANTHROPIC_API_KEY']}
OPENAI_API_KEY={config['OPENAI_API_KEY']}
AI_PROVIDER={config['AI_PROVIDER']}

# ====================
# MONITORING
# ====================
SENTRY_DSN={config.get('SENTRY_DSN', '')}

# ====================
# CORS
# ====================
ALLOWED_ORIGINS={config['FRONTEND_URL']},http://localhost:3000
ALLOW_CREDENTIALS=true

# ====================
# DEVELOPMENT SETTINGS
# ====================
DEBUG=false
RELOAD=true
WORKERS=1
PORT=8000
"""

    # Save .env file
    env_path = Path(__file__).parent / '.env'

    if env_path.exists():
        backup = input(f"\n⚠️  .env file already exists. Create backup? (yes/no): ").strip().lower()
        if backup in ['yes', 'y']:
            backup_path = Path(__file__).parent / '.env.backup'
            env_path.rename(backup_path)
            print(f"✅ Backed up to: {backup_path}")

    env_path.write_text(env_content)

    print(f"\n✅ .env file created successfully!")
    print(f"📁 Location: {env_path}")

    # ============================================
    # NEXT STEPS
    # ============================================
    print_header("Next Steps")

    print("1. Review your .env file:")
    print(f"   code {env_path}")

    print("\n2. Install dependencies:")
    print("   pip install -r requirements.txt")

    print("\n3. Initialize database:")
    print("   alembic init alembic")
    print("   alembic revision --autogenerate -m 'Initial schema'")
    print("   alembic upgrade head")

    print("\n4. Test your setup:")
    print("   python test-config.py")

    print("\n5. Start the API:")
    print("   uvicorn src.api.main:app --reload")

    print("\n6. Deploy to Railway:")
    print("   - Push to GitHub: git push origin main")
    print("   - Railway will auto-deploy")
    print("   - Add environment variables in Railway dashboard")

    print("\n📚 For detailed instructions, see SETUP-GUIDE.md")

    print_header("Setup Complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("Please check your inputs and try again.")
