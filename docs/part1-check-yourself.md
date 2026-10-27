# Part 1: Check Yourself

## Question 1
*SYN Order Fulfillment has had five "order stuck in queue" incidents this month, each resolved by restarting a batch job. Which is the problem, which is the known error, and which is the workaround? What would make this a known error rather than a problem?*

Problem: Cause of incidents not specified; could potentially be the batch job freezing when a bad order is recorded
Known error: Same cause, once it's been analyzed, but before it's been resolved
Workaround: Restarting a batch job

This would be a known error rather than a problem when we know what is wrong but have not removed it.


## Question 2
*A Payments fix was deployed on October 1. On October 20 the change manager reports that the change closed as successful, so the problem should be closed. What is wrong with that reasoning, and what evidence would you ask for instead?*

Problems are not resolved until the incidents stop, so I would want to compare the incident rate before and after the fix. Additionally, because the default is W = 30 days according to the Recurrence rate after a fix row in the §1.12 table, it is 11 days too early to say the problem is gone.

## Question 3
*The problem backlog fell from 40 to 12 last quarter. Name two KPIs you would check before celebrating, and say what each would reveal.*

1. Backlog size and age - Were old problems closed without a fix?
2. Recurrence rate after fix - Once the problems were fixed, did the incidents actually stop?
