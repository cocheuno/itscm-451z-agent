## Finding: when known_error was set
- problem.known_error exists (sys_dictionary: Table = problem, Column = known_error, Type = True/False, Audit = false).
- The field is not on the problem form (checked all tabs on PRB0040001).
- sys_audit has no rows for tablename = problem, fieldname = known_error.
- Conclusion: this PDI does not record the time known_error was set.

# KPI Data Trace: Time to Known Error (TTKE)

## The formula (from primer §1.12)
TTKE = median over problems of (time known_error was set − opened_at of the first linked incident), in days.

## Term 1: when known_error was set
- Field: problem.known_error. It exists (sys_dictionary: Table = problem, Column = known_error, Type = True/False).
- Not shown on the problem form (checked every tab on the probe problem PRB0040001).
- Not audited: the dictionary entry shows Audit = false, and sys_audit has no rows for tablename = problem, fieldname = known_error.
- **Conclusion: this PDI does not record when known_error was set.**

## Term 2: opened_at of the first linked incident
- Field: incident.opened_at. It is defined on the parent table task (sys_dictionary: Table = task, Column = opened_at, Type = [Date/Time]).
- Link from incident to problem: **none exists on this PDI.** sys_dictionary has no field containing "problem" on the incident table or the task table.
- Without that link, there is no way to find "the first linked incident," so TTKE can't be calculated on this PDI yet. (Ask about this)
## Time zone note
Times on screen appear about 2 hours behind Chicago time (saved ~21:29 CT, displayed 19:29:32), so the instance likely displays US Pacific time. ServiceNow stores date/times in UTC; agents should compute TTKE from UTC values only.

## Proposed convention for recording the known_error time
Because the instance doesn't record it, agents will write one work note on the problem at the moment they mark it a known error, in a fixed format:

    [KE-SET] 2026-10-27T06:15:00Z by <agent or user>

- One line, UTC, ISO 8601 format, so code can find it with a simple text search.
- Written in the same update that sets known_error = true.
- Cross-check (assumed): the creation time (sys_created_on) of the article in the problem's "Primary Known Error article" field should be close to this time. A large gap means one of them is wrong.

## Formula with my field names
TTKE = median over problems of
  ( time of the [KE-SET] work note on the problem
    − min(incident.opened_at for incidents linked to the problem) ),
  in days, calculated in UTC.

The link between incidents and problems does not exist on this PDI yet, so "linked to the problem" has no field name until we decide how to record it.