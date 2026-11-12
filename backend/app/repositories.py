"""Capa de repositorios: unico lugar donde se escribe SQL (ADR 0004)."""


class UserRepository:
    def __init__(self, db):
        self.db = db

    def create(self, name, email, password_hash):
        return self.db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, password_hash))

    def by_email(self, email):
        return self.db.query_one("SELECT * FROM users WHERE email = ?", (email,))

    def by_id(self, user_id):
        return self.db.query_one("SELECT id, name, email FROM users WHERE id = ?", (user_id,))


class TeamRepository:
    def __init__(self, db):
        self.db = db

    def create(self, name, owner_id):
        with self.db.transaction():
            team_id = self.db.execute("INSERT INTO teams (name, owner_id) VALUES (?, ?)", (name, owner_id))
            self.db.execute("INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'owner')",
                            (team_id, owner_id))
        return team_id

    def get(self, team_id):
        return self.db.query_one("SELECT id, name, owner_id FROM teams WHERE id = ?", (team_id,))

    def for_user(self, user_id):
        return self.db.query(
            "SELECT t.id, t.name, t.owner_id, tm.role FROM teams t "
            "JOIN team_members tm ON tm.team_id = t.id WHERE tm.user_id = ? ORDER BY t.name", (user_id,))

    def role(self, team_id, user_id):
        row = self.db.query_one("SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
                                (team_id, user_id))
        return row["role"] if row else None

    def members(self, team_id):
        return self.db.query(
            "SELECT u.id, u.name, u.email, tm.role FROM team_members tm "
            "JOIN users u ON u.id = tm.user_id WHERE tm.team_id = ? ORDER BY u.name", (team_id,))

    def add_member(self, team_id, user_id):
        self.db.execute("INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'member')",
                        (team_id, user_id))

    def create_invitation(self, team_id, email, invited_by):
        return self.db.execute(
            "INSERT INTO team_invitations (team_id, email, invited_by) VALUES (?, ?, ?)",
            (team_id, email, invited_by))

    def pending_invitation(self, team_id, email):
        return self.db.query_one(
            "SELECT id FROM team_invitations WHERE team_id = ? AND email = ? AND status = 'pending'",
            (team_id, email))

    def invitation(self, invitation_id):
        return self.db.query_one(
            "SELECT i.id, i.team_id, i.email, i.invited_by, i.status, t.name AS team_name "
            "FROM team_invitations i JOIN teams t ON t.id = i.team_id WHERE i.id = ?", (invitation_id,))

    def pending_for_email(self, email):
        return self.db.query(
            "SELECT i.id, i.team_id, t.name AS team_name, u.name AS invited_by_name, i.created_at "
            "FROM team_invitations i JOIN teams t ON t.id = i.team_id JOIN users u ON u.id = i.invited_by "
            "WHERE i.email = ? AND i.status = 'pending' ORDER BY i.id DESC", (email,))

    def set_invitation_status(self, invitation_id, status):
        self.db.execute("UPDATE team_invitations SET status = ? WHERE id = ?", (status, invitation_id))


class ProjectRepository:
    def __init__(self, db):
        self.db = db

    def create(self, team_id, name, description):
        return self.db.execute("INSERT INTO projects (team_id, name, description) VALUES (?, ?, ?)",
                               (team_id, name, description))

    def get(self, project_id):
        return self.db.query_one(
            "SELECT id, team_id, name, description, created_at FROM projects WHERE id = ?", (project_id,))

    def for_team(self, team_id):
        return self.db.query(
            "SELECT id, team_id, name, description, created_at FROM projects "
            "WHERE team_id = ? ORDER BY id DESC", (team_id,))


class TaskRepository:
    EDITABLE = ("title", "description", "status", "assignee_id", "due_date")
    SELECT = ("SELECT t.id, t.project_id, t.title, t.description, t.status, t.assignee_id, "
              "a.name AS assignee_name, t.created_by, t.due_date, t.created_at "
              "FROM tasks t LEFT JOIN users a ON a.id = t.assignee_id ")

    def __init__(self, db):
        self.db = db

    def create(self, project_id, title, description, status, assignee_id, due_date, created_by):
        return self.db.execute(
            "INSERT INTO tasks (project_id, title, description, status, assignee_id, due_date, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, title, description, status, assignee_id, due_date, created_by))

    def get(self, task_id):
        return self.db.query_one(self.SELECT + "WHERE t.id = ?", (task_id,))

    def for_project(self, project_id, status=None):
        sql, params = self.SELECT + "WHERE t.project_id = ?", [project_id]
        if status:
            sql += " AND t.status = ?"
            params.append(status)
        return self.db.query(sql + " ORDER BY t.id", params)

    def update(self, task_id, fields):
        columns = [c for c in fields if c in self.EDITABLE]
        if not columns:
            return
        assignments = ", ".join(f"{c} = ?" for c in columns)
        self.db.execute(f"UPDATE tasks SET {assignments} WHERE id = ?",
                        [fields[c] for c in columns] + [task_id])

    def delete(self, task_id):
        self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


class NotificationRepository:
    def __init__(self, db):
        self.db = db

    def create(self, user_id, message):
        self.db.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, message))

    def for_user(self, user_id, limit=50):
        return self.db.query(
            "SELECT id, message, is_read, created_at FROM notifications "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))

    def unread_count(self, user_id):
        return self.db.query_one(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,))["n"]

    def get(self, notification_id):
        return self.db.query_one("SELECT id, user_id FROM notifications WHERE id = ?", (notification_id,))

    def mark_read(self, notification_id):
        self.db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))

    def mark_all_read(self, user_id):
        self.db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
