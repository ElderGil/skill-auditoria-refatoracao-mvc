import hashlib
import hmac
import re

from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from src.database import db
from src.models.task_model import Task
from src.utils.dates import now_utc

_LEGACY_MD5 = re.compile(r'[0-9a-f]{32}')


class User(db.Model):
    __tablename__ = 'users'

    ROLES = ('user', 'admin', 'manager')
    DEFAULT_ROLE = 'user'
    ADMIN_ROLE = 'admin'
    MIN_PASSWORD_LENGTH = 4
    MAX_NAME_LENGTH = 100
    MAX_EMAIL_LENGTH = 150
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now_utc)

    tasks = db.relationship('Task', back_populates='user', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if self.has_legacy_password_hash():
            # Hash MD5 gravado pela versão anterior: aceito só para migrar no próximo login.
            legacy = hashlib.md5(raw_password.encode(), usedforsecurity=False).hexdigest()
            return hmac.compare_digest(legacy, self.password)
        return check_password_hash(self.password, raw_password)

    def has_legacy_password_hash(self):
        return bool(self.password and _LEGACY_MD5.fullmatch(self.password))

    def is_admin(self):
        return self.role == self.ADMIN_ROLE

    @classmethod
    def get(cls, user_id):
        return db.session.get(cls, user_id)

    @classmethod
    def get_by_email(cls, email):
        return db.session.execute(db.select(cls).filter_by(email=email)).scalar_one_or_none()

    @classmethod
    def email_taken(cls, email, exclude_id=None):
        existing = cls.get_by_email(email)
        return existing is not None and existing.id != exclude_id

    @classmethod
    def list_all(cls):
        return db.session.execute(db.select(cls).order_by(cls.id)).scalars().all()

    @classmethod
    def list_with_task_counts(cls):
        query = (db.select(cls, func.count(Task.id))
                 .outerjoin(Task, Task.user_id == cls.id)
                 .group_by(cls.id)
                 .order_by(cls.id))
        return db.session.execute(query).all()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(func.count(cls.id)))
