# Unit Tests

Location: `tests/`. Pure `unittest` (Python standard library) — no extra packages to install.

## Run

```
python -m unittest discover -s tests -v
```

39 tests, ~12s, all passing.

## Isolation

`tests/base.py` defines `IsolatedDBTestCase`. Its `setUp`/`tearDown` point
`database.DB_PATH` and `database.UPLOADS_DIR` at a fresh temp file/folder for
the duration of each test, then restore the originals. Every function in
`database.py` reads those two names as module globals on each call, so this
redirects the entire data layer without touching `database.py` itself —
tests can never read or write the real `assignment_app.db` or `uploads/`.

## Coverage

### `tests/test_auth.py` — password hashing & login
- Hash contains a salt + digest; the same password hashes differently each
  call (random salt), and both still verify correctly.
- `verify_password` accepts the right password, rejects a wrong one.
- `login()` returns the user row on success, `None` on wrong password or
  unknown email.

### `tests/test_database.py` — CRUD + constraints
- **Users**: create/lookup by email, duplicate email rejected (`UNIQUE`),
  invalid role rejected (`CHECK`), filter by role.
- **Courses**: create/list by faculty, duplicate course code rejected.
- **Enrollment**: enroll/list, duplicate enrollment rejected, "not enrolled"
  list excludes enrolled students, unenroll removes the enrollment *and*
  clears the student from any group under that course's assignments.
- **Assignments**: create/list, invalid `type` rejected (`CHECK`), edit
  (title/description/marks/due date), attachment set and cleared,
  faculty-scoped listing filtered by type (`INDIVIDUAL` vs `GROUP`).
- **Submissions**: create/list, the `SUBMISSIONS` table's CHECK constraint
  rejects a row with neither `student_id` nor `group_id` set, and rejects a
  row with both set.
- **Groups**: duplicate group name rejected per assignment, moving a student
  between groups updates member counts correctly, unassigning works, group
  membership is scoped per-assignment (the same student in two different
  GROUP assignments doesn't leak membership across them), auto-distribute
  places every enrolled student, never moves someone already placed, and is
  safe to run twice (idempotent).
- **Migration**: `_migrate()` adds the `attachment_path` column to a
  pre-existing `ASSIGNMENTS` table that predates it, and is a no-op if the
  column already exists.

### `tests/test_workflow.py` — end-to-end scenarios
Mirrors the real user flow using the same `database.py` functions and disk
layout the UI calls, in the same order:
- Individual assignment: create → faculty attaches a brief → student (who is
  enrolled) can see it → student submits → submission recorded with the file
  present on disk.
- Group assignment: create → auto-distribute → student is placed in a group.
- Unenrolling a student removes their visibility into that course.
- Regression: two assignments sharing an identical title stay independently
  submittable (locks in the fix for the dropdown bug where same-titled
  assignments used to collide and silently resolve to the wrong
  `assignment_id`).
