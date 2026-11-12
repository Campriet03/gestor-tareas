"""Pruebas de integración de la API.

Por defecto usan SQLite en memoria. Para probar contra MySQL real:
    TEST_DATABASE_URL=mysql://usuario:clave@127.0.0.1:3306/base python -m unittest discover -s tests
"""
import os
import unittest

from app import create_app
from app.auth import create_token
from app.db import make_database

SECRET = "secreto-de-pruebas"
TABLES = ("notifications", "tasks", "projects", "team_invitations", "team_members", "teams", "users")


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.db = make_database(os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:"))
        self.db.init_schema()
        for table in TABLES:
            self.db.execute(f"DELETE FROM {table}")
        self.app = create_app({"DATABASE": self.db, "JWT_SECRET": SECRET})
        self.client = self.app.test_client()

    # ---- ayudas ----
    def call(self, method, path, token=None, **kwargs):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return getattr(self.client, method)(f"/api/v1{path}", headers=headers, **kwargs)

    def register(self, name, email=None):
        email = email or f"{name.lower()}@example.com"
        res = self.call("post", "/auth/register", json={"name": name, "email": email, "password": "clave-segura-1"})
        self.assertEqual(res.status_code, 201, res.get_json())
        return res.get_json()

    def team_with_project(self, owner_token):
        team = self.call("post", "/teams", owner_token, json={"name": "Equipo A"}).get_json()
        project = self.call("post", f"/teams/{team['id']}/projects", owner_token,
                            json={"name": "Proyecto 1", "description": "Demo"}).get_json()
        return team, project

    def add_member(self, team, owner_token, member):
        self.call("post", f"/teams/{team['id']}/invitations", owner_token, json={"email": member["user"]["email"]})
        inv = self.call("get", "/invitations", member["token"]).get_json()[0]
        self.assertEqual(self.call("post", f"/invitations/{inv['id']}/accept", member["token"]).status_code, 200)


class AuthTests(ApiTestCase):
    def test_register_login_and_me(self):
        data = self.register("Ana")
        self.assertIn("token", data)
        self.assertNotIn("password_hash", data["user"])
        login = self.call("post", "/auth/login", json={"email": "ANA@example.com", "password": "clave-segura-1"})
        self.assertEqual(login.status_code, 200)
        me = self.call("get", "/auth/me", login.get_json()["token"])
        self.assertEqual(me.get_json()["email"], "ana@example.com")

    def test_password_is_hashed(self):
        self.register("Ana")
        row = self.db.query_one("SELECT password_hash FROM users")
        self.assertNotEqual(row["password_hash"], "clave-segura-1")
        self.assertNotIn("clave-segura-1", row["password_hash"])

    def test_register_validation(self):
        bad = [{"name": "", "email": "a@b.co", "password": "clave-segura-1"},
               {"name": "Ana", "email": "no-es-correo", "password": "clave-segura-1"},
               {"name": "Ana", "email": "a@b.co", "password": "corta"}]
        for payload in bad:
            self.assertEqual(self.call("post", "/auth/register", json=payload).status_code, 400, payload)
        self.assertEqual(self.call("post", "/auth/register", data="no json").status_code, 400)

    def test_duplicate_email(self):
        self.register("Ana")
        res = self.call("post", "/auth/register", json={"name": "Otra", "email": "ana@example.com",
                                                         "password": "clave-segura-1"})
        self.assertEqual(res.status_code, 409)

    def test_wrong_credentials(self):
        self.register("Ana")
        for payload in ({"email": "ana@example.com", "password": "incorrecta"},
                        {"email": "nadie@example.com", "password": "clave-segura-1"}):
            self.assertEqual(self.call("post", "/auth/login", json=payload).status_code, 401)

    def test_protected_routes_need_valid_token(self):
        self.assertEqual(self.call("get", "/teams").status_code, 401)
        self.assertEqual(self.call("get", "/teams", "token-falso").status_code, 401)
        user = self.register("Ana")
        expired = create_token(user["user"]["id"], SECRET, -10)
        self.assertEqual(self.call("get", "/teams", expired).status_code, 401)
        forged = create_token(user["user"]["id"], "otra-clave", 3600)
        self.assertEqual(self.call("get", "/teams", forged).status_code, 401)

    def test_health_and_unknown_route(self):
        self.assertEqual(self.call("get", "/health").get_json(), {"status": "ok"})
        res = self.call("get", "/no-existe")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.get_json()["error"]["code"], "not_found")


