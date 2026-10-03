Evaluation on 6106 held-out rows from SQLiV3.csv (2256 SQL injection, 3850 normal)

| Method | Accuracy | Precision | Recall | False alarms | Missed attacks |
|---|---|---|---|---|---|
| Rules only | 73.6% | 92.1% | 31.1% | 60 | 1554 |
| ML only (threshold 0.7) | 99.3% | 100.0% | 98.3% | 1 | 39 |
| Rules + ML (SentinelWeb) | 98.4% | 97.3% | 98.3% | 61 | 39 |

Examples of attacks still missed:
- `begin dbms_lock.sleep ( 5 )`
- `create or replace function sleep ( int ) returns int as '/lib/libc.so.6','sleep' language `
- `distinct`
- `) s`
- `hi or a = a`
- `1"" ( .'. ( , ( .`
- `as`
- `PRINT @@variable`

Examples of false alarms:
- `SELECT student FROM wore UNION SELECT sang FROM pour ORDER BY habit`
- `SELECT * FROM Users WHERE Name = "" or "" = "" AND Pass = "" or "" = ""`
- `SELECT nation FROM rising UNION ALL SELECT freedom FROM pool ORDER BY dirt`
- `SELECT original,policeman FROM guide WHERE away = 'bright' UNION SELECT keep, coffee FROM `
- `SELECT height FROM chart UNION ALL SELECT parallel FROM principle ORDER BY tax`
- `SELECT automobile,large FROM sleep WHERE extra = 'biggest' UNION SELECT sheet, had FROM ra`
- `SELECT rule,cave FROM agree WHERE naturally = 'package' UNION SELECT specific, remain FROM`
- `SELECT slipped FROM drove UNION SELECT alone FROM name ORDER BY planning`

Caveat: the dataset repeats similar payloads, so scores here are optimistic. Real traffic will score lower.
