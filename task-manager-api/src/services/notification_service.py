"""Envio de e-mail. Ainda não é chamado por nenhum fluxo (ver melhorias propostas)."""
import logging
import smtplib

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, host, port, user, password):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    @classmethod
    def from_config(cls, config):
        return cls(config['SMTP_HOST'], config['SMTP_PORT'], config['SMTP_USER'], config['SMTP_PASSWORD'])

    def send_email(self, to, subject, body):
        if not self.host:
            logger.warning('SMTP não configurado; e-mail não enviado')
            return False
        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, to, f"Subject: {subject}\n\n{body}")
        except (smtplib.SMTPException, OSError):
            logger.exception('falha ao enviar e-mail')
            return False
        logger.info('e-mail enviado')
        return True

    def notify_task_assigned(self, user, task):
        subject = f"Nova task atribuída: {task.title}"
        body = (f"Olá {user.name},\n\nA task '{task.title}' foi atribuída a você.\n\n"
                f"Prioridade: {task.priority}\nStatus: {task.status}")
        return self.send_email(user.email, subject, body)

    def notify_task_overdue(self, user, task):
        subject = f"Task atrasada: {task.title}"
        body = f"Olá {user.name},\n\nA task '{task.title}' está atrasada!\n\nData limite: {task.due_date}"
        return self.send_email(user.email, subject, body)
