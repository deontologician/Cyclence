from Cyclence.Calendaring import RecurringTask
from datetime import timedelta, date

class TestRecurringTask(object):

    def test_basic_check(self):
        tomorrow = date.today() + timedelta(1)
        a = RecurringTask('Eat Ham', 12, tomorrow,
                          False, 120, timedelta(3), ['hi', 'there'], 'OK then')
        b = RecurringTask('Eat Ham', timedelta(12), tomorrow,
                          False, 120, 3, ['there', 'hi', 'hi'], "OK then")
        assert a.length == b.length
        assert a.name == b.name
        assert a.allow_early == b.allow_early
        assert a.points == b.points
        assert a.tags == b.tags
        assert a.decay_length == b.decay_length
        assert a.first_due == b.first_due
        assert a.notes == b.notes
        assert a.completion_history == b.completion_history == []
        assert a.notes == b.notes
        
    def test_dueity(self):
        today = date.today()
        tomorrow = today + timedelta(1)
        yesterday = today - timedelta(1)

        a = RecurringTask('Eat Ham', 12, yesterday)
        assert a.dueity == RecurringTask.OVERDUE
        assert a.is_overdue
        assert not a.is_due
        assert not a.is_not_due
        
        b = RecurringTask('Eat Spam', 12, today)
        assert b.dueity == RecurringTask.DUE
        assert b.is_due
        assert not b.is_not_due
        assert not b.is_overdue

        c = RecurringTask('Eat Pam', 12, tomorrow)        
        assert c.dueity == RecurringTask.NOT_DUE
        assert c.is_not_due
        assert not c.is_due
        assert not c.is_overdue
