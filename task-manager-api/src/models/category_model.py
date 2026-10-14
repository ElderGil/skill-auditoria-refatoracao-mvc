import re

from sqlalchemy import func

from src.database import db
from src.models.task_model import Task
from src.utils.dates import now_utc


class Category(db.Model):
    __tablename__ = 'categories'

    DEFAULT_COLOR = '#000000'
    COLOR_PATTERN = re.compile(r'^#[0-9a-fA-F]{6}$')
    MAX_NAME_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 300

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=now_utc)

    # Sem cascade de exclusão: apagar a categoria anula o category_id das tasks.
    tasks = db.relationship('Task', back_populates='category')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'created_at': str(self.created_at),
        }

    @classmethod
    def get(cls, category_id):
        return db.session.get(cls, category_id)

    @classmethod
    def list_with_task_counts(cls):
        query = (db.select(cls, func.count(Task.id))
                 .outerjoin(Task, Task.category_id == cls.id)
                 .group_by(cls.id)
                 .order_by(cls.id))
        return db.session.execute(query).all()

    @classmethod
    def count(cls):
        return db.session.scalar(db.select(func.count(cls.id)))
