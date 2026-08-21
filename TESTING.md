# Unit Tests

Location: `tests/`. Pure `unittest` (Python standard library) — no extra packages to install.

## Run

```
python -m unittest discover -s tests -v
```

49 tests, ~13s, all passing. Run one file at a time, in build-up order:

```
python -m unittest tests.test_auth -v
python -m unittest tests.test_database -v
python -m unittest tests.test_workflow -v
```

## Isolation

`tests/base.py` defines `IsolatedDBTestCase`. Its `setUp`/`tearDown` point
`database.DB_PATH` and `database.UPLOADS_DIR` at a fresh temp file/folder for
the duration of each test, then restore the originals. Every function in
`database.py` reads those two names as module globals on each call, so this
redirects the entire data layer without touching `database.py` itself —
tests can never read or write the real `assignment_app.db` or `uploads/`.

```python
# tests/base.py
import shutil
import tempfile
import unittest
from pathlib import Path

import database


class IsolatedDBTestCase(unittest.TestCase):
    """Points database.DB_PATH / database.UPLOADS_DIR at a throwaway temp
    location for the duration of each test, so tests can never read or write
    the real assignment_app.db or uploads/ folder — every database.py
    function reads these as module globals on each call, so reassigning them
    here redirects every function without touching database.py itself."""

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="ama_test_")
        self._original_db_path = database.DB_PATH
        self._original_uploads_dir = database.UPLOADS_DIR
        database.DB_PATH = str(Path(self._tmp_dir) / "test.db")
        database.UPLOADS_DIR = str(Path(self._tmp_dir) / "uploads")
        database.initialize_db()

    def tearDown(self):
        database.DB_PATH = self._original_db_path
        database.UPLOADS_DIR = self._original_uploads_dir
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
```

## Coverage

### `tests/test_auth.py` — password hashing & login (7 tests)
- Hash contains a salt + digest; the same password hashes differently each
  call (random salt), and both still verify correctly.
- `verify_password` accepts the right password, rejects a wrong one.
- `login()` returns the user row on success, `None` on wrong password or
  unknown email.

```python
# tests/test_auth.py
import unittest

import database
from auth import hash_password, login, verify_password
from tests.base import IsolatedDBTestCase


class HashPasswordTests(unittest.TestCase):
    def test_hash_contains_salt_and_digest(self):
        hashed = hash_password("secret123")
        salt_hex, digest_hex = hashed.split("$")
        self.assertTrue(salt_hex)
        self.assertTrue(digest_hex)

    def test_same_password_hashes_differently_each_time(self):
        # Random salt per call — two hashes of the same password must never match
        # verbatim, even though both verify correctly.
        first = hash_password("secret123")
        second = hash_password("secret123")
        self.assertNotEqual(first, second)

    def test_verify_password_correct(self):
        hashed = hash_password("secret123")
        self.assertTrue(verify_password("secret123", hashed))

    def test_verify_password_incorrect(self):
        hashed = hash_password("secret123")
        self.assertFalse(verify_password("wrong-password", hashed))


class LoginTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        database.create_user("Test User", "test@example.com", hash_password("secret123"), "student")

    def test_login_success_returns_user_row(self):
        user = login("test@example.com", "secret123")
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "test@example.com")
        self.assertEqual(user["role"], "student")

    def test_login_wrong_password_returns_none(self):
        self.assertIsNone(login("test@example.com", "wrong-password"))

    def test_login_unknown_email_returns_none(self):
        self.assertIsNone(login("nobody@example.com", "secret123"))
```

### `tests/test_database.py` — CRUD + constraints (38 tests)
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
- **Grading**: an ungraded submission reports `marks_obtained = None` to both
  faculty and student views; `create_or_update_grade` is visible from both
  `list_submissions_for_assignment` (faculty) and `list_submissions_by_student`
  (student) after grading; re-grading updates the existing `GRADES` row in
  place rather than inserting a second one (`GRADES.submission_id` is
  `UNIQUE`); a group submission reports `group_name`, not `student_name`;
  `list_submissions_for_faculty` spans every course they teach and never
  leaks another faculty member's submissions.
