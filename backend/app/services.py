"""Capa de servicios: reglas de negocio y permisos (ADR 0003 y 0004)."""
import re
from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

from .auth import create_token
from .errors import Conflict, Forbidden, NotFound, Unauthorized, ValidationError
from .repositories import (NotificationRepository, ProjectRepository, TaskRepository,
                           TeamRepository, UserRepository)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATUSES = ("todo", "doing", "done")


def _text(data, field, label, max_len, required=True):
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{label} es obligatorio")
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"{label} debe ser texto")
    value = value.strip()
    if len(value) > max_len:
        raise ValidationError(f"{label} no puede superar {max_len} caracteres")
    return value


def _email(data):
    email = _text(data, "email", "El correo", 255).lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("El correo no es válido")
    return email


def _due_date(value):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValidationError("La fecha límite debe tener formato AAAA-MM-DD")


class Services:
    def __init__(self, db, jwt_secret, jwt_expires):
        self.db = db
        self.secret, self.expires = jwt_secret, jwt_expires
        self.users, self.teams = UserRepository(db), TeamRepository(db)
        self.projects, self.tasks = ProjectRepository(db), TaskRepository(db)
        self.notifications = NotificationRepository(db)

    # ---------- autenticación ----------
    def _auth_response(self, user):
        public = {"id": user["id"], "name": user["name"], "email": user["email"]}
        return {"token": create_token(user["id"], self.secret, self.expires), "user": public}

    def register(self, data):
        name = _text(data, "name", "El nombre", 80)
        email = _email(data)
        password = data.get("password")
        if not isinstance(password, str) or not 8 <= len(password) <= 128:
            raise ValidationError("La contraseña debe tener entre 8 y 128 caracteres")
        if self.users.by_email(email):
            raise Conflict("Ya existe una cuenta con ese correo")
        user_id = self.users.create(name, email, generate_password_hash(password))
        return self._auth_response({"id": user_id, "name": name, "email": email})

    def login(self, data):
        email = str(data.get("email", "")).strip().lower()
        user = self.users.by_email(email)
        if not user or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
            raise Unauthorized("Correo o contraseña incorrectos")
        return self._auth_response(user)

    def me(self, user_id):
        user = self.users.by_id(user_id)
        if not user:
            raise Unauthorized("La cuenta ya no existe")
        return user

    # ---------- permisos ----------
    def _role(self, user_id, team_id):
        if not self.teams.get(team_id):
            raise NotFound("Equipo no encontrado")
        role = self.teams.role(team_id, user_id)
        if role is None:
            raise Forbidden("No perteneces a este equipo")
        return role

    def _project(self, user_id, project_id):
        project = self.projects.get(project_id)
        if not project:
            raise NotFound("Proyecto no encontrado")
        return project, self._role(user_id, project["team_id"])

    def _task(self, user_id, task_id):
        task = self.tasks.get(task_id)
        if not task:
            raise NotFound("Tarea no encontrada")
        project, role = self._project(user_id, task["project_id"])
        return task, project, role

    # ---------- equipos e invitaciones ----------
    def create_team(self, user_id, data):
        team_id = self.teams.create(_text(data, "name", "El nombre del equipo", 80), user_id)
        return {**self.teams.get(team_id), "role": "owner"}

    def list_teams(self, user_id):
        return self.teams.for_user(user_id)

    def team_detail(self, user_id, team_id):
        role = self._role(user_id, team_id)
        return {**self.teams.get(team_id), "role": role, "members": self.teams.members(team_id)}

    def invite(self, user_id, team_id, data):
        if self._role(user_id, team_id) != "owner":
            raise Forbidden("Solo el propietario puede invitar")
        email = _email(data)
        invitee = self.users.by_email(email)
        if not invitee:
            raise NotFound("No existe un usuario registrado con ese correo")
        if self.teams.role(team_id, invitee["id"]):
            raise Conflict("Esa persona ya pertenece al equipo")
        if self.teams.pending_invitation(team_id, email):
            raise Conflict("Ya hay una invitación pendiente para ese correo")
        team = self.teams.get(team_id)
        inv_id = self.teams.create_invitation(team_id, email, user_id)
        self.notifications.create(invitee["id"], f"Te invitaron al equipo «{team['name']}»")
        return {"id": inv_id, "team_id": team_id, "email": email, "status": "pending"}

    def my_invitations(self, user_id):
        return self.teams.pending_for_email(self.me(user_id)["email"])

    def respond_invitation(self, user_id, invitation_id, accept):
        user = self.me(user_id)
        inv = self.teams.invitation(invitation_id)
        if not inv or inv["email"] != user["email"]:
            raise NotFound("Invitación no encontrada")
        if inv["status"] != "pending":
            raise Conflict("La invitación ya fue respondida")
        if accept:
            self.teams.add_member(inv["team_id"], user_id)
        self.teams.set_invitation_status(invitation_id, "accepted" if accept else "declined")
        verb = "aceptó" if accept else "rechazó"
        self.notifications.create(inv["invited_by"], f"{user['name']} {verb} unirse a «{inv['team_name']}»")
        return {"id": invitation_id, "status": "accepted" if accept else "declined"}

    # ---------- proyectos ----------
    def create_project(self, user_id, team_id, data):
        self._role(user_id, team_id)
        project_id = self.projects.create(team_id, _text(data, "name", "El nombre del proyecto", 100),
                                          _text(data, "description", "La descripción", 1000, required=False))
        return self.projects.get(project_id)

    def list_projects(self, user_id, team_id):
        self._role(user_id, team_id)
        return self.projects.for_team(team_id)

    def get_project(self, user_id, project_id):
        return self._project(user_id, project_id)[0]

    # ---------- tareas ----------
    def _check_assignee(self, team_id, assignee_id):
        if assignee_id is None:
            return None
        if not isinstance(assignee_id, int) or self.teams.role(team_id, assignee_id) is None:
            raise ValidationError("La persona asignada debe pertenecer al equipo")
        return assignee_id

    def _notify_assignment(self, actor_id, assignee_id, title):
        if assignee_id and assignee_id != actor_id:
            actor = self.users.by_id(actor_id)
            self.notifications.create(assignee_id, f"{actor['name']} te asignó la tarea «{title}»")

    def create_task(self, user_id, project_id, data):
        project, _ = self._project(user_id, project_id)
        title = _text(data, "title", "El título", 150)
        status = data.get("status", "todo")
        if status not in STATUSES:
            raise ValidationError("El estado debe ser todo, doing o done")
        assignee = self._check_assignee(project["team_id"], data.get("assignee_id"))
        task_id = self.tasks.create(project_id, title, _text(data, "description", "La descripción", 1000, False),
                                    status, assignee, _due_date(data.get("due_date")), user_id)
        self._notify_assignment(user_id, assignee, title)
        return self.tasks.get(task_id)

    def list_tasks(self, user_id, project_id, status=None):
        self._project(user_id, project_id)
        if status and status not in STATUSES:
            raise ValidationError("El estado debe ser todo, doing o done")
        return self.tasks.for_project(project_id, status)

    def update_task(self, user_id, task_id, data):
        task, project, _ = self._task(user_id, task_id)
        fields = {}
        if "title" in data:
            fields["title"] = _text(data, "title", "El título", 150)
        if "description" in data:
            fields["description"] = _text(data, "description", "La descripción", 1000, False)
        if "status" in data:
            if data["status"] not in STATUSES:
                raise ValidationError("El estado debe ser todo, doing o done")
            fields["status"] = data["status"]
        if "assignee_id" in data:
            fields["assignee_id"] = self._check_assignee(project["team_id"], data["assignee_id"])
        if "due_date" in data:
            fields["due_date"] = _due_date(data["due_date"])
        self.tasks.update(task_id, fields)
        if fields.get("assignee_id") and fields["assignee_id"] != task["assignee_id"]:
            self._notify_assignment(user_id, fields["assignee_id"], fields.get("title", task["title"]))
        return self.tasks.get(task_id)

    def delete_task(self, user_id, task_id):
        task, _, role = self._task(user_id, task_id)
        if role != "owner" and task["created_by"] != user_id:
            raise Forbidden("Solo el propietario del equipo o quien creó la tarea puede eliminarla")
        self.tasks.delete(task_id)

    # ---------- notificaciones ----------
    def list_notifications(self, user_id):
        items = [{**n, "is_read": bool(n["is_read"])} for n in self.notifications.for_user(user_id)]
        return {"items": items, "unread": self.notifications.unread_count(user_id)}

    def mark_notification(self, user_id, notification_id):
        note = self.notifications.get(notification_id)
        if not note or note["user_id"] != user_id:
            raise NotFound("Notificación no encontrada")
        self.notifications.mark_read(notification_id)

    def mark_all_notifications(self, user_id):
        self.notifications.mark_all_read(user_id)
