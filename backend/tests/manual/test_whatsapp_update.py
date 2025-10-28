"""
Test script to verify WhatsApp number updates for regular users vs super admins
"""
import os
from supabase import create_client

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def test_whatsapp_update():
    """Test WhatsApp number update with service role key"""

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("❌ Missing Supabase credentials")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get a regular user (not super admin)
    print("🔍 Looking for regular users...")
    users = supabase.table("users").select("*").neq("user_type", "super_admin").limit(1).execute()

    if not users.data:
        print("❌ No regular users found")
        return

    user = users.data[0]
    print(f"✅ Found regular user: {user.get('email')} (user_type: {user.get('user_type')})")
    print(f"   Current WhatsApp: {user.get('whatsapp_number')}")

    # Try to update WhatsApp number
    test_number = "+15551234567"
    print(f"\n📝 Attempting to update WhatsApp number to: {test_number}")

    try:
        response = supabase.table("users").update({
            "whatsapp_number": test_number
        }).eq("auth_user_id", user.get("auth_user_id")).execute()

        if response.data:
            print(f"✅ Update successful!")
            print(f"   New WhatsApp: {response.data[0].get('whatsapp_number')}")
        else:
            print(f"❌ Update failed - no data returned")
            print(f"   Response: {response}")
    except Exception as e:
        print(f"❌ Update failed with error: {e}")

    # Check RLS policies
    print("\n🔐 Checking RLS policies on users table...")
    try:
        # This query won't return the actual policies, but we can check if RLS is enabled
        print("   Note: Use Supabase dashboard to verify RLS policies")
        print("   Check if regular users can UPDATE whatsapp_number field")
    except Exception as e:
        print(f"   Error checking policies: {e}")

if __name__ == "__main__":
    test_whatsapp_update()
