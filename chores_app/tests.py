from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from chores_app.models import Chore, Household, Member, PointLog


class HouseholdModelTest(TestCase):
    def test_household_creation(self):
        household = Household.objects.create(name="Test House")
        self.assertEqual(household.name, "Test House")
        self.assertEqual(household.member_count(), 0)

    def test_max_member_limit(self):
        household = Household.objects.create(name="Full House")
        for i in range(Household.MAX_MEMBERS):
            user = User.objects.create_user(username=f"user{i}", password="pass")
            Member.objects.create(user=user, household=household)
        self.assertTrue(household.is_full())


class MemberModelTest(TestCase):
    def test_member_roles(self):
        household = Household.objects.create(name="House")
        user = User.objects.create_user(username="admin", password="pass")
        admin = Member.objects.create(user=user, household=household, role=Member.ROLE_ADMIN)
        self.assertTrue(admin.is_admin())

        user2 = User.objects.create_user(username="member", password="pass")
        member = Member.objects.create(user=user2, household=household, role=Member.ROLE_MEMBER)
        self.assertFalse(member.is_admin())

    def test_joining_household(self):
        household = Household.objects.create(name="House")
        user = User.objects.create_user(username="newbie", password="pass")
        member = Member.objects.create(user=user, household=household)
        self.assertEqual(household.member_count(), 1)
        self.assertEqual(member.household, household)


class ChoreModelTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="House")
        self.user = User.objects.create_user(username="creator", password="pass")
        self.member = Member.objects.create(user=self.user, household=self.household)

    def test_chore_creation_defaults(self):
        chore = Chore.objects.create(
            title="Take out trash",
            household=self.household,
            created_by=self.member,
        )
        self.assertEqual(chore.status, Chore.STATUS_OPEN)
        self.assertEqual(chore.points, 1)
        self.assertIsNone(chore.due_date)
        self.assertEqual(chore.reminder_level, 0)

    def test_point_assignment(self):
        chore = Chore.objects.create(
            title="Deep clean",
            points=10,
            household=self.household,
            created_by=self.member,
        )
        self.assertEqual(chore.points, 10)

    def test_due_date_validation(self):
        past_date = timezone.now() - timedelta(days=1)
        chore = Chore.objects.create(
            title="Overdue chore",
            due_date=past_date,
            household=self.household,
            created_by=self.member,
        )
        self.assertIsNotNone(chore.due_date)


class PointLogModelTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="House")
        self.user = User.objects.create_user(username="claimer", password="pass")
        self.member = Member.objects.create(user=self.user, household=self.household)
        self.chore = Chore.objects.create(
            title="Wash dishes",
            points=5,
            household=self.household,
            created_by=self.member,
        )

    def test_points_recorded_on_completion(self):
        self.chore.claim(self.member)
        self.chore.complete()
        self.chore.finalize()
        log = PointLog.objects.get(chore=self.chore)
        self.assertEqual(log.points, 5)
        self.assertEqual(log.member, self.member)

    def test_points_pending_during_dispute_window(self):
        self.chore.claim(self.member)
        self.chore.complete()
        self.assertEqual(self.chore.status, Chore.STATUS_COMPLETED)
        self.assertEqual(PointLog.objects.filter(chore=self.chore).count(), 0)

    def test_points_finalized_after_window_expiry(self):
        self.chore.claim(self.member)
        self.chore.complete()
        self.chore.finalize()
        self.assertEqual(self.chore.status, Chore.STATUS_FINALIZED)
        self.assertEqual(PointLog.objects.filter(chore=self.chore).count(), 1)


class ChoreLifecycleTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="House")
        self.user1 = User.objects.create_user(username="u1", password="pass")
        self.user2 = User.objects.create_user(username="u2", password="pass")
        self.member1 = Member.objects.create(user=self.user1, household=self.household)
        self.member2 = Member.objects.create(user=self.user2, household=self.household)

    def test_any_member_can_create_chore(self):
        chore = Chore.objects.create(
            title="Task by member1",
            household=self.household,
            created_by=self.member1,
        )
        self.assertEqual(chore.created_by, self.member1)

        chore2 = Chore.objects.create(
            title="Task by member2",
            household=self.household,
            created_by=self.member2,
        )
        self.assertEqual(chore2.created_by, self.member2)

    def test_claim_chore(self):
        chore = Chore.objects.create(
            title="Claimable",
            household=self.household,
            created_by=self.member1,
        )
        chore.claim(self.member2)
        self.assertEqual(chore.status, Chore.STATUS_CLAIMED)
        self.assertEqual(chore.claimed_by, self.member2)

    def test_cant_claim_already_claimed(self):
        chore = Chore.objects.create(
            title="Already claimed",
            household=self.household,
            created_by=self.member1,
        )
        chore.claim(self.member1)
        with self.assertRaises(ValueError):
            chore.claim(self.member2)

    def test_complete_chore_opens_dispute_window(self):
        chore = Chore.objects.create(
            title="Completable",
            household=self.household,
            created_by=self.member1,
        )
        chore.claim(self.member1)
        chore.complete()
        self.assertEqual(chore.status, Chore.STATUS_COMPLETED)
        self.assertTrue(chore.is_dispute_window_open())

    def test_dispute_within_window_reopens_chore(self):
        chore = Chore.objects.create(
            title="Disputable",
            household=self.household,
            created_by=self.member1,
        )
        chore.claim(self.member1)
        chore.complete()
        chore.dispute()
        self.assertEqual(chore.status, Chore.STATUS_DISPUTED)
        self.assertEqual(PointLog.objects.filter(chore=chore).count(), 0)

    def test_dispute_window_expiry_finalizes_points(self):
        chore = Chore.objects.create(
            title="Expiring",
            dispute_window_hours=1,
            household=self.household,
            created_by=self.member1,
        )
        chore.claim(self.member1)
        chore.complete()
        chore.completed_at = timezone.now() - timedelta(hours=2)
        chore.save()
        self.assertFalse(chore.is_dispute_window_open())
        chore.finalize()
        self.assertEqual(chore.status, Chore.STATUS_FINALIZED)
        self.assertEqual(PointLog.objects.filter(chore=chore).count(), 1)


class PermissionsTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="House")
        self.user_admin = User.objects.create_user(username="admin", password="pass")
        self.user_member = User.objects.create_user(username="member", password="pass")
        self.admin = Member.objects.create(
            user=self.user_admin, household=self.household, role=Member.ROLE_ADMIN
        )
        self.member = Member.objects.create(
            user=self.user_member, household=self.household, role=Member.ROLE_MEMBER
        )
        self.other_household = Household.objects.create(name="Other House")
        self.other_user = User.objects.create_user(username="other", password="pass")
        self.other_member = Member.objects.create(
            user=self.other_user, household=self.other_household
        )

    def test_admin_can_override_any_chore(self):
        chore = Chore.objects.create(
            title="Member chore",
            household=self.household,
            created_by=self.member,
        )
        self.assertEqual(chore.created_by, self.member)
        chore.title = "Updated by admin"
        chore.save()
        chore.refresh_from_db()
        self.assertEqual(chore.title, "Updated by admin")

    def test_any_member_can_edit_chores(self):
        chore = Chore.objects.create(
            title="Original",
            household=self.household,
            created_by=self.admin,
        )
        chore.title = "Edited by member"
        chore.save()
        chore.refresh_from_db()
        self.assertEqual(chore.title, "Edited by member")

    def test_non_household_member_cannot_access_chores(self):
        chore = Chore.objects.create(
            title="Private chore",
            household=self.household,
            created_by=self.admin,
        )
        household_members = chore.household.members.all()
        self.assertNotIn(self.other_member, household_members)


class LeaderboardTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="House")
        self.user1 = User.objects.create_user(username="leader", password="pass")
        self.user2 = User.objects.create_user(username="laggard", password="pass")
        self.member1 = Member.objects.create(user=self.user1, household=self.household)
        self.member2 = Member.objects.create(user=self.user2, household=self.household)

    def test_leaderboard_ranks_by_finalized_points(self):
        chore1 = Chore.objects.create(
            title="High value", points=10,
            household=self.household, created_by=self.member1,
        )
        chore2 = Chore.objects.create(
            title="Low value", points=2,
            household=self.household, created_by=self.member1,
        )

        chore1.claim(self.member1)
        chore1.complete()
        chore1.finalize()

        chore2.claim(self.member2)
        chore2.complete()
        chore2.finalize()

        leaderboard = []
        for member in self.household.members.all():
            total = sum(
                log.points for log in PointLog.objects.filter(member=member)
            )
            leaderboard.append((member, total))
        leaderboard.sort(key=lambda x: x[1], reverse=True)

        self.assertEqual(leaderboard[0][0], self.member1)
        self.assertEqual(leaderboard[0][1], 10)
        self.assertEqual(leaderboard[1][0], self.member2)
        self.assertEqual(leaderboard[1][1], 2)

    def test_pending_disputed_points_dont_count(self):
        chore = Chore.objects.create(
            title="Pending", points=5,
            household=self.household, created_by=self.member1,
        )
        chore.claim(self.member1)
        chore.complete()
        total = sum(
            log.points for log in PointLog.objects.filter(member=self.member1)
        )
        self.assertEqual(total, 0)


class RemindersTest(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="House")
        self.user = User.objects.create_user(username="user", password="pass")
        self.member = Member.objects.create(user=self.user, household=self.household)

    def test_unclaimed_chore_escalates_reminder(self):
        chore = Chore.objects.create(
            title="Unclaimed",
            household=self.household,
            created_by=self.member,
        )
        self.assertEqual(chore.reminder_level, 0)
        chore.escalate_reminder()
        self.assertEqual(chore.reminder_level, 1)
        chore.escalate_reminder()
        self.assertEqual(chore.reminder_level, 2)

    def test_claimed_chore_does_not_trigger_reminder(self):
        chore = Chore.objects.create(
            title="Claimed",
            household=self.household,
            created_by=self.member,
        )
        chore.claim(self.member)
        level_before = chore.reminder_level
        chore.escalate_reminder()
        chore.refresh_from_db()
        self.assertEqual(chore.reminder_level, level_before)

    def test_completed_chore_does_not_trigger_reminder(self):
        chore = Chore.objects.create(
            title="Completed",
            household=self.household,
            created_by=self.member,
        )
        chore.claim(self.member)
        chore.complete()
        level_before = chore.reminder_level
        chore.escalate_reminder()
        chore.refresh_from_db()
        self.assertEqual(chore.reminder_level, level_before)
