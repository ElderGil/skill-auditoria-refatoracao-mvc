import logging

from src.database import db
from src.errors import NotFoundError, ValidationError
from src.models import Category, Task, User
from src.utils import validators as v
from src.utils.dates import now_utc
from src.utils.stats import percentage

logger = logging.getLogger(__name__)

TASK_NOT_FOUND = 'Task não encontrada'
PRIORITY_MESSAGE = f'Prioridade deve ser entre {Task.MIN_PRIORITY} e {Task.MAX_PRIORITY}'
DUE_DATE_MESSAGE = 'Formato de data inválido. Use YYYY-MM-DD'


def _get_task(task_id):
    task = Task.get(task_id)
    if task is None:
        raise NotFoundError(TASK_NOT_FOUND)
    return task


def _existing_id(value, model, field, not_found_message):
    entity_id = v.optional_id(value, message=f'{field} inválido')
    if entity_id is not None and model.get(entity_id) is None:
        raise NotFoundError(not_found_message)
    return entity_id


def _apply_fields(task, data):
    """Valida e aplica os campos presentes. Criar e atualizar passam por aqui."""
    if 'title' in data:
        task.title = v.text(data['title'], required_message='Título é obrigatório',
                            invalid_message='Título deve ser texto',
                            min_len=Task.MIN_TITLE_LENGTH, max_len=Task.MAX_TITLE_LENGTH,
                            too_short_message='Título muito curto', too_long_message='Título muito longo')
    if 'description' in data:
        task.description = v.optional_text(data['description'], message='Descrição deve ser texto')
    if 'status' in data:
        task.status = v.choice(data['status'], Task.STATUSES, message='Status inválido')
    if 'priority' in data:
        task.priority = v.integer(data['priority'], message=PRIORITY_MESSAGE,
                                  minimum=Task.MIN_PRIORITY, maximum=Task.MAX_PRIORITY)
    if 'user_id' in data:
        task.user_id = _existing_id(data['user_id'], User, 'user_id', 'Usuário não encontrado')
    if 'category_id' in data:
        task.category_id = _existing_id(data['category_id'], Category, 'category_id', 'Categoria não encontrada')
    if 'due_date' in data:
        task.due_date = (v.date(data['due_date'], Task.DUE_DATE_FORMAT, message=DUE_DATE_MESSAGE)
                         if data['due_date'] else None)
    if 'tags' in data:
        task.set_tags(v.string_list_or_text(data['tags'], message='Tags devem ser texto ou lista de textos'))


def list_tasks():
    return [task.to_list_dict() for task in Task.list_with_relations()]


def get_task(task_id):
    return _get_task(task_id).to_detail_dict()


def create_task(data):
    v.require_object(data)
    if 'title' not in data:
        raise ValidationError('Título é obrigatório')
    task = Task(description='', status=Task.DEFAULT_STATUS, priority=Task.DEFAULT_PRIORITY)
    _apply_fields(task, data)
    db.session.add(task)
    db.session.commit()
    logger.info('task criada id=%s', task.id)
    return task.to_dict()


def update_task(task_id, data):
    task = _get_task(task_id)
    v.require_object(data)
    _apply_fields(task, data)
    task.updated_at = now_utc()
    db.session.commit()
    logger.info('task atualizada id=%s', task.id)
    return task.to_dict()


def delete_task(task_id):
    task = _get_task(task_id)
    db.session.delete(task)
    db.session.commit()
    logger.info('task excluída id=%s', task_id)
    return {'message': 'Task deletada com sucesso'}


def search_tasks(text, status, priority, user_id):
    tasks = Task.search(
        text=text,
        status=status,
        priority=v.query_int(priority, message='Parâmetro priority deve ser um número inteiro'),
        user_id=v.query_int(user_id, message='Parâmetro user_id deve ser um número inteiro'),
    )
    return [task.to_dict() for task in tasks]


def task_stats():
    total = Task.count()
    by_status = Task.count_by_status()
    overdue = sum(1 for task in Task.list_open_with_due_date() if task.is_overdue())
    return {
        'total': total,
        'pending': by_status['pending'],
        'in_progress': by_status['in_progress'],
        'done': by_status['done'],
        'cancelled': by_status['cancelled'],
        'overdue': overdue,
        'completion_rate': percentage(by_status['done'], total),
    }
