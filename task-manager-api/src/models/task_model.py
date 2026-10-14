from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from src.database import db
from src.utils.dates import utc_today, now_utc


class Task(db.Model):
    __tablename__ = 'tasks'

    STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
    CLOSED_STATUSES = ('done', 'cancelled')
    DEFAULT_STATUS = 'pending'
    MIN_PRIORITY = 1
    MAX_PRIORITY = 5
    DEFAULT_PRIORITY = 3
    HIGH_PRIORITY_THRESHOLD = 2
    MIN_TITLE_LENGTH = 3
    MAX_TITLE_LENGTH = 200
    DUE_DATE_FORMAT = '%Y-%m-%d'
    SUMMARY_FIELDS = ('id', 'title', 'description', 'status', 'priority', 'created_at', 'due_date')

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=DEFAULT_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=now_utc)
    updated_at = db.Column(db.DateTime, default=now_utc, onupdate=now_utc)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', back_populates='tasks')
    category = db.relationship('Category', back_populates='tasks')

    # --- regra de domínio ---

    def is_overdue(self, today=None):
        """Atrasada a partir do dia seguinte ao prazo; tasks concluídas ou canceladas nunca atrasam."""
        if not self.due_date or self.status in self.CLOSED_STATUSES:
            return False
        return self.due_date.date() < (today or utc_today())

    def days_overdue(self, today=None):
        return ((today or utc_today()) - self.due_date.date()).days

    def set_tags(self, tags):
        self.tags = ','.join(tags) if isinstance(tags, list) else tags

    # --- serialização ---

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    def to_detail_dict(self):
        data = self.to_dict()
        data['overdue'] = self.is_overdue()
        return data

    def to_list_dict(self):
        data = self.to_detail_dict()
        data['user_name'] = self.user.name if self.user else None
        data['category_name'] = self.category.name if self.category else None
        return data

    def to_summary_dict(self):
        data = {key: value for key, value in self.to_dict().items() if key in self.SUMMARY_FIELDS}
        data['overdue'] = self.is_overdue()
        return data

    # --- consultas ---

    @classmethod
    def get(cls, task_id):
        return db.session.get(cls, task_id)

    @classmethod
    def list_with_relations(cls):
        query = db.select(cls).options(selectinload(cls.user), selectinload(cls.category)).order_by(cls.id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def list_for_user(cls, user_id):
        return db.session.execute(db.select(cls).filter_by(user_id=user_id).order_by(cls.id)).scalars().all()

    @classmethod
    def search(cls, text=None, status=None, priority=None, user_id=None):
        query = db.select(cls)
        if text:
            query = query.where(or_(cls.title.contains(text, autoescape=True),
                                    cls.description.contains(text, autoescape=True)))
        if status:
            query = query.where(cls.status == status)
        if priority is not None:
            query = query.where(cls.priority == priority)
        if user_id is not None:
            query = query.where(cls.user_id == user_id)
        return db.session.execute(query.order_by(cls.id)).scalars().all()

    @classmethod
    def list_open_with_due_date(cls):
        query = db.select(cls).where(cls.due_date.is_not(None), cls.status.not_in(cls.CLOSED_STATUSES))
        return db.session.execute(query.order_by(cls.id)).scalars().all()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(func.count(cls.id)))

    @classmethod
    def count_by_status(cls):
        rows = db.session.execute(db.select(cls.status, func.count(cls.id)).group_by(cls.status)).all()
        counts = dict.fromkeys(cls.STATUSES, 0)
        counts.update({status: total for status, total in rows if status in counts})
        return counts

    @classmethod
    def count_by_priority(cls):
        rows = db.session.execute(db.select(cls.priority, func.count(cls.id)).group_by(cls.priority)).all()
        counts = dict.fromkeys(range(cls.MIN_PRIORITY, cls.MAX_PRIORITY + 1), 0)
        counts.update({priority: total for priority, total in rows if priority in counts})
        return counts

    @classmethod
    def count_status_by_user(cls):
        """{user_id: {status: total}} numa única consulta."""
        rows = db.session.execute(
            db.select(cls.user_id, cls.status, func.count(cls.id)).group_by(cls.user_id, cls.status)).all()
        result = {}
        for user_id, status, total in rows:
            result.setdefault(user_id, {})[status] = total
        return result

    @classmethod
    def count_created_since(cls, since):
        return db.session.scalar(db.select(func.count(cls.id)).where(cls.created_at >= since))

    @classmethod
    def count_done_updated_since(cls, since):
        return db.session.scalar(
            db.select(func.count(cls.id)).where(cls.status == 'done', cls.updated_at >= since))
