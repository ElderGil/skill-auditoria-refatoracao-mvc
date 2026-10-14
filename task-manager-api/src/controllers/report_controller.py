from datetime import timedelta

from src.errors import NotFoundError
from src.models import Category, Task, User
from src.utils.dates import utc_today, now_utc
from src.utils.stats import percentage

RECENT_DAYS = 7
PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}


def summary_report():
    today = utc_today()
    overdue_tasks = [task for task in Task.list_open_with_due_date() if task.is_overdue(today)]
    since = now_utc() - timedelta(days=RECENT_DAYS)
    by_status = Task.count_by_status()
    by_priority = Task.count_by_priority()
    status_by_user = Task.count_status_by_user()

    user_productivity = []
    for user in User.list_all():
        counts = status_by_user.get(user.id, {})
        total = sum(counts.values())
        completed = counts.get('done', 0)
        user_productivity.append({
            'user_id': user.id,
            'user_name': user.name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': percentage(completed, total),
        })

    return {
        'generated_at': str(now_utc()),
        'overview': {
            'total_tasks': Task.count(),
            'total_users': User.count(),
            'total_categories': Category.count(),
        },
        'tasks_by_status': {status: by_status[status] for status in Task.STATUSES},
        'tasks_by_priority': {label: by_priority[priority] for priority, label in PRIORITY_LABELS.items()},
        'overdue': {
            'count': len(overdue_tasks),
            'tasks': [{
                'id': task.id,
                'title': task.title,
                'due_date': str(task.due_date),
                'days_overdue': task.days_overdue(today),
            } for task in overdue_tasks],
        },
        'recent_activity': {
            'tasks_created_last_7_days': Task.count_created_since(since),
            'tasks_completed_last_7_days': Task.count_done_updated_since(since),
        },
        'user_productivity': user_productivity,
    }


def user_report(user_id):
    user = User.get(user_id)
    if user is None:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.list_for_user(user_id)
    today = utc_today()
    counts = dict.fromkeys(Task.STATUSES, 0)
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1
    total = len(tasks)

    return {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': {
            'total_tasks': total,
            'done': counts['done'],
            'pending': counts['pending'],
            'in_progress': counts['in_progress'],
            'cancelled': counts['cancelled'],
            'overdue': sum(1 for task in tasks if task.is_overdue(today)),
            'high_priority': sum(1 for task in tasks if task.priority <= Task.HIGH_PRIORITY_THRESHOLD),
            'completion_rate': percentage(counts['done'], total),
        },
    }
