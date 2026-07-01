---
name: OUTLOOK
description: Create Outlook appointments and emails via Slang OLE automation
---

# OUTLOOK — Outlook OLE Automation via secexpr

> **Purpose:** Create Outlook calendar appointments and email drafts via Slang's `_LIB Outlook Functions` OLE automation, executed through `secexpr --safe`.

**Out of scope:** Reading mailboxes, processing attachments, calendar queries.

## Skill Identity

| Field | Value |
|-------|-------|
| **Name** | `OUTLOOK` |
| **Scope** | Create appointments and emails in the user's Outlook |
| **Inputs** | Subject, body, attendees, date/time, duration |
| **Outputs** | Outlook item saved as draft or sent |
| **Authority** | secexpr `--safe` (OLE calls don't require `--full`) |

## When to Use

- User asks to create a calendar meeting or appointment.
- User asks to draft or send an email from Outlook.

---

> **Memory:** `memory/_dormant/slang/secexpr-gotchas.md` (date literals, Outlook constants), `memory/_dormant/slang/utility-libs.md` (library reference).

## Prerequisites

- Outlook must be running on the user's workstation.
- secexpr must be available (via `H:\all-languages-env.cmd`).

## Quick Start — Create Appointment

```powershell
# 1. Write expression to temp file
Set-Content -Path "workspace/tmp/outlook-expr.txt" -Value '<SLANG_EXPRESSION>' -NoNewline
# 2. Execute (paths relative to repo root)
cmd /c "workspace\bin\secexpr-safe.cmd" "workspace\tmp\outlook-expr.txt" 2>&1
```

The agent writes the Slang expression to a temp file (with `""` for inner quotes), then passes the file path to `secexpr-safe.cmd`.

## Procedure — Create Appointment

### 1. Gather details from user

| Parameter | Required | Description |
|-----------|----------|-------------|
| Subject | Yes | Meeting title |
| Body | No | Description (empty string `""` if none) |
| Required Attendees | No | Array of kerberos IDs resolved via `Email Address()` VT, or `[]` |
| Optional Attendees | No | Array of kerberos IDs resolved via `Email Address()` VT, or `[]` |
| Start Date | Yes | Format: `DDMmmYYYY` (e.g. `27Mar2026`) |
| Start Time (hour) | Yes | 24-hour format (e.g. `14` for 2pm) |
| Duration | Yes | Minutes (e.g. `60`) |
| Timezone | No | Default: `"America/New_York"` |
| Location | No | Room or location string |
| Send | No | `True` to send immediately, `False` (default) to save as draft |
| Reminder | No | Minutes before start (default: `0`) |

### 2. Build the Slang expression and invoke

Write the Slang expression to `workspace/tmp/outlook-expr.txt` with `""` for inner quotes, then pass the file path to `secexpr-safe.cmd`:

```powershell
Set-Content -Path "workspace\tmp\outlook-expr.txt" -Value 'Link( ""_Const Microsoft Outlook"" ); Link( ""_LIB Outlook Functions"" ); O = CheckE( @Outlook::Create Instance() ); UseDatabase( Database( ""!NYC_Production"" ) ) { CheckE( @Outlook::Create Appointment Item( O, ""<SUBJECT>"", ""<BODY>"", [<REQUIRED_ATTENDEES>], TimeFromDateNew( Date( ""<DDMmmYYYY>"" ), ""<TIMEZONE>"", <HOUR>, <MIN>, 0 ), Duration := <MINUTES>, Optional Attendees := [<OPTIONAL_ATTENDEES>], MeetingStatus := Outlook::olMeeting, Busy Status := <BUSY_STATUS>, Reminder Minutes Before Start := <REMINDER>, Send := <SEND>, Save As Draft := True, Display := False ) ); };' -NoNewline
cmd /c "workspace\bin\secexpr-safe.cmd" "workspace\tmp\outlook-expr.txt" 2>&1
```

### 3. Critical rules

- **Date literals:** NEVER use bare date literals (`27Mar26`). ALWAYS use `Date( "27Mar2026" )` with 4-digit year.
- **Constants:** ALWAYS `Link( "_Const Microsoft Outlook" )` — omitting it causes `Outlook::olMeeting` to be uninitialized.
- **Quote escaping:** In the expression file, double all quotes: `""` for each `"` in the Slang expression. The file is read by cmd `for /f` and passed to secexpr.
- **Attendees format:** Resolve kerberos IDs to emails dynamically using `Email Address( "KERBEROS" )` VT inside `UseDatabase( Database( "!NYC_Production" ) )`. The kerberos securities live in Production, not in `!NYC_Source` or `DbRing::Equity Prod`. Example: `UseDatabase( Database( "!NYC_Production" ) ) { Email Address( "FIGUVI" ) };` → `Vitor.Figueira@ny.email.gs.com`. Never hardcode email strings.
- **Empty arrays:** Use `[]` for empty required/optional attendees.
- **Display := False:** Required for non-interactive (terminal) execution. Otherwise secexpr hangs waiting for GUI interaction.
- **Save As Draft := True:** Saves the appointment to the user's calendar. User can then open Outlook and Send.

### 4. Run and verify

```powershell
cmd /c "workspace\bin\secexpr-safe.cmd" "workspace\tmp\outlook-expr.txt" 2>&1
```

**Success output:** `Evaluated: Ole Object: <hex-address>`
**Failure output:** `ERROR:` message with details.

## Procedure — Create Email

Same pattern, using `@Outlook::Create Mail Item` instead:

```powershell
Set-Content -Path "workspace\tmp\outlook-expr.txt" -Value 'Link( ""_Const Microsoft Outlook"" ); Link( ""_LIB Outlook Functions"" ); O = CheckE( @Outlook::Create Instance() ); CheckE( @Outlook::Create Mail Item( O, ""<SUBJECT>"", ""<BODY>"", Body Format := Outlook::olFormatHTML, To := [<TO>], CC := [<CC>], Send := <SEND>, Save As Draft := True, Display := False ) );' -NoNewline
cmd /c "workspace\bin\secexpr-safe.cmd" "workspace\tmp\outlook-expr.txt" 2>&1
```

## Outlook Constants Reference

| Constant | Value | Description |
|----------|-------|-------------|
| `Outlook::olMeeting` | — | Meeting request (sends invites) |
| `Outlook::olNonMeeting` | — | Personal appointment (no invites) |
| `Outlook::olBusy` | — | Show as busy |
| `Outlook::olTentative` | — | Show as tentative |
| `Outlook::olOutOfOffice` | — | Show as OOO |
| `Outlook::olFree` | — | Show as free |
| `Outlook::olFormatHTML` | — | HTML email body |
| `Outlook::olFormatPlain` | — | Plain text email body |
| `Outlook::olImportanceHigh` | — | High importance |
| `Outlook::olImportanceNormal` | — | Normal importance |
| `Outlook::olImportanceLow` | — | Low importance |
| `Outlook::olAppointmentItem` | — | Appointment item type |
| `Outlook::olMailItem` | — | Mail item type |

## `@Outlook::Create Appointment Item` — Full Signature

```slang
Outlook::Create Appointment Item = Func(
    Ole Object( Outlook ),                              // from @Outlook::Create Instance()
    String( Subject ),
    String( Body ),
    Array( Required Attendees ),                        // [ "user1", "user2" ] or []
    Time( Start Time ),                                 // TimeFromDateNew( Date("27Mar2026"), "America/New_York", 14, 0, 0 )
    Time( End Time ) := LowLimit( "Time" ),             // OR use Duration
    Double( Duration ) := 0,                            // minutes (use this OR End Time)
    Double( All Day Event ) := False,
    String( Location ) := "",
    Array( Optional Attendees ) := [],
    Double( MeetingStatus ) := Outlook::olMeeting,
    Double( Busy Status ) := Outlook::olBusy,
    Double( Importance ) := Outlook::olImportanceNormal,
    Double( Reminder Minutes Before Start ) := 0,
    Double( Send ) := False,
    Double( Save As Draft ) := False,
    Array( Attachments ) := [],
    Double( Display ) := True,
    Double( ResponseRequested ) := True,
)
```

## `@Outlook::Create Mail Item` — Full Signature

```slang
Outlook::Create Mail Item = Func(
    Ole Object( Outlook ),
    String( Subject ),
    String( Body ),
    Double( Body Format ) := Outlook::olFormatPlain,
    Array( To ) := [],
    Array( CC ) := [],
    Array( BCC ) := [],
    Double( Importance ) := Outlook::olImportanceNormal,
    Double( Send ) := False,
    Double( Save As Draft ) := False,
    Array( Attachments ) := [],
    Array( Categories ) := [],
    String( Reply To ) := "",
    Double( Display ) := True,
    Double( Disable Reply To All ) := False,
    Double( Disable Forward ) := False,
)
```

## Multi-Day All-Day Events (Workaround)

**Bug:** `@Outlook::Create Appointment Item` with `All Day Event := True` sets `AllDayEvent` on the COM object but **never sets `End` or `Duration` afterward**. Outlook COM automatically resets the event to exactly 1 day when `AllDayEvent` is toggled on, ignoring any previously-set `End Time` or `Duration`.

**Workaround:** Use direct OLE calls (`O.CreateItem()`) and set properties in this exact order: `Start` → `AllDayEvent` → `End`.

**End date is exclusive** for all-day events: to cover Jul 2 and Jul 3, set `End` to Jul 4.

```slang
// Example: 2-day all-day event covering Jul 2-3, 2026
Link( ""_Const Microsoft Outlook"" );
Link( ""_LIB Outlook Functions"" );
O = @Outlook::Create Instance();
Appointment = O.CreateItem( Outlook::olAppointmentItem );
Appointment.Subject = ""Francisco - OOO"";
Appointment.Start = TimeFromDateNew( Date( ""02Jul2026"" ), ""America/New_York"", 0, 0, 0 );
Appointment.AllDayEvent = True;
Appointment.End = TimeFromDateNew( Date( ""04Jul2026"" ), ""America/New_York"", 0, 0, 0 );  // exclusive end
Appointment.BusyStatus = Outlook::olOutOfOffice;
Appointment.MeetingStatus = Outlook::olNonMeeting;
Appointment.ReminderMinutesBeforeStart = 0;
Appointment.Save();
```

For meetings with attendees, add recipients after `Save()` or use `MeetingStatus = Outlook::olMeeting` and add via `Appointment.Recipients.Add( email )`.

### Verifying calendar events

Read back from the calendar to confirm:

```slang
App = O.Application;
NS = App.GetNamespace( ""MAPI"" );
Cal = NS.GetDefaultFolder( Outlook::olFolderCalendar );
Items = Cal.Items;
Items.Sort( ""[Start]"" );
Item = Items.Find( ""[Subject] = 'Francisco - OOO'"" );
// Item.Start, Item.End, Item.Duration, Item.AllDayEvent
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Access of an uninitialized variable 'Outlook::olMeeting'` | Missing `_Const Microsoft Outlook` link | Add `Link( ""_Const Microsoft Outlook"" )` |
| `unexpected SL_SYMBOL ... Mar26` | Bare date literal in `-e` mode | Use `Date( ""27Mar2026"" )` wrapper |
| TUI error dialog / secexpr hangs | `Display := True` in non-interactive mode | Set `Display := False` |
| `Couldn't create appointment item` | Outlook not running | Start Outlook first |
| `Must set either end time or duration` | Neither End Time nor Duration given | Provide `Duration := 60` |
| All-day event only spans 1 day | Wrapper sets `AllDayEvent` before `End`, COM resets to 1 day | Use direct OLE workaround (see section above) |

## Links

- memory/slang/secexpr-gotchas.md — secexpr date literals, Outlook constants
- memory/slang/utility-libs.md — Slang utility library reference

