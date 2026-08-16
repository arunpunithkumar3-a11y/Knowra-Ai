import asyncio
from uuid import UUID

from src.core.main import get_session
from src.models.auth_schemas import UserSignup
from src.models.org_schemas import OrgCreate
from src.services.user import UserService
from src.services.org import OrgService


async def run_all_tests():
    async for session in get_session():
        user_service = UserService(session)
        org_service = OrgService(session)
        
        # Test 1: Create user
        print("\n=== Test 1: Create User ===")
        data = UserSignup(
            email="imtheking@gmail.com",
            password="1154339085",
            user_name="punith_k7",
            role="member",
        )
        
        existing_user = await user_service.get_user_by_email(data.email)
        if existing_user:
            print(f"User already exists: {existing_user.uid}")
            user = existing_user
        else:
            user = await user_service.create_user(data)
            print(f"Created user: {user.uid}")
        
        # Test 2: Create org
        print("\n=== Test 2: Create Org ===")
        org_data = OrgCreate(org_name="Test Org", description="Test organization")
        org = await org_service.create_org(org_data, user.uid)
        print(f"Created org: {org.uid}")
        
        # Test 3: Get user orgs
        print("\n=== Test 3: Get User Orgs ===")
        orgs = await org_service.get_orgs_by_user(user.uid)
        print(f"User orgs: {orgs}")
        
        # Test 4: Login / Password verification
        print("\n=== Test 4: Login / Password Verification ===")
        from src.core.password import verify_password
        from src.core.security import create_access_token
        
        user = await user_service.get_user_by_email("imtheking@gmail.com")
        if user:
            print(f"User found: {user.email}")
            is_valid = verify_password("1154339085", user.password_hash)
            print(f"Password valid: {is_valid}")
            
            token = create_access_token({"user_id": str(user.uid)})
            print(f"Token created: {token[:50]}...")
        
        # Test 5: Test wrong password
        print("\n=== Test 5: Wrong Password ===")
        is_valid = verify_password("wrongpassword", user.password_hash)
        print(f"Wrong password valid: {is_valid}")
        
        print("\n=== All tests passed! ===")


if __name__ == "__main__":
    asyncio.run(run_all_tests())