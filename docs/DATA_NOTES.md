# DATA NOTES (profiled from the raw xlsx files, before any cleaning)

Use these numbers as ground truth for tests. Re-verify with pandas on the raw files if in doubt.

## Deals ("Deal tracker" sheet): 346 rows x 12 columns
Columns: Deal Name, Owner code, Client Code, Deal Status, Close Date (A), Closure Probability,
Masked Deal value, Tentative Close Date, Deal Stage, Product deal, Sector/service, Created Date.

- Junk: 2 rows have header text pasted into data cells (deal names Nezuko, Bugs Bunny); 1 row has null status (Tanjiro); 12 exact duplicate rows.
- Missing: Masked Deal value 181/346; Closure Probability 258; Product deal 170; Close Date (A) 318; Tentative Close Date 74; Owner 17; Sector 8.
- Status counts: Won 165, Dead 127, Open 49, On Hold 2.
- Value coverage by status: Won 64/165 (~Rs 9.5 Cr total), Open 47/49 (~Rs 68.8 Cr), Dead 54/127.
  => "Won revenue" from this board is heavily understated.
- Open pipeline concentration: two Tender deals (Sakura Rs 30.6 Cr, Luffy Rs 12.2 Cr) = ~62% of open value; all 4 open Tender deals ~77%.
- Sector values: Renewables 111, Mining 106, Railways 40, Others 28, Powerline 26, Construction 9, blank 8, DSP 7, Tender 5, Manufacturing 2, Security and Surveillance 1, Aviation 1.
  "Tender" and "DSP" are not real sectors.
- Status vs Stage conflicts: 70 Won deals at "A. Lead Generated"; 1 Dead at "G. Project Won"; Open deals at "H. Work Order Received" (1) and "M. Projects On Hold" (1); "Project Completed" lacks the letter prefix used by other stages.
- Deal Name is NOT unique: 155 unique names over 346 rows ("Sakura" x27); 43 names map to multiple client codes.
- Dates are real datetimes except the pasted-header rows. Ranges: Created 2024-08-09 to 2026-01-09; Close (A) to 2026-01-15; Tentative Close to 2026-04-01.
  48 of 49 open deals have a Tentative Close Date before 2026-09-19 (stale).

## Work Orders ("work order tracker" sheet): 176 rows x 38 columns; HEADER ON ROW 2 (row 1 blank)
- Fully empty columns: Expected Billing Month, Actual Collection Month, Collection status, Collection Date.
- Sector (clean, 6 values): Mining 100, Renewables 51, Railways 13, Powerline 6, Others 4, Construction 2.
- `Serial #` (e.g. SDPLDEAL-075) is unique (176). `Deal name masked` is not (58 unique).
- Money (all numeric floats): Amount excl GST total ~Rs 21.16 Cr (1 null: Luffy, SDPLDEAL-085);
  Billed excl GST 113 non-null, ~Rs 10.7 Cr; Collected (incl GST) 78 non-null, ~Rs 9.0 Cr; Receivable total ~Rs 3.6 Cr.
- Negatives (CORRECTED): raw counts are 6 (to-be-billed) and 11 (receivable), but most are floating-point noise (< 1 rupee).
  Material (< -Rs 1): to-be-billed 4 rows (2 of them beyond -Rs 1,000: SDPLDEAL-004 about -Rs 97.8k incl GST, SDPLDEAL-185 about -Rs 29.5k), receivable 1 row (-Rs 160).
  Also: billed > order amount on 4 rows (over-billing); collected > billed on 1 row. Use a Rs 1 tolerance when flagging.
- Both incl-GST and excl-GST columns exist: pick one and say which.
- VERIFIED identities (hold on 100% of rows): amount_incl = amount_excl x 1.18; receivable = billed_incl - collected_incl;
  to_be_billed = amount - billed (both GST bases).
- Blank billed value = not billed yet: 63 rows have billed_incl = 0 and billed_excl blank.
- Totals incl GST: order value ~Rs 24.97 Cr, billed ~Rs 12.67 Cr, collected ~Rs 9.04 Cr, receivable ~Rs 3.63 Cr, still to bill ~Rs 12.30 Cr.
- "Collected" exists only incl GST. Execution Status vs WO Status (billed) often disagree (e.g. 34 Completed orders have blank WO status).
- Status columns overlap and are dirty: Invoice Status (Fully Billed 91, Partially Billed 10, Not billed yet 8, "Billed- Visit 7", "Billed- Visit 3", Stuck), WO Status (billed) (Closed 78, Open 24), Billing Status (typo "BIlled", Update Required, Not Billable, Stuck).
- Execution Status: Completed 117, Ongoing 25, Executed until current month 12, Not Started 11, Pause / struck 4, blank 4, Partial Completed 2, Details pending from Client 1.
- "Quantities as per PO" is text mixing numbers and units ("5360 HA", "3000", "4").
- "Type of Work" is a multi-value comma-separated text field with inconsistent ordering.
- Dates are real datetimes; latest invoice date 2026-01-14.

## Joining Deals <-> Work Orders
- No clean shared key. Names overlap (52 of 58 WO names appear in Deals) but names repeat.
- Client codes differ in format: `COMPANY089` (Deals) vs `WOCOMPANY_002` (WO). Numeric parts overlap for 50 of 51 WO codes: probably the same entity (assumption).
- Owner codes are consistent across boards (OWNER_001..).
- Therefore cross-board answers are at sector / client / owner level, and the agent must say so.

## Test question ideas (verify each against pandas)
1. Open pipeline by sector, with and without the two largest deals.
2. Win rate by sector (Won vs Dead), and value coverage caveat.
3. "Energy sector this quarter" (ambiguity: energy synonym, quarter definition, stale data).
4. Work orders: billed vs collected vs receivable by sector; list negative-receivable orders.
5. Top clients by work-order value and whether they also have open deals.
6. Which owners carry the most open pipeline value.
7. "Prepare a leadership update" (headline numbers + risks + caveats).