- **Deadline status**: `list_assignments_for_student_with_status` correctly
  flags an unsubmitted assignment as not-submitted, flips to
  `submitted_individually` after an individual submission, flips to
  `submitted_as_group` when the student's group (via `GROUP_MEMBERS`)
  submitted instead, and only ever includes courses the student is actually
  enrolled in.
- **Groups**: duplicate group name rejected per assignment, moving a student
  between groups updates member counts correctly, unassigning works, group
  membership is scoped per-assignment (the same student in two different
  GROUP assignments doesn't leak membership across them), auto-distribute
  places every enrolled student, never moves someone already placed, and is
  safe to run twice (idempotent).
- **Migration**: `_migrate()` adds the `attachment_path` column to a
  pre-existing `ASSIGNMENTS` table that predates it, and is a no-op if the
  column already exists.

```python
# tests/test_database.py
import sqlite3
import unittest

import database
from auth import hash_password
from tests.base import IsolatedDBTestCase


class UserTests(IsolatedDBTestCase):
    def test_create_and_get_user_by_email(self):
        database.create_user("Alice", "alice@example.com", hash_password("pw"), "student")
        user = database.get_user_by_email("alice@example.com")
        self.assertEqual(user["name"], "Alice")
        self.assertEqual(user["role"], "student")

    def test_duplicate_email_raises(self):
        database.create_user("Alice", "alice@example.com", hash_password("pw"), "student")
        with self.assertRaises(sqlite3.IntegrityError):
            database.create_user("Alice Two", "alice@example.com", hash_password("pw2"), "student")

    def test_invalid_role_rejected_by_check_constraint(self):
        with self.assertRaises(sqlite3.IntegrityError):
            database.create_user("Bob", "bob@example.com", hash_password("pw"), "wizard")

    def test_list_users_filtered_by_role(self):
        database.create_user("Fac", "fac@example.com", hash_password("pw"), "faculty")
        database.create_user("Stu", "stu@example.com", hash_password("pw"), "student")
        students = database.list_users(role="student")
        self.assertEqual([s["email"] for s in students], ["stu@example.com"])


class CourseTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user("Dr. Fac", "fac@example.com", hash_password("pw"), "faculty")

    def test_create_and_list_courses_by_faculty(self):
        database.create_course("CS101", "Intro to CS", self.faculty_id)
        courses = database.list_courses_by_faculty(self.faculty_id)
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0]["course_code"], "CS101")

    def test_duplicate_course_code_raises(self):
        database.create_course("CS101", "Intro to CS", self.faculty_id)
        with self.assertRaises(sqlite3.IntegrityError):
            database.create_course("CS101", "A Different Course", self.faculty_id)


class EnrollmentTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user("Dr. Fac", "fac@example.com", hash_password("pw"), "faculty")
        self.student_id = database.create_user("Stu", "stu@example.com", hash_password("pw"), "student")
        self.course_id = database.create_course("CS101", "Intro to CS", self.faculty_id)

    def test_enroll_and_list_enrolled_students(self):
        database.enroll_student(self.student_id, self.course_id)
        enrolled = database.list_enrolled_students(self.course_id)
        self.assertEqual([s["user_id"] for s in enrolled], [self.student_id])

    def test_duplicate_enrollment_raises(self):
        database.enroll_student(self.student_id, self.course_id)
        with self.assertRaises(sqlite3.IntegrityError):
            database.enroll_student(self.student_id, self.course_id)

    def test_list_students_not_enrolled_excludes_enrolled(self):
        self.assertEqual(len(database.list_students_not_enrolled_in_course(self.course_id)), 1)
        database.enroll_student(self.student_id, self.course_id)
        self.assertEqual(len(database.list_students_not_enrolled_in_course(self.course_id)), 0)

    def test_unenroll_removes_enrollment(self):
        database.enroll_student(self.student_id, self.course_id)
        database.unenroll_student(self.student_id, self.course_id)
        self.assertEqual(database.list_enrolled_students(self.course_id), [])

    def test_unenroll_also_clears_group_membership(self):
        database.enroll_student(self.student_id, self.course_id)
        assignment_id = database.create_assignment(
            self.course_id, "Group Project", "desc", "GROUP", 50, "2026-12-01 23:59", self.faculty_id
        )
        group_id = database.create_group(assignment_id, "Group 1")
        database.set_student_group(assignment_id, self.student_id, group_id)
        self.assertEqual(database.list_groups_by_assignment(assignment_id)[0]["member_count"], 1)

        database.unenroll_student(self.student_id, self.course_id)

        self.assertEqual(database.list_groups_by_assignment(assignment_id)[0]["member_count"], 0)


class AssignmentTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user("Dr. Fac", "fac@example.com", hash_password("pw"), "faculty")
        self.course_id = database.create_course("CS101", "Intro to CS", self.faculty_id)

    def test_create_and_list_assignment(self):
        assignment_id = database.create_assignment(
            self.course_id, "HW1", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        assignments = database.list_assignments_by_course(self.course_id)
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["assignment_id"], assignment_id)
        self.assertIsNone(assignments[0]["attachment_path"])

    def test_invalid_type_rejected_by_check_constraint(self):
        with self.assertRaises(sqlite3.IntegrityError):
            database.create_assignment(
                self.course_id, "HW1", "desc", "SOLO", 100, "2026-10-01 23:59", self.faculty_id
            )

    def test_update_assignment_changes_fields(self):
        assignment_id = database.create_assignment(
            self.course_id, "HW1", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        database.update_assignment(assignment_id, "HW1 Revised", "new desc", 80, "2026-10-15 23:59")
        updated = database.list_assignments_by_course(self.course_id)[0]
        self.assertEqual(updated["title"], "HW1 Revised")
        self.assertEqual(updated["description"], "new desc")
        self.assertEqual(updated["max_marks"], 80)
        self.assertEqual(updated["due_date"], "2026-10-15 23:59")

    def test_update_assignment_attachment(self):
        assignment_id = database.create_assignment(
            self.course_id, "HW1", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        database.update_assignment_attachment(assignment_id, "/fake/path/brief.pdf")
        updated = database.list_assignments_by_course(self.course_id)[0]
        self.assertEqual(updated["attachment_path"], "/fake/path/brief.pdf")

        database.update_assignment_attachment(assignment_id, None)
        cleared = database.list_assignments_by_course(self.course_id)[0]
        self.assertIsNone(cleared["attachment_path"])

    def test_list_assignments_by_faculty_filters_by_type(self):
        database.create_assignment(self.course_id, "Solo HW", "d", "INDIVIDUAL", 10, "2026-10-01 23:59", self.faculty_id)
        database.create_assignment(self.course_id, "Team HW", "d", "GROUP", 10, "2026-10-01 23:59", self.faculty_id)

        self.assertEqual(len(database.list_assignments_by_faculty(self.faculty_id)), 2)
        group_only = database.list_assignments_by_faculty(self.faculty_id, type_="GROUP")
        self.assertEqual([a["title"] for a in group_only], ["Team HW"])


class SubmissionTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user("Dr. Fac", "fac@example.com", hash_password("pw"), "faculty")
        self.student_id = database.create_user("Stu", "stu@example.com", hash_password("pw"), "student")
        self.course_id = database.create_course("CS101", "Intro to CS", self.faculty_id)
        database.enroll_student(self.student_id, self.course_id)
        self.assignment_id = database.create_assignment(
            self.course_id, "HW1", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )

    def test_create_and_list_submission(self):
        database.create_submission(self.assignment_id, self.student_id, "/fake/path/hw1.pdf")
        submissions = database.list_submissions_by_student(self.student_id)
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0]["title"], "HW1")
        self.assertEqual(submissions[0]["course_code"], "CS101")

    def test_submission_rejects_neither_student_nor_group(self):
        conn = database.get_connection()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO SUBMISSIONS (assignment_id, student_id, group_id, file_path) VALUES (?, NULL, NULL, ?)",
                (self.assignment_id, "/fake/path.pdf"),
            )
        conn.close()

    def test_submission_rejects_both_student_and_group(self):
        group_id = database.create_group(self.assignment_id, "Group 1")
        conn = database.get_connection()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO SUBMISSIONS (assignment_id, student_id, group_id, file_path) VALUES (?, ?, ?, ?)",
                (self.assignment_id, self.student_id, group_id, "/fake/path.pdf"),
            )
        conn.close()


class GradingTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user("Dr. Fac", "fac@example.com", hash_password("pw"), "faculty")
        self.student_id = database.create_user("Stu", "stu@example.com", hash_password("pw"), "student")
        self.course_id = database.create_course("CS101", "Intro to CS", self.faculty_id)
        database.enroll_student(self.student_id, self.course_id)
        self.assignment_id = database.create_assignment(
            self.course_id, "HW1", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        self.submission_id = database.create_submission(self.assignment_id, self.student_id, "/fake/hw1.pdf")

    def test_ungraded_submission_shows_no_marks(self):
        submissions = database.list_submissions_for_assignment(self.assignment_id)
        self.assertEqual(len(submissions), 1)
        self.assertIsNone(submissions[0]["marks_obtained"])
        self.assertEqual(submissions[0]["student_name"], "Stu")

        by_student = database.list_submissions_by_student(self.student_id)
        self.assertIsNone(by_student[0]["marks_obtained"])

    def test_create_grade_then_visible_to_faculty_and_student(self):
        database.create_or_update_grade(self.submission_id, 85, "Good work", self.faculty_id)

        for_faculty = database.list_submissions_for_assignment(self.assignment_id)[0]
        self.assertEqual(for_faculty["marks_obtained"], 85)
        self.assertEqual(for_faculty["feedback"], "Good work")

        for_student = database.list_submissions_by_student(self.student_id)[0]
        self.assertEqual(for_student["marks_obtained"], 85)
        self.assertEqual(for_student["feedback"], "Good work")
        self.assertEqual(for_student["max_marks"], 100)

    def test_regrading_updates_in_place_not_a_second_row(self):
        database.create_or_update_grade(self.submission_id, 70, "First pass", self.faculty_id)
        database.create_or_update_grade(self.submission_id, 90, "Revised after resubmission talk", self.faculty_id)

        conn = database.get_connection()
        rows = conn.execute(
            "SELECT * FROM GRADES WHERE submission_id = ?", (self.submission_id,)
        ).fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["marks_obtained"], 90)
        self.assertEqual(rows[0]["feedback"], "Revised after resubmission talk")

    def test_group_submission_reports_group_name_not_student_name(self):
        group_assignment_id = database.create_assignment(
            self.course_id, "Team HW", "desc", "GROUP", 50, "2026-10-01 23:59", self.faculty_id
        )
        group_id = database.create_group(group_assignment_id, "Group 1")
        conn = database.get_connection()
        conn.execute(
            "INSERT INTO SUBMISSIONS (assignment_id, student_id, group_id, file_path) VALUES (?, NULL, ?, ?)",
            (group_assignment_id, group_id, "/fake/team.pdf"),
        )
        conn.commit()
        conn.close()

        submissions = database.list_submissions_for_assignment(group_assignment_id)
        self.assertEqual(submissions[0]["group_name"], "Group 1")
        self.assertIsNone(submissions[0]["student_name"])

    def test_faculty_submission_history_spans_all_their_courses(self):
        other_course_id = database.create_course("CS102", "Other Course", self.faculty_id)
        other_assignment_id = database.create_assignment(
            other_course_id, "HW2", "desc", "INDIVIDUAL", 20, "2026-10-05 23:59", self.faculty_id
        )
        database.enroll_student(self.student_id, other_course_id)
        database.create_submission(other_assignment_id, self.student_id, "/fake/hw2.pdf")

        history = database.list_submissions_for_faculty(self.faculty_id)
        self.assertEqual(len(history), 2)
        self.assertEqual({h["assignment_title"] for h in history}, {"HW1", "HW2"})

    def test_submission_history_does_not_leak_other_faculty(self):
        other_faculty_id = database.create_user(
            "Dr. Other", "other@example.com", hash_password("pw"), "faculty"
        )
        other_course_id = database.create_course("CS900", "Not Mine", other_faculty_id)
        database.enroll_student(self.student_id, other_course_id)
        other_assignment_id = database.create_assignment(
            other_course_id, "Other HW", "desc", "INDIVIDUAL", 20, "2026-10-05 23:59", other_faculty_id
        )
        database.create_submission(other_assignment_id, self.student_id, "/fake/other.pdf")

        my_history = database.list_submissions_for_faculty(self.faculty_id)
        self.assertEqual(len(my_history), 1)
        self.assertEqual(my_history[0]["assignment_title"], "HW1")


class DeadlineStatusTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user("Dr. Fac", "fac@example.com", hash_password("pw"), "faculty")
        self.student_id = database.create_user("Stu", "stu@example.com", hash_password("pw"), "student")
        self.course_id = database.create_course("CS101", "Intro to CS", self.faculty_id)
        database.enroll_student(self.student_id, self.course_id)

    def test_unsubmitted_individual_assignment_flagged_correctly(self):
        database.create_assignment(
            self.course_id, "HW1", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        rows = database.list_assignments_for_student_with_status(self.student_id)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["submitted_individually"])
        self.assertFalse(rows[0]["submitted_as_group"])

    def test_individual_submission_marks_submitted_individually(self):
        assignment_id = database.create_assignment(
            self.course_id, "HW1", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        database.create_submission(assignment_id, self.student_id, "/fake/hw1.pdf")
        rows = database.list_assignments_for_student_with_status(self.student_id)
        self.assertTrue(rows[0]["submitted_individually"])
        self.assertFalse(rows[0]["submitted_as_group"])

    def test_group_submission_via_membership_marks_submitted_as_group(self):
        assignment_id = database.create_assignment(
            self.course_id, "Team HW", "desc", "GROUP", 100, "2026-10-01 23:59", self.faculty_id
        )
        group_id = database.create_group(assignment_id, "Group 1")
        database.set_student_group(assignment_id, self.student_id, group_id)
        conn = database.get_connection()
        conn.execute(
            "INSERT INTO SUBMISSIONS (assignment_id, student_id, group_id, file_path) VALUES (?, NULL, ?, ?)",
            (assignment_id, group_id, "/fake/team.pdf"),
        )
        conn.commit()
        conn.close()

        rows = database.list_assignments_for_student_with_status(self.student_id)
        self.assertFalse(rows[0]["submitted_individually"])
        self.assertTrue(rows[0]["submitted_as_group"])

    def test_only_this_students_enrolled_courses_are_included(self):
        other_course_id = database.create_course("CS999", "Not Enrolled", self.faculty_id)
        database.create_assignment(
            other_course_id, "Not Mine", "desc", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        rows = database.list_assignments_for_student_with_status(self.student_id)
        self.assertEqual(rows, [])


class GroupTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user("Dr. Fac", "fac@example.com", hash_password("pw"), "faculty")
        self.course_id = database.create_course("CS101", "Intro to CS", self.faculty_id)
        self.students = [
            database.create_user(f"Stu {i}", f"stu{i}@example.com", hash_password("pw"), "student")
            for i in range(5)
        ]
        for sid in self.students:
            database.enroll_student(sid, self.course_id)
        self.assignment_id = database.create_assignment(
            self.course_id, "Team Project", "desc", "GROUP", 100, "2026-12-01 23:59", self.faculty_id
        )

    def test_duplicate_group_name_rejected_per_assignment(self):
        database.create_group(self.assignment_id, "Group 1")
        with self.assertRaises(sqlite3.IntegrityError):
            database.create_group(self.assignment_id, "Group 1")

    def test_set_student_group_moves_between_groups(self):
        g1 = database.create_group(self.assignment_id, "Group 1")
        g2 = database.create_group(self.assignment_id, "Group 2")

        database.set_student_group(self.assignment_id, self.students[0], g1)
        counts = {g["group_id"]: g["member_count"] for g in database.list_groups_by_assignment(self.assignment_id)}
        self.assertEqual(counts[g1], 1)
        self.assertEqual(counts[g2], 0)

        database.set_student_group(self.assignment_id, self.students[0], g2)
        counts = {g["group_id"]: g["member_count"] for g in database.list_groups_by_assignment(self.assignment_id)}
        self.assertEqual(counts[g1], 0)
        self.assertEqual(counts[g2], 1)

    def test_set_student_group_none_unassigns(self):
        g1 = database.create_group(self.assignment_id, "Group 1")
        database.set_student_group(self.assignment_id, self.students[0], g1)
        database.set_student_group(self.assignment_id, self.students[0], None)

        membership = database.list_group_membership_for_assignment(self.course_id, self.assignment_id)
        mine = next(m for m in membership if m["user_id"] == self.students[0])
        self.assertIsNone(mine["group_id"])

    def test_group_membership_is_scoped_to_this_assignment_only(self):
        other_assignment_id = database.create_assignment(
            self.course_id, "Other Team Project", "desc", "GROUP", 50, "2026-12-15 23:59", self.faculty_id
        )
        g1 = database.create_group(self.assignment_id, "Group 1")
        database.set_student_group(self.assignment_id, self.students[0], g1)

        # Same student, different assignment: must show unassigned, not the other group.
        other_membership = database.list_group_membership_for_assignment(self.course_id, other_assignment_id)
        mine = next(m for m in other_membership if m["user_id"] == self.students[0])
        self.assertIsNone(mine["group_id"])

    def test_auto_distribute_groups_places_everyone(self):
        database.auto_distribute_groups(self.course_id, self.assignment_id, group_size=2)
        membership = database.list_group_membership_for_assignment(self.course_id, self.assignment_id)
        self.assertTrue(all(m["group_id"] is not None for m in membership))

        groups = database.list_groups_by_assignment(self.assignment_id)
        self.assertEqual(len(groups), 3)  # 5 students at size 2 -> ceil(5/2) = 3 groups
        self.assertEqual(sum(g["member_count"] for g in groups), 5)

    def test_auto_distribute_never_moves_an_already_placed_student(self):
        g1 = database.create_group(self.assignment_id, "Group 1")
        database.set_student_group(self.assignment_id, self.students[0], g1)

        database.auto_distribute_groups(self.course_id, self.assignment_id, group_size=2)

        membership = database.list_group_membership_for_assignment(self.course_id, self.assignment_id)
        mine = next(m for m in membership if m["user_id"] == self.students[0])
        self.assertEqual(mine["group_id"], g1)

    def test_auto_distribute_is_safe_to_call_twice(self):
        database.auto_distribute_groups(self.course_id, self.assignment_id, group_size=2)
        first_pass = {
            m["user_id"]: m["group_id"]
            for m in database.list_group_membership_for_assignment(self.course_id, self.assignment_id)
        }

        database.auto_distribute_groups(self.course_id, self.assignment_id, group_size=2)
        second_pass = {
            m["user_id"]: m["group_id"]
            for m in database.list_group_membership_for_assignment(self.course_id, self.assignment_id)
        }
        self.assertEqual(first_pass, second_pass)


class MigrationTests(IsolatedDBTestCase):
    def test_migrate_adds_attachment_column_to_a_pre_existing_table(self):
        conn = database.get_connection()
        conn.execute("DROP TABLE ASSIGNMENTS")
        conn.execute(
            """CREATE TABLE ASSIGNMENTS (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL,
                max_marks REAL NOT NULL,
                due_date DATETIME NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.commit()
        before = [r["name"] for r in conn.execute("PRAGMA table_info(ASSIGNMENTS)").fetchall()]
        self.assertNotIn("attachment_path", before)

        database._migrate(conn)

        after = [r["name"] for r in conn.execute("PRAGMA table_info(ASSIGNMENTS)").fetchall()]
        self.assertIn("attachment_path", after)
        conn.close()

    def test_migrate_is_a_no_op_on_an_up_to_date_table(self):
        conn = database.get_connection()
        database._migrate(conn)  # should not raise on a table that already has the column
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(ASSIGNMENTS)").fetchall()]
        self.assertEqual(columns.count("attachment_path"), 1)
        conn.close()
```

### `tests/test_workflow.py` — end-to-end scenarios (4 tests)
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

```python
# tests/test_workflow.py
"""End-to-end checks that mirror the real user flow: faculty creates a course
and assignments, enrolls a student, the student submits, and (for GROUP
assignments) gets placed into a group — using the exact database.py functions
the UI calls, in the same order the UI calls them."""

import os
import unittest

import database
from auth import hash_password
from tests.base import IsolatedDBTestCase


class FullAssignmentWorkflowTests(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        self.faculty_id = database.create_user(
            "Dr. Faculty", "faculty@example.com", hash_password("facpass"), "faculty"
        )
        self.student_id = database.create_user(
            "Student One", "student@example.com", hash_password("studpass"), "student"
        )
        self.course_id = database.create_course("CS999", "Workflow Test Course", self.faculty_id)
        database.enroll_student(self.student_id, self.course_id)

    def test_individual_assignment_create_then_submit(self):
        assignment_id = database.create_assignment(
            self.course_id, "Essay 1", "Write 500 words", "INDIVIDUAL", 100,
            "2026-10-01 23:59", self.faculty_id,
        )

        # Faculty attaches a brief (same disk layout the Create/Edit forms use).
        upload_dir = os.path.join(database.UPLOADS_DIR, str(assignment_id))
        os.makedirs(upload_dir, exist_ok=True)
        brief_path = os.path.join(upload_dir, "brief.txt")
        with open(brief_path, "w") as f:
            f.write("Essay brief")
        database.update_assignment_attachment(assignment_id, brief_path)

        listed = database.list_assignments_by_course(self.course_id)[0]
        self.assertEqual(listed["type"], "INDIVIDUAL")
        self.assertEqual(listed["attachment_path"], brief_path)

        # Student is enrolled, so the assignment must be visible to them...
        enrolled_courses = database.list_enrolled_courses(self.student_id)
        self.assertEqual(len(enrolled_courses), 1)
        visible = database.list_assignments_by_course(enrolled_courses[0]["course_id"])
        self.assertEqual([a["assignment_id"] for a in visible], [assignment_id])

        # ...and then submits (same disk layout the Submit tab uses).
        submission_dir = os.path.join(database.UPLOADS_DIR, str(assignment_id), "submissions")
        os.makedirs(submission_dir, exist_ok=True)
        submitted_path = os.path.join(submission_dir, "essay.txt")
        with open(submitted_path, "w") as f:
            f.write("My essay")
        database.create_submission(assignment_id, self.student_id, submitted_path)

        submissions = database.list_submissions_by_student(self.student_id)
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0]["assignment_id"], assignment_id)
        self.assertTrue(os.path.isfile(submissions[0]["file_path"]))

    def test_group_assignment_create_groups_and_place_student(self):
        assignment_id = database.create_assignment(
            self.course_id, "Team Project", "Build something", "GROUP", 100,
            "2026-11-15 23:59", self.faculty_id,
        )
        self.assertEqual(
            [a["assignment_id"] for a in database.list_assignments_by_faculty(self.faculty_id, type_="GROUP")],
            [assignment_id],
        )

        database.auto_distribute_groups(self.course_id, assignment_id, group_size=3)
        groups = database.list_groups_by_assignment(assignment_id)
        self.assertEqual(len(groups), 1)  # 1 student, size 3 -> 1 group
        self.assertEqual(groups[0]["member_count"], 1)

        membership = database.list_group_membership_for_assignment(self.course_id, assignment_id)
        self.assertEqual(membership[0]["user_id"], self.student_id)
        self.assertEqual(membership[0]["group_id"], groups[0]["group_id"])

    def test_unenrolled_student_loses_visibility_into_the_course(self):
        database.create_assignment(
            self.course_id, "Essay 1", "d", "INDIVIDUAL", 100, "2026-10-01 23:59", self.faculty_id
        )
        database.unenroll_student(self.student_id, self.course_id)
        self.assertEqual(database.list_enrolled_courses(self.student_id), [])

    def test_two_assignments_sharing_a_title_stay_distinguishable(self):
        # Regression check: the student Submit tab used to key its assignment
        # dropdown by title alone, so two same-titled assignments would collide
        # and silently resolve to the wrong assignment_id.
        first_id = database.create_assignment(
            self.course_id, "Homework", "First", "INDIVIDUAL", 10, "2026-11-01 10:00", self.faculty_id
        )
        second_id = database.create_assignment(
            self.course_id, "Homework", "Second", "INDIVIDUAL", 20, "2026-11-01 10:00", self.faculty_id
        )
        self.assertNotEqual(first_id, second_id)

        database.create_submission(first_id, self.student_id, "/fake/first.pdf")
        database.create_submission(second_id, self.student_id, "/fake/second.pdf")

        submissions = {s["assignment_id"]: s["file_path"] for s in database.list_submissions_by_student(self.student_id)}
        self.assertEqual(submissions[first_id], "/fake/first.pdf")
        self.assertEqual(submissions[second_id], "/fake/second.pdf")
```
