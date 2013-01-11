Cyclence
==========
The periodic scheduler

Introduction
----------

Most calendaring software or task tracking software has some kind of recurring
task feature that reminds the user of periodic tasks or events. Unfortunately,
the recurrence periods of these tasks are usually locked to calendar dates. So,
for example, a reminder might be provided on the first and fifteenth of every
month for an event that is supposed to recur biweekly. This is fine if the event
being scheduled truly is locked to the calendar, something like "Taxes due" or
"Pay credit card".

But many times we wish to use these scheduled events to remind ourselves of
things we need to do with some regularity, but don't particularly care if it is
linked to a particular day of the month. In addition, these tasks usually
tolerate some flexibility in when we complete them, as long as the next time the
task occurs is shifted by an amount of time equal to how late or early the task
was completed. For example, for a task like "Change the bed sheets" we might
want to be reminded to do this task every two weeks. If we are late by a few
days in changing the sheets, we don't want to be reminded again a week and a
half after changing them, we want the full two weeks again. Similarly, if we get
some free time unexpectedly and change them a few days early, we want to be
reminded that we need to change them in two weeks, not in two and a half weeks.

It is this type of duration dependent, and calendar independent tasks that
Cyclence seeks to manage. Cyclence knows when you *should* complete a task,
but it strictly adheres to reality, and doesn't expect you to constantly do
bookkeeping to match up what *should* happen with what actually *does*
happen. Life is complicated enough without your task scheduling software
insisting that you can only change your oil on the first of the month.

All of this isn't to say that Cyclence isn't judgemental about when you complete
tasks. At all times it is easy to determine what tasks are overdue, what can be
completed early, and what is fine and shouldn't be completed early (changing
your oil once a month is both wasteful and expensive!).

Cyclence aims to fulfill a need that other scheduling software does not.

## License

Copyright 2013 Josh Kuhn

Cyclence is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option)
any later version.

Cyclence is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
more details.

You should have received a copy of the GNU Affero General Public License
along with Cyclence.  If not, see <http://www.gnu.org/licenses/>.