class TeamTests(ApiTestCase):
    def test_create_and_list_teams_are_private(self):
        ana, luis = self.register("Ana"), self.register("Luis")
        team = self.call("post", "/teams", ana["token"], json={"name": "Equipo A"}).get_json()
        self.assertEqual(team["role"], "owner")
        self.assertEqual(len(self.call("get", "/teams", ana["token"]).get_json()), 1)
        self.assertEqual(self.call("get", "/teams", luis["token"]).get_json(), [])
        self.assertEqual(self.call("get", f"/teams/{team['id']}", luis["token"]).status_code, 403)
        self.assertEqual(self.call("get", "/teams/999", ana["token"]).status_code, 404)

    def test_team_name_required(self):
        ana = self.register("Ana")
        self.assertEqual(self.call("post", "/teams", ana["token"], json={"name": "  "}).status_code, 400)

    def test_invitation_flow(self):
        ana, luis = self.register("Ana"), self.register("Luis")
        team, _ = self.team_with_project(ana["token"])
        res = self.call("post", f"/teams/{team['id']}/invitations", ana["token"], json={"email": "luis@example.com"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(self.call("post", f"/teams/{team['id']}/invitations", ana["token"],
                                   json={"email": "luis@example.com"}).status_code, 409)
        notes = self.call("get", "/notifications", luis["token"]).get_json()
        self.assertEqual(notes["unread"], 1)
        invitations = self.call("get", "/invitations", luis["token"]).get_json()
        self.assertEqual(invitations[0]["team_name"], "Equipo A")
        self.assertEqual(self.call("post", f"/invitations/{invitations[0]['id']}/accept", luis["token"]).status_code, 200)
        self.assertEqual(self.call("get", f"/teams/{team['id']}", luis["token"]).get_json()["role"], "member")
        self.assertEqual(self.call("post", f"/invitations/{invitations[0]['id']}/accept", luis["token"]).status_code, 409)
        self.assertEqual(self.call("get", "/notifications", ana["token"]).get_json()["unread"], 1)

    def test_decline_does_not_add_member(self):
        ana, luis = self.register("Ana"), self.register("Luis")
        team, _ = self.team_with_project(ana["token"])
        self.call("post", f"/teams/{team['id']}/invitations", ana["token"], json={"email": "luis@example.com"})
        inv = self.call("get", "/invitations", luis["token"]).get_json()[0]
        self.call("post", f"/invitations/{inv['id']}/decline", luis["token"])
        self.assertEqual(self.call("get", f"/teams/{team['id']}", luis["token"]).status_code, 403)
        self.assertEqual(self.call("get", "/invitations", luis["token"]).get_json(), [])

    def test_invitation_rules(self):
        ana, luis, eva = self.register("Ana"), self.register("Luis"), self.register("Eva")
        team, _ = self.team_with_project(ana["token"])
        self.add_member(team, ana["token"], luis)
        # un miembro no puede invitar
        res = self.call("post", f"/teams/{team['id']}/invitations", luis["token"], json={"email": "eva@example.com"})
        self.assertEqual(res.status_code, 403)
        # correo inexistente, ya miembro y correo inválido
        for email, code in (("nadie@example.com", 404), ("luis@example.com", 409), ("mal", 400)):
            res = self.call("post", f"/teams/{team['id']}/invitations", ana["token"], json={"email": email})
            self.assertEqual(res.status_code, code, email)
        # otra persona no puede responder una invitación ajena
        self.call("post", f"/teams/{team['id']}/invitations", ana["token"], json={"email": "eva@example.com"})
        inv = self.call("get", "/invitations", eva["token"]).get_json()[0]
        self.assertEqual(self.call("post", f"/invitations/{inv['id']}/accept", luis["token"]).status_code, 404)


class ProjectAndTaskTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.ana, self.luis, self.eva = self.register("Ana"), self.register("Luis"), self.register("Eva")
        self.team, self.project = self.team_with_project(self.ana["token"])
        self.add_member(self.team, self.ana["token"], self.luis)
        self.path = f"/projects/{self.project['id']}/tasks"

    def new_task(self, token=None, **extra):
        payload = {"title": "Diseñar pantalla", **extra}
        return self.call("post", self.path, token or self.ana["token"], json=payload)

    def test_outsider_cannot_touch_team_data(self):
        t = self.eva["token"]
        self.assertEqual(self.call("get", f"/teams/{self.team['id']}/projects", t).status_code, 403)
        self.assertEqual(self.call("post", f"/teams/{self.team['id']}/projects", t, json={"name": "X"}).status_code, 403)
        self.assertEqual(self.call("get", f"/projects/{self.project['id']}", t).status_code, 403)
        self.assertEqual(self.call("get", self.path, t).status_code, 403)
        self.assertEqual(self.new_task(t).status_code, 403)
        task = self.new_task().get_json()
        self.assertEqual(self.call("patch", f"/tasks/{task['id']}", t, json={"status": "done"}).status_code, 403)
        self.assertEqual(self.call("delete", f"/tasks/{task['id']}", t).status_code, 403)

    def test_projects(self):
        res = self.call("post", f"/teams/{self.team['id']}/projects", self.luis["token"],
                        json={"name": "Proyecto 2"})
        self.assertEqual(res.status_code, 201)
        listed = self.call("get", f"/teams/{self.team['id']}/projects", self.luis["token"]).get_json()
        self.assertEqual({p["name"] for p in listed}, {"Proyecto 1", "Proyecto 2"})
        self.assertEqual(self.call("post", f"/teams/{self.team['id']}/projects", self.ana["token"],
                                   json={"description": "sin nombre"}).status_code, 400)

    def test_task_crud(self):
        task = self.new_task(description="Detalle", due_date="2026-12-01").get_json()
        self.assertEqual((task["status"], task["due_date"], task["assignee_id"]), ("todo", "2026-12-01", None))
        upd = self.call("patch", f"/tasks/{task['id']}", self.luis["token"],
                        json={"status": "doing", "title": "Nuevo título"}).get_json()
        self.assertEqual((upd["status"], upd["title"]), ("doing", "Nuevo título"))
        self.assertEqual(len(self.call("get", self.path, self.ana["token"]).get_json()), 1)
        self.assertEqual(self.call("delete", f"/tasks/{task['id']}", self.ana["token"]).status_code, 204)
        self.assertEqual(self.call("get", self.path, self.ana["token"]).get_json(), [])
        self.assertEqual(self.call("patch", "/tasks/999", self.ana["token"], json={"status": "done"}).status_code, 404)

    def test_task_validation(self):
        bad = [{"title": ""}, {"title": "x" * 151}, {"title": "ok", "status": "otro"},
               {"title": "ok", "due_date": "mañana"}, {"title": "ok", "assignee_id": self.eva["user"]["id"]},
               {"title": "ok", "assignee_id": "uno"}]
        for payload in bad:
            self.assertEqual(self.call("post", self.path, self.ana["token"], json=payload).status_code, 400, payload)
        task = self.new_task().get_json()
        for payload in ({"status": "otro"}, {"title": ""}, {"assignee_id": 9999}, {"due_date": "x"}):
            res = self.call("patch", f"/tasks/{task['id']}", self.ana["token"], json=payload)
            self.assertEqual(res.status_code, 400, payload)

    def test_status_filter(self):
        self.new_task(status="done")
        self.new_task(title="Otra")
        done = self.call("get", f"{self.path}?status=done", self.ana["token"]).get_json()
        self.assertEqual([t["status"] for t in done], ["done"])
        self.assertEqual(self.call("get", f"{self.path}?status=raro", self.ana["token"]).status_code, 400)

    def test_assignment_creates_notification_and_clears_with_null(self):
        luis_id = self.luis["user"]["id"]
        self.call("post", "/notifications/read-all", self.luis["token"])
        task = self.new_task(assignee_id=luis_id).get_json()
        self.assertEqual(task["assignee_name"], "Luis")
        notes = self.call("get", "/notifications", self.luis["token"]).get_json()
        self.assertEqual(notes["unread"], 1)
        self.assertIn("Diseñar pantalla", notes["items"][0]["message"])
        # asignarse a uno mismo no genera aviso
        self.call("post", "/notifications/read-all", self.ana["token"])
        self.new_task(title="Propia", assignee_id=self.ana["user"]["id"])
        self.assertEqual(self.call("get", "/notifications", self.ana["token"]).get_json()["unread"], 0)
        # reasignar notifica y null quita la asignación
        other = self.new_task(title="Sin asignar").get_json()
        self.call("patch", f"/tasks/{other['id']}", self.ana["token"], json={"assignee_id": luis_id})
        self.assertEqual(self.call("get", "/notifications", self.luis["token"]).get_json()["unread"], 2)
        cleared = self.call("patch", f"/tasks/{other['id']}", self.ana["token"], json={"assignee_id": None}).get_json()
        self.assertIsNone(cleared["assignee_id"])

    def test_delete_permissions(self):
        task = self.new_task(self.ana["token"]).get_json()
        self.assertEqual(self.call("delete", f"/tasks/{task['id']}", self.luis["token"]).status_code, 403)
        mine = self.new_task(self.luis["token"]).get_json()
        self.assertEqual(self.call("delete", f"/tasks/{mine['id']}", self.luis["token"]).status_code, 204)
        theirs = self.new_task(self.luis["token"]).get_json()
        self.assertEqual(self.call("delete", f"/tasks/{theirs['id']}", self.ana["token"]).status_code, 204)


class NotificationTests(ApiTestCase):
    def test_read_one_and_all(self):
        ana, luis = self.register("Ana"), self.register("Luis")
        team, _ = self.team_with_project(ana["token"])
        for _ in range(2):
            self.db.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (luis["user"]["id"], "hola"))
        notes = self.call("get", "/notifications", luis["token"]).get_json()
        self.assertEqual((notes["unread"], len(notes["items"])), (2, 2))
        self.assertIs(notes["items"][0]["is_read"], False)
        first = notes["items"][0]["id"]
        self.assertEqual(self.call("post", f"/notifications/{first}/read", ana["token"]).status_code, 404)
        self.assertEqual(self.call("post", f"/notifications/{first}/read", luis["token"]).status_code, 204)
        self.assertEqual(self.call("get", "/notifications", luis["token"]).get_json()["unread"], 1)
        self.call("post", "/notifications/read-all", luis["token"])
        self.assertEqual(self.call("get", "/notifications", luis["token"]).get_json()["unread"], 0)


if __name__ == "__main__":
    unittest.main()
