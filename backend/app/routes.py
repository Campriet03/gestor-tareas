"""Rutas y controladores HTTP: validan la forma de la petición y delegan en Services."""
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from .auth import decode_token
from .errors import Unauthorized, ValidationError

api = Blueprint("api", __name__, url_prefix="/api/v1")


def services():
    return current_app.extensions["services"]


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("El cuerpo debe ser un objeto JSON")
    return data


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise Unauthorized("Falta el token de autenticación")
        g.user_id = decode_token(header[7:], current_app.config["JWT_SECRET"])
        return view(*args, **kwargs)
    return wrapper


@api.get("/health")
def health():
    services().db.query("SELECT 1 AS ok")
    return jsonify({"status": "ok"})


@api.post("/auth/register")
def register():
    return jsonify(services().register(body())), 201


@api.post("/auth/login")
def login():
    return jsonify(services().login(body()))


@api.get("/auth/me")
@login_required
def me():
    return jsonify(services().me(g.user_id))


@api.get("/teams")
@login_required
def list_teams():
    return jsonify(services().list_teams(g.user_id))


@api.post("/teams")
@login_required
def create_team():
    return jsonify(services().create_team(g.user_id, body())), 201


@api.get("/teams/<int:team_id>")
@login_required
def team_detail(team_id):
    return jsonify(services().team_detail(g.user_id, team_id))


@api.post("/teams/<int:team_id>/invitations")
@login_required
def invite(team_id):
    return jsonify(services().invite(g.user_id, team_id, body())), 201


@api.get("/invitations")
@login_required
def my_invitations():
    return jsonify(services().my_invitations(g.user_id))


@api.post("/invitations/<int:invitation_id>/accept")
@login_required
def accept_invitation(invitation_id):
    return jsonify(services().respond_invitation(g.user_id, invitation_id, True))


@api.post("/invitations/<int:invitation_id>/decline")
@login_required
def decline_invitation(invitation_id):
    return jsonify(services().respond_invitation(g.user_id, invitation_id, False))


@api.get("/teams/<int:team_id>/projects")
@login_required
def list_projects(team_id):
    return jsonify(services().list_projects(g.user_id, team_id))


@api.post("/teams/<int:team_id>/projects")
@login_required
def create_project(team_id):
    return jsonify(services().create_project(g.user_id, team_id, body())), 201


@api.get("/projects/<int:project_id>")
@login_required
def get_project(project_id):
    return jsonify(services().get_project(g.user_id, project_id))


@api.get("/projects/<int:project_id>/tasks")
@login_required
def list_tasks(project_id):
    return jsonify(services().list_tasks(g.user_id, project_id, request.args.get("status")))


@api.post("/projects/<int:project_id>/tasks")
@login_required
def create_task(project_id):
    return jsonify(services().create_task(g.user_id, project_id, body())), 201


@api.patch("/tasks/<int:task_id>")
@login_required
def update_task(task_id):
    return jsonify(services().update_task(g.user_id, task_id, body()))


@api.delete("/tasks/<int:task_id>")
@login_required
def delete_task(task_id):
    services().delete_task(g.user_id, task_id)
    return "", 204


@api.get("/notifications")
@login_required
def list_notifications():
    return jsonify(services().list_notifications(g.user_id))


@api.post("/notifications/read-all")
@login_required
def read_all():
    services().mark_all_notifications(g.user_id)
    return "", 204


@api.post("/notifications/<int:notification_id>/read")
@login_required
def read_one(notification_id):
    services().mark_notification(g.user_id, notification_id)
    return "", 204
