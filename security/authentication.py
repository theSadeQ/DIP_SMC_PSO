#==========================================================================================\\\
#=============================== security/authentication.py ============================\\\
#==========================================================================================\\\
"""
Production-Grade Authentication and Authorization System
Secure access control for DIP control system to prevent unauthorized access.

SECURITY FEATURES:
- JWT token-based authentication
- Role-based access control (RBAC)
- Session management with timeout
- Secure password hashing
- Rate limiting for login attempts
"""

import jwt
import hashlib
import secrets
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta, timezone
import bcrypt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles with different permission levels"""
    ADMIN = "admin"           # Full system access
    OPERATOR = "operator"     # Control system operations
    MONITOR = "monitor"       # Read-only monitoring
    EMERGENCY = "emergency"   # Emergency shutdown only

class Permission(Enum):
    """System permissions"""
    CONTROL_WRITE = "control:write"       # Send control commands
    CONTROL_READ = "control:read"         # Read control status
    CONFIG_WRITE = "config:write"         # Modify configuration
    CONFIG_READ = "config:read"           # Read configuration
    MONITOR_READ = "monitor:read"         # Monitor system status
    EMERGENCY_STOP = "emergency:stop"     # Emergency shutdown
    USER_MANAGE = "user:manage"           # Manage users
    SYSTEM_ADMIN = "system:admin"         # Full system administration

@dataclass
class User:
    """User account data structure"""
    username: str
    password_hash: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    permissions: Set[Permission] = field(default_factory=set)

    def __post_init__(self):
        """Set default permissions based on role"""
        if not self.permissions:
            self.permissions = self._get_default_permissions()

    def _get_default_permissions(self) -> Set[Permission]:
        """Get default permissions for user role"""
        if self.role == UserRole.ADMIN:
            return set(Permission)  # All permissions
        elif self.role == UserRole.OPERATOR:
            return {
                Permission.CONTROL_WRITE, Permission.CONTROL_READ,
                Permission.CONFIG_READ, Permission.MONITOR_READ,
                Permission.EMERGENCY_STOP
            }
        elif self.role == UserRole.MONITOR:
            return {
                Permission.CONTROL_READ, Permission.CONFIG_READ,
                Permission.MONITOR_READ
            }
        elif self.role == UserRole.EMERGENCY:
            return {Permission.EMERGENCY_STOP, Permission.MONITOR_READ}
        else:
            return set()

@dataclass
class Session:
    """User session data structure"""
    token: str
    username: str
    role: UserRole
    permissions: Set[Permission]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime

class AuthenticationManager:
    """Secure authentication and authorization manager"""

    def __init__(self, secret_key: Optional[str] = None, session_timeout: int = 3600):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.session_timeout = session_timeout  # seconds
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.login_attempts: Dict[str, List[datetime]] = {}

        # Create default admin user
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user for initial setup"""
        default_password = "DIP_Admin_2025!"
        logger.warning("Creating default admin user. CHANGE PASSWORD IMMEDIATELY!")
        logger.warning(f"Default credentials - Username: admin, Password: {default_password}")

        self.create_user("admin", default_password, UserRole.ADMIN)

    def _hash_password(self, password: str) -> str:
        """Securely hash password using bcrypt"""
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    def create_user(self, username: str, password: str, role: UserRole) -> bool:
        """Create new user account"""
        try:
            if username in self.users:
                logger.error(f"User {username} already exists")
                return False

            if len(password) < 8:
                logger.error("Password must be at least 8 characters")
                return False

            password_hash = self._hash_password(password)
            user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                created_at=datetime.now(timezone.utc)
            )

            self.users[username] = user
            logger.info(f"Created user {username} with role {role.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return False

    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts"""
        user = self.users.get(username)
        if not user or not user.locked_until:
            return False

        if datetime.now(timezone.utc) > user.locked_until:
            # Unlock account
            user.locked_until = None
            user.failed_login_attempts = 0
            return False

        return True

    def _record_failed_login(self, username: str):
        """Record failed login attempt and lock if necessary"""
        user = self.users.get(username)
        if not user:
            return

        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            logger.warning(f"Account {username} locked for 15 minutes due to failed login attempts")

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return JWT token"""
        try:
            # Check if user exists
            user = self.users.get(username)
            if not user:
                logger.warning(f"Authentication failed: user {username} not found")
                return None

            # Check if account is locked
            if self._is_account_locked(username):
                logger.warning(f"Authentication failed: account {username} is locked")
                return None

            # Verify password
            if not self._verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password for {username}")
                self._record_failed_login(username)
                return None

            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now(timezone.utc)

            # Create session
            token = self._create_session(user)
            logger.info(f"User {username} authenticated successfully")
            return token

        except Exception as e:
            logger.error(f"Authentication error for {username}: {e}")
            return None

    def _create_session(self, user: User) -> str:
        """Create JWT session token"""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.session_timeout)

        payload = {
            'username': user.username,
            'role': user.role.value,
            'permissions': [p.value for p in user.permissions],
            'iat': now,
            'exp': expires_at
        }

        token = jwt.encode(payload, self.secret_key, algorithm='HS256')

        # Store session
        session = Session(
            token=token,
            username=user.username,
            role=user.role,
            permissions=user.permissions,
            created_at=now,
            expires_at=expires_at,
            last_activity=now
        )

        self.sessions[token] = session
        return token

    def validate_token(self, token: str) -> Optional[Session]:
        """Validate JWT token and return session"""
        try:
            # Check if session exists
            session = self.sessions.get(token)
            if not session:
                return None

            # Verify JWT
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])

            # Check expiration
            now = datetime.now(timezone.utc)
            if now > session.expires_at:
                self.logout(token)
                return None

            # Update last activity
            session.last_activity = now
            return session

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            self.logout(token)
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    def check_permission(self, token: str, required_permission: Permission) -> bool:
        """Check if user has required permission"""
        session = self.validate_token(token)
        if not session:
            return False

        return required_permission in session.permissions

    def logout(self, token: str) -> bool:
        """Logout user and invalidate token"""
        try:
            if token in self.sessions:
                username = self.sessions[token].username
                del self.sessions[token]
                logger.info(f"User {username} logged out")
                return True
            return False
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token for token, session in self.sessions.items()
            if now > session.expires_at
        ]

        for token in expired_tokens:
            del self.sessions[token]

        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")

# Global authentication manager instance
auth_manager = AuthenticationManager()

def require_permission(required_permission: Permission):
    """Decorator to require specific permission for function access"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract token from kwargs or first argument
            token = kwargs.get('token') or (args[0] if args else None)

            if not token or not auth_manager.check_permission(token, required_permission):
                raise PermissionError(f"Permission {required_permission.value} required")

            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_authentication(func):
    """Decorator to require valid authentication"""
    def wrapper(*args, **kwargs):
        # Extract token from kwargs or first argument
        token = kwargs.get('token') or (args[0] if args else None)

        if not token or not auth_manager.validate_token(token):
            raise PermissionError("Valid authentication required")

        return func(*args, **kwargs)
    return wrapper