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


if __name__ == "__main__":
    unittest.main()
