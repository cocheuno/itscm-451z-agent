# Known Error: Payments checkout timeout after nightly batch

## 1. Symptom (as users describe it)
Customers on SYN Payments see checkout time out; the payment page spins, then fails.
Customers say the order did not go through and their card was not charged. (assumed)

## 2. When it happens
- Mostly between 02:00 and 03:00 UTC, right after the nightly batch runs 
- Started after the Payments database change on a Tuesday evening; the first timeout came the next day at 02:10 (§1.8).
- Three or Four nights a week, typically lasting 20-40 minutes (assumed)

## 3. Affected services and CIs
- Service: SYN Payments (tier 1)
- CI: database cluster syn-shared-sqlclu-prd-01
- Not affected: SYN Order Fulfillment, which uses the same cluster but doesn't run the 02:00 batch (§1.8, Kepner-Tregoe)

## 4. Workaround: steps, and who may apply them
Who may apply it: SYN Payments on-call engineer (assumed)

1. Confirm with the caller that the timeout happened between 02:00 and 03:00 UTC
2. Check the monitoring dashboard for the connection-pool alert (assumed)
3. Fail the database connection pool over to the second node of syn-shared-sqlclu-prd-01 
4. Create a test checkout in the Payments test account and confirm it completes in under five seconds (assumed)
5. Record that the work around has been applied; note time, and resolve the incident (assumed)

## 5. Known cause
Database statistics are not refreshed after the nightly batch loads data. The query plan then changes and becomes slow, connections wait on the slow query, and the connection pool runs out. The batch was extended last month (§1.8, Kepner-Tregoe).

## 6. Problem record number
PRB0040123 (assumed)

## 7. Owner
Problem analyst, SYN Payments DevOps (assumed)

## 8. Date written
2026-10-27

## 9. Date last confirmed to work
2026-10-24 (assumed)