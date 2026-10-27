# Discovery: Problem Record

PDI checked by: Brinley Everson, signed in as admin, 2026-10-26

## 1. Problem states

Each state stored as number. sys_choice list>filtered Table = problem>Element = state>Language = en.

| State label | Numeric value | Sequence | Mandatory fields at this state | Refused transitions (exact message) |
|---|---|---|---|---|
| New | 101 | 1 | [Problem statement] |  [fill in after testing the progress bar] |
| Assess | 102 | 2 | | |
| Root Cause Analysis | 103 | 3 | | |
| Fix in Progress | 104 | 4 | Cause Notes | Fix notes (both required upon clicking Fix) |
| Resolved | 106 | 6 | Problem Statement, Assigned to | |
| Closed | 107 | 7 | No popups or required fields | fields still editable |

Observations:
- There is no state number 105. The numbers go 101, 102, 103, 104, 106, 107. (sys_choice)
- All six states are active (Inactive = false). (sys_choice)
- You can't pick a state from a dropdown. The State field is greyed out, and the state only changes when you click a button at the top of the form. (problem form)
- Problem tasks use their own state numbers: New 151, Assess 152, Work in Progress 154, Closed 157. (sys_choice, Table = problem_task)

## 2. Buttons at each state

The buttons at the top of the problem form change with each state. The button that moves the problem forward is in **bold**.

| State | Buttons shown |
|---|---|
| New | Follow, **Assess**, Update, Delete |
| Assess | Follow, **Confirm**, Mark Duplicate, Cancel, Update, Delete |
| Root Cause Analysis | Follow, **Fix**, Mark Duplicate, Cancel, Accept Risk, Update, Delete |
| Fix in Progress | Follow, **Resolve**, Re-Analyze, Accept Risk, Update, Delete |
| Resolved | Follow, **Complete**, Re-Analyze, Update, Delete |
| Closed | Follow, Re-Analyze, Update, Delete |

Observations:
- **Re-Analyze** is still offered at Closed (problem form header)
- **Accept Risk** appears from Root Cause Analysis onward. It matches the "Accept" decision in §1.10 of the primer. (problem form header)

## 3. Links between records

| From (table.field) | Points to | How I set it | Can you see the link from the other side? |
|---|---|---|---|
| incident: no field found | problem | **Could not link.** The incident form has no Problem field (checked the main form and the Related Records and Resolution Information tabs), and Problem was not offered in the incident list's column picker | No. The problem form has no Incidents related list |
| change_request.parent | problem | Created the change from the problem's Change Requests tab → New. The link was filled in automatically | Yes. The problem's Change Requests tab lists CHG0030001, filtered "Parent = PRB0040001" |
| kb_knowledge, field labeled "Source task" (field name not checked) | problem | Filled in automatically with PRB0040001 when the article was created from the problem | Yes, see next row |
| problem, field labeled "Primary Known Error article" (field name not checked) | kb_knowledge | Filled in automatically with "KB0010001 v0.01" after the article was created | Yes. The article's Source task points back to the problem |
| problem_task, field labeled "Problem" (field name not checked) | problem | Created from the problem's Problem Tasks tab → New. The Problem field was already filled in | Yes. The problem's Problem Tasks tab is filtered "Problem = PRB0040001" |

Observations:
- The problem form has no "Change request" field on its main form, so the problem-to-change link is stored on the change, not on the problem. (problem form; Change Requests related list)
- The problem form's related lists are: Affected CIs, Problem Tasks, Change Requests, Outages, Attached Knowledge. There is no Incidents list. (problem form)

## 4. Known error article

- Menu>Create Known Error Article
- Article number: KB0010001
- Knowledge base: Known Error (required field)
- Template: "Known Error article" is form header, has separate Workaround and Cause fields
- Fields copied from the problem: Problem statement>Short description, Workaround>Workaround, Cause notes> Case
- SYN-PROBE was copied


##Problem task types
-On the Problem Tasks tab, clicking New opens a "problem Task Models" chooser
-Options: Root Cause Analysis, General
- Match examples in §1.11
-Problem task problem field already filled


Matches:
- The six state labels match the primer exactly: New, Assess, Root Cause Analysis, Fix in Progress, Resolved, Closed. (sys_choice, Table = problem, Element = state)

Differences:
- State values skip 105 
- The All menu has no Problem module; searching "problem" returned No Results. The form opened only via /problem.do. (All menu; browser URL)
- The short description field is labeled "Problem statement" on the form. [confirm field name: short_description?] (problem form)
- State can't be edited directly; it changes only through buttons. (problem form, State field read-only)
- Buttons the primer doesn't mention: Confirm (Assess → RCA), Fix (RCA → Fix in Progress), Complete (at Resolved), Re-Analyze (reopen path), Mark Duplicate, Cancel, Accept Risk. (problem form header)
- sys_choice has no "Canceled" or "Duplicate" state, so Cancel and Mark Duplicate must end the problem some other way (not tested). (sys_choice; problem form)
- Fix notes are required when moving to Fix in Progress, not only at Resolved. (Fix dialog)

##Cleanup

I deleted all five test records, then searched each table for records with "SYN-PROBE." Each search returned nothing.

| Record | Number | Table searched | Result |
|---|---|---|---|
| Problem task | [PTASK number] | problem_task | No records |
| Change | CHG0030001 | change_request | No records |
| Incident | INC0010001 | incident | No records |
| Knowledge article | KB0010001 | kb_knowledge | No records |
| Problem | PRB0040001 | problem | No records |