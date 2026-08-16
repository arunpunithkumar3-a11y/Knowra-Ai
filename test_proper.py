import pytest
import pytest_asyncio
from uuid import UUID
from datetime import datetime, timezone, timedelta

from src.core.main import get_session, async_session_maker
from src.models.auth_schemas import UserSignup, UserUpdate
from src.models.org_schemas import OrgCreate, OrgUpdate
from src.services.user import UserService
from src.services.org import OrgService
from src.core.password import verify_password, create_hash_password as hash_password
from src.core.security import create_access_token, decode_access_token
from fastapi import HTTPException
from src.config import configure
import jwt
from sqlalchemy import delete, select
from src.models.database import User, Org, OrgMember, JoinRequest, Document, Chat, UserRole


class TestUserService:
    @pytest_asyncio.fixture
    async def session(self):
        async for s in get_session():
            yield s
    
    @pytest_asyncio.fixture
    async def user_service(self, session):
        return UserService(session)
    
    @pytest_asyncio.fixture
    async def org_service(self, session):
        return OrgService(session)
    
    @pytest_asyncio.fixture
    async def test_user(self, user_service):
        """Create or get test user"""
        user = await user_service.get_user_by_email("test@example.com")
        if not user:
            user = await user_service.create_user(UserSignup(
                email="test@example.com",
                password="testpassword123",
                user_name="testuser",
                role="member",
            ))
        return user
    
    @pytest_asyncio.fixture
    async def cleanup_user(self, user_service):
        """Clean up test user after test"""
        yield
        user = await user_service.get_user_by_email("newuser@example.com")
        if user:
            await user_service.delete_user(user.uid)
    
    @pytest_asyncio.fixture
    async def cleanup_delete_user(self, user_service):
        """Clean up user created for deletion test"""
        yield
        user = await user_service.get_user_by_email("todelete@example.com")
        if user:
            await user_service.delete_user(user.uid)

    async def test_create_user(self, user_service, cleanup_user):
        user = await user_service.create_user(UserSignup(
            email="newuser@example.com",
            password="password123",
            user_name="newuser",
            role="member",
        ))
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.user_name == "newuser"
        assert user.role == "member"
        # Password should be hashed
        assert user.password_hash != "password123"
        assert verify_password("password123", user.password_hash)
    
    async def test_get_user_by_email(self, user_service, test_user):
        user = await user_service.get_user_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"
        assert user.uid == test_user.uid
    
    async def test_get_user_by_id(self, user_service, test_user):
        user = await user_service.get_user_by_id(test_user.uid)
        assert user is not None
        assert user.uid == test_user.uid
    
    async def test_duplicate_user_raises_conflict(self, user_service, test_user):
        with pytest.raises(HTTPException) as exc_info:
            await user_service.create_user(UserSignup(
                email="test@example.com",
                password="password123",
                user_name="anotheruser",
                role="member",
            ))
        assert exc_info.value.status_code == 403
    
    async def test_update_user(self, user_service, test_user):
        # Get the user first
        user = await user_service.get_user_by_id(test_user.uid)
        assert user is not None
        
        updated = await user_service.update_user(UserUpdate(
            user_name="updatedname",
            role=UserRole.admin
        ), user)
        assert updated.user_name == "updatedname"
        assert updated.role == UserRole.admin
    
    async def test_delete_user(self, user_service, cleanup_delete_user):
        # Create a user to delete
        user = await user_service.create_user(UserSignup(
            email="todelete@example.com",
            password="password123",
            user_name="todelete",
            role="member",
        ))
        deleted = await user_service.delete_user(user.uid)
        assert deleted is not None
        # Verify it's gone
        assert await user_service.get_user_by_id(user.uid) is None


