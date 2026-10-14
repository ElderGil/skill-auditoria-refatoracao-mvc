import logging

from sqlalchemy.exc import IntegrityError

from src.database import db
from src.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from src.models import Task, User
from src.utils import validators as v

logger = logging.getLogger(__name__)

USER_NOT_FOUND = 'Usuário não encontrado'
EMAIL_TAKEN = 'Email já cadastrado'


def _get_user(user_id):
    user = User.get(user_id)
    if user is None:
        raise NotFoundError(USER_NOT_FOUND)
    return user


def _name(value):
    return v.text(value, required_message='Nome é obrigatório', invalid_message='Nome deve ser texto',
                  max_len=User.MAX_NAME_LENGTH, too_long_message='Nome muito longo')


def _email(value):
    email = v.text(value, required_message='Email é obrigatório', invalid_message='Email inválido',
                   max_len=User.MAX_EMAIL_LENGTH, too_long_message='Email inválido')
    return v.pattern(email, User.EMAIL_PATTERN, message='Email inválido')


def _password(value, too_short_message):
    if value is None or value == '':
        raise ValidationError('Senha é obrigatória')
    if not isinstance(value, str):
        raise ValidationError('Senha inválida')
    if len(value) < User.MIN_PASSWORD_LENGTH:
        raise ValidationError(too_short_message)
    return value


def _require_admin(actor, message):
    if actor is None:
        raise UnauthorizedError('Autenticação necessária')
    if not actor.is_admin():
        raise ForbiddenError(message)


def _commit():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ConflictError(EMAIL_TAKEN) from None


def list_users():
    return [dict(user.to_dict(), task_count=task_count) for user, task_count in User.list_with_task_counts()]


def get_user(user_id):
    user = _get_user(user_id)
    data = user.to_dict()
    data['tasks'] = [task.to_dict() for task in Task.list_for_user(user_id)]
    return data


def list_user_tasks(user_id):
    _get_user(user_id)
    return [task.to_summary_dict() for task in Task.list_for_user(user_id)]


def create_user(data, actor):
    """Cadastro público cria role 'user'; outro role exige um administrador autenticado."""
    v.require_object(data)
    name = _name(data.get('name'))
    email = _email(data.get('email'))
    password = _password(data.get('password'), f'Senha deve ter no mínimo {User.MIN_PASSWORD_LENGTH} caracteres')
    role = v.choice(data.get('role', User.DEFAULT_ROLE), User.ROLES, message='Role inválido')
    if role != User.DEFAULT_ROLE:
        _require_admin(actor, 'Somente administradores podem definir o role')
    if User.email_taken(email):
        raise ConflictError(EMAIL_TAKEN)

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    _commit()
    logger.info('usuário criado id=%s', user.id)
    return user.to_dict()


def update_user(user_id, data, actor):
    """O próprio usuário altera nome, e-mail e senha; role e active só um administrador."""
    user = _get_user(user_id)
    if actor.id != user.id and not actor.is_admin():
        raise ForbiddenError('Sem permissão para alterar este usuário')
    v.require_object(data)
    if 'role' in data or 'active' in data:
        _require_admin(actor, 'Somente administradores podem alterar role ou active')

    if 'name' in data:
        user.name = _name(data['name'])
    if 'email' in data:
        email = _email(data['email'])
        if User.email_taken(email, exclude_id=user.id):
            raise ConflictError(EMAIL_TAKEN)
        user.email = email
    if 'password' in data:
        user.set_password(_password(data['password'], 'Senha muito curta'))
    if 'role' in data:
        user.role = v.choice(data['role'], User.ROLES, message='Role inválido')
    if 'active' in data:
        user.active = v.boolean(data['active'], message='Campo active deve ser true ou false')

    _commit()
    logger.info('usuário atualizado id=%s', user.id)
    return user.to_dict()


def delete_user(user_id):
    user = _get_user(user_id)
    db.session.delete(user)  # as tasks do usuário saem na mesma transação (cascade do model)
    db.session.commit()
    logger.info('usuário excluído id=%s', user_id)
    return {'message': 'Usuário deletado com sucesso'}
