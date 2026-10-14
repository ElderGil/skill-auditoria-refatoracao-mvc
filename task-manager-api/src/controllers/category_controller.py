import logging

from src.database import db
from src.errors import NotFoundError
from src.models import Category
from src.utils import validators as v

logger = logging.getLogger(__name__)

CATEGORY_NOT_FOUND = 'Categoria não encontrada'


def _get_category(category_id):
    category = Category.get(category_id)
    if category is None:
        raise NotFoundError(CATEGORY_NOT_FOUND)
    return category


def _apply_fields(category, data):
    if 'name' in data:
        category.name = v.text(data['name'], required_message='Nome é obrigatório',
                               invalid_message='Nome deve ser texto',
                               max_len=Category.MAX_NAME_LENGTH, too_long_message='Nome muito longo')
    if 'description' in data:
        category.description = v.optional_text(data['description'], message='Descrição inválida',
                                               max_len=Category.MAX_DESCRIPTION_LENGTH)
    if 'color' in data:
        category.color = v.pattern(data['color'], Category.COLOR_PATTERN,
                                   message='Cor inválida. Use o formato #RRGGBB')


def list_categories():
    return [dict(category.to_dict(), task_count=task_count)
            for category, task_count in Category.list_with_task_counts()]


def create_category(data):
    v.require_object(data)
    category = Category(description='', color=Category.DEFAULT_COLOR)
    _apply_fields(category, dict(data, name=data.get('name')))
    db.session.add(category)
    db.session.commit()
    logger.info('categoria criada id=%s', category.id)
    return category.to_dict()


def update_category(category_id, data):
    category = _get_category(category_id)
    v.require_object(data, allow_empty=True)
    _apply_fields(category, data)
    db.session.commit()
    return category.to_dict()


def delete_category(category_id):
    category = _get_category(category_id)
    db.session.delete(category)  # o relacionamento anula o category_id das tasks
    db.session.commit()
    logger.info('categoria excluída id=%s', category_id)
    return {'message': 'Categoria deletada'}