class TestOrgService:
    @pytest_asyncio.fixture
    async def session(self):
        async for s in get_session():
            yield s
    
    @pytest_asyncio.fixture
    async def user_service(self, session):
        return UserService(session)
    
    @pytest_asyncio.fixture
    async def org_service(self, session):
        return OrgService(session)
    
    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self, session, user_service):
        """Clean up test data before and after each test"""
        # Clean up before test
        test_emails = ["orgtest@example.com"]
        test_org_names = ["Test Organization", "Get By ID Org", "Org 1", "Org 2", "Original", "To Delete"]
        test_users = await session.execute(
            select(User).where(User.email.in_(test_emails))
        )
        users = test_users.scalars().all()
        for user in users:
            # Delete orgs for this user
            await session.execute(delete(Org).where(Org.user_id == user.uid))
            await session.execute(delete(OrgMember).where(OrgMember.user_id == user.uid))
            await session.execute(delete(JoinRequest).where(JoinRequest.user_id == user.uid))
        await session.execute(delete(User).where(User.email.in_(test_emails)))
        await session.commit()
        yield
        # Clean up after test
        test_users = await session.execute(
            select(User).where(User.email.in_(test_emails))
        )
        users = test_users.scalars().all()
        for user in users:
            await session.execute(delete(Org).where(Org.user_id == user.uid))
            await session.execute(delete(OrgMember).where(OrgMember.user_id == user.uid))
            await session.execute(delete(JoinRequest).where(JoinRequest.user_id == user.uid))
        await session.execute(delete(User).where(User.email.in_(test_emails)))
        await session.commit()

    @pytest_asyncio.fixture
    async def test_user(self, user_service):
        user = await user_service.get_user_by_email("orgtest@example.com")
        if not user:
            user = await user_service.create_user(UserSignup(
                email="orgtest@example.com",
                password="password123",
                user_name="orgtestuser",
                role="member",
            ))
        return user
    
    async def test_create_org(self, org_service, test_user):
        org = await org_service.create_org(OrgCreate(
            org_name="Test Organization",
            description="A test org"
        ), test_user.uid)
        assert org is not None
        assert org.org_name == "Test Organization"
        assert org.description == "A test org"
        assert org.user_id == test_user.uid
    
    async def test_get_org_by_id(self, org_service, test_user):
        org = await org_service.create_org(OrgCreate(
            org_name="Get By ID Org",
            description="Test"
        ), test_user.uid)
        found = await org_service.get_org_by_id(org.uid)
        assert found is not None
        assert found.uid == org.uid
    
    async def test_get_orgs_by_user(self, org_service, test_user):
        await org_service.create_org(OrgCreate(org_name="Org 1", description="1"), test_user.uid)
        await org_service.create_org(OrgCreate(org_name="Org 2", description="2"), test_user.uid)
        orgs = await org_service.get_orgs_by_user(test_user.uid)
        assert len(orgs) >= 2
    
    async def test_update_org(self, org_service, test_user):
        org = await org_service.create_org(OrgCreate(org_name="Original", description="Orig"), test_user.uid)
        updated = await org_service.update_org(org.uid, OrgUpdate(
            org_name="Updated",
            description="Updated desc"
        ))
        assert updated.org_name == "Updated"
        assert updated.description == "Updated desc"
    
    async def test_delete_org(self, org_service, test_user):
        org = await org_service.create_org(OrgCreate(org_name="To Delete", description="Del"), test_user.uid)
        deleted = await org_service.delete_org(org.uid)
        assert deleted is not None
        assert await org_service.get_org_by_id(org.uid) is None


class TestAuth:
    @pytest_asyncio.fixture
    async def session(self):
        async for s in get_session():
            yield s
    
    @pytest_asyncio.fixture
    async def user_service(self, session):
        return UserService(session)
    
    @pytest_asyncio.fixture
    async def test_user(self, user_service):
        user = await user_service.get_user_by_email("authtest@example.com")
        if not user:
            user = await user_service.create_user(UserSignup(
                email="authtest@example.com",
                password="authtestpass",
                user_name="authtest",
                role="member",
            ))
        return user
    
    def test_hash_password(self):
        password = "testpassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong", hashed)
    
    async def test_create_and_decode_token(self, test_user):
        token = create_access_token({"user_id": str(test_user.uid)})
        assert token is not None
        assert isinstance(token, str)
        
        payload = decode_access_token(token)
        assert payload["user_data"]["user_id"] == str(test_user.uid)
    
    def test_expired_token_raises(self):
        from datetime import datetime, timedelta
        
        expired_token = jwt.encode(
            {"user_data": {"user_id": "test"}, "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            configure.JWT_SECRET,
            algorithm=configure.JWT_ALGORITHM
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(expired_token)
        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()
    
    def test_invalid_token_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("invalid.token.here")
        assert exc_info.value.status_code == 401
        assert "invalid" in str(exc_info.value.detail).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])