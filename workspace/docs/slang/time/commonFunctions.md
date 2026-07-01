# Date and Time Functions -- Quick Reference

A concise lookup of date and time functions in Slang.

This guide has two parts:

1. **[Part 1: Library Functions](#part-1-library-functions-_lib-time-functions)** -- Functions from `_LIB Time Functions` (require `Link( "_LIB Time Functions" )`)
2. **[Part 2: Built-in Functions](#part-2-built-in-functions)** -- Functions available without any `Link`

For detailed examples see [workingWithTime.md](workingWithTime.md) and [examples.md](examples.md).

---

# Part 1: Library Functions (`_LIB Time Functions`)

All functions below require:

```slang
Link( "_LIB Time Functions" );
```

Source: `_LIB Time Functions` | Test: `Test: Time Functions`

---

## Table of Contents (Library)

- [Time Zone Functions](#time-zone-functions)
- [Location Functions](#location-functions)
- [Time-to-String Format Functions](#time-to-string-format-functions)
- [Elapsed-to-String Functions](#elapsed-to-string-functions)
- [String-to-Time Parsing Functions](#string-to-time-parsing-functions)
- [ISO 8601 Functions](#iso-8601-functions)
- [RFC Functions](#rfc-functions)
- [Time-to/from-Date Functions](#time-tofrom-date-functions)
- [Time-to/from-Integer Functions](#time-tofrom-integer-functions)
- [Time-to/from-Structure Functions](#time-tofrom-structure-functions)
- [Time-to/from-Epoch Functions](#time-tofrom-epoch-functions)
- [Procmon String Functions](#procmon-string-functions)
- [Elapsed / Arithmetic Functions](#elapsed--arithmetic-functions)
- [Rounding and Trimming Functions](#rounding-and-trimming-functions)
- [Comparison Functions](#comparison-functions)
- [Miscellaneous Functions](#miscellaneous-functions)

---

## Time Zone Functions

### Time::Get Time Zone

**Get the current local time zone string.**

```
/****************************************************************
** Routine: Time::Get Time Zone
****************************************************************/
Time::Get Time Zone = Func(
    Double( Use Time Zone New ) := False
)
Returns( String(), NULL )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `Use Time Zone New` | Double | `False` | If True, returns new-style time zones (e.g. `Australia/Sydney`) |

Returns the `TZ` environment variable, or falls back to the current Location object's timezone.

```slang
TZ = @Time::Get Time Zone();
// e.g. "Europe/London"

TZ New = @Time::Get Time Zone( Use Time Zone New := True );
// e.g. "America/New_York"
```

---

### Time::Set Time Zone

**Set the TZ environment variable and invalidate Current/Pricing Date.**

```
/****************************************************************
** Routine: Time::Set Time Zone
****************************************************************/
Time::Set Time Zone = Func(
    String( Time Zone )
)
Returns()
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `Time Zone` | String | Timezone string (e.g. `"America/New_York"`) |

Useful when running reports for remote books on local machines.

```slang
@Time::Set Time Zone( "America/New_York" );
```

---

### Time::Is Valid TimeZone

**Check whether a string is a valid timezone. Case-sensitive.**

```
/****************************************************************
** Routine: Time::Is Valid TimeZone
****************************************************************/
Time::Is Valid TimeZone = Func(
    String( TZ )
)
Returns( Double() )
```

Validates by checking `/sw/ficc/timezone/zoneinfo`. Uses a lazy single-check cache for one-off queries, then switches to full enumeration after 3 checks.

```slang
@Time::Is Valid TimeZone( "Europe/London" );  // True
@Time::Is Valid TimeZone( "europe/London" );  // False (case-sensitive)
@Time::Is Valid TimeZone( "Bogus/Zone" );     // False
```

---

### Time::Is Valid TimeZone New

**Like `Is Valid TimeZone` but also requires a valid continent prefix (e.g. `Europe/`, `America/`).**

```
/****************************************************************
** Routine: Time::Is Valid TimeZone New
****************************************************************/
Time::Is Valid TimeZone New = Func(
    String( TZ )
)
Returns( Double() )
```

```slang
@Time::Is Valid TimeZone New( "Europe/London" );  // True
@Time::Is Valid TimeZone New( "EST" );            // False (no continent prefix)
@Time::Is Valid TimeZone New( "Etc/UTC" );        // True (special case)
@Time::Is Valid TimeZone New( "Etc/GMT-12" );     // True (special case for IDL)
```

---

### Time::Valid TimeZones

**Return a `StructureCase` of all valid timezone names.**

```
/****************************************************************
** Routine: Time::Valid TimeZones
****************************************************************/
Time::Valid TimeZones = Func()
Returns( StructureCase() )
```

```slang
All TZs = @Time::Valid TimeZones();
// StructureCase with keys like "GMT", "EST", "Europe/London", ...
```

---

### Time::Valid TimeZones New

**Return a `StructureCase` of valid timezone names with proper continent prefixes.**

```
/****************************************************************
** Routine: Time::Valid TimeZones New
****************************************************************/
Time::Valid TimeZones New = Func()
Returns( StructureCase() )
```

Filters for continents: Africa, America, Antarctica, Arctic, Asia, Atlantic, Australia, Europe, Indian, Mideast, Pacific, plus `Etc/UTC` and `Etc/GMT-12`.

---

### Time::Time Zone From Host

**When running on Unix, returns the timezone configured by cfengine.**

```
/****************************************************************
** Routine: Time::Time Zone From Host
****************************************************************/
Time::Time Zone From Host = Func()
Returns( String() )
```

Only works on Unix hosts. Will throw on Windows.

---

### Time::Time Zone From Location

**Get the timezone string for a given location (e.g. "NYC", "LDN").**

```
/****************************************************************
** Routine: Time::Time Zone From Location
****************************************************************/
Time::Time Zone From Location = Func(
    String( Location ),
    Double( Time Zone New ) := False
)
Returns( String(), Error() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `Location` | String | -- | Location string (e.g. `"NYC"`, `"LDN"`, `"TKO"`) |
| `Time Zone New` | Double | `False` | If True, returns new-style timezone |

```slang
@Time::Time Zone From Location( "NYC" );                           // "EST5EDT"
@Time::Time Zone From Location( "LDN" );                           // "GB"
@Time::Time Zone From Location( "NYC", Time Zone New := True );    // "America/New_York"
```

---

## Location Functions

### Time::LocalToTZ

**Convert local time to a specific timezone. (DO NOT USE -- see FAQE timezone gotchas.)**

```
/****************************************************************
** Routine: Time::LocalToTZ
****************************************************************/
Time::LocalToTZ = Func(
    String( Time Zone ),
    Time = CurrentGMTime()
)
Returns( Time() )
```

---

### Time::TZToLocal

**Convert a timezone time to local time. (DO NOT USE -- see FAQE timezone gotchas.)**

```
/****************************************************************
** Routine: Time::TZToLocal
****************************************************************/
Time::TZToLocal = Func(
    Time,
    String( TZ ) = "GMT",
    Strict := False
)
Returns( Time(), Error() )
```

---

### Time::LocalToLocation

**Convert local time to a named location's time. (DO NOT USE.)**

```
/****************************************************************
** Routine: Time::LocalToLocation
****************************************************************/
Time::LocalToLocation = Func(
    String( Location ),
    Time = CurrentGMTime(),
    Double( Time Zone New ) := False
)
Returns( Time(), Error() )
```

---

### Time::LocationToLocal

**Convert location time to local time.**

```
/****************************************************************
** Routine: Time::LocationToLocal
****************************************************************/
Time::LocationToLocal = Func(
    String( Time ),
    String( Location )
)
Returns( Time(), Error() )
```

---

### Time::Convert Timezone

**Convert a time from one location to another.**

```
/****************************************************************
** Routine: Time::Convert Timezone
****************************************************************/
Time::Convert Timezone = Func(
    Time( Time ),
    String( From Location ),
    String( To Location )
)
Returns( Time() )
```

```slang
NYC Time = @Time::Convert Timezone( Time(), "LDN", "NYC" );
```

---

### Time::FromTimeAndLocation

**Convert "HH:MM Location" to local time. Useful in config.**

```
/****************************************************************
** Routine: Time::FromTimeAndLocation
****************************************************************/
Time::FromTimeAndLocation = Func(
    String( Time ),
    Location := GetEnv( "Location" ),
    Double( Time Zone New ) := False
)
Returns( Time() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `Time` | String | -- | e.g. `"18:00 LDN"` |
| `Location` | String | `GetEnv("Location")` | Target location |
| `Time Zone New` | Double | `False` | Use new-style timezones |

```slang
// Convert 6pm LDN to local time, regardless of where you are
Exit Time = @Time::FromTimeAndLocation( "18:00 LDN", Location := "NYC" );
```

---

## Time-to-String Format Functions

### Time::HHMM

**Format as `HH:MM`.**

```
/****************************************************************
** Routine: Time::HHMM
****************************************************************/
Time::HHMM = Func(
    Any( aTime ),
    String( delimiter ) := ":",
    TZ := @Time::Get Time Zone()
)
Returns( String(), Error() )
```

```slang
@Time::HHMM( Time( "00:00:00.123" ) );   // "00:00"
```

---

### Time::HMMpm

**Format as `H:MMam/pm` (12-hour clock).**

```
/****************************************************************
** Routine: Time::HMMpm
****************************************************************/
Time::HMMpm = Func(
    Any( aTime ),
    String( delimiter ) := ":",
    TZ := @Time::Get Time Zone()
)
Returns( String(), Error() )
```

```slang
@Time::HMMpm( Time( "17:00:00" ) );   // " 5:00pm"
@Time::HMMpm( Time( "00:00:00" ) );   // "12:00am"
```

---

### Time::HHMMSS

**Format as `HH:MM:SS`.**

```
/****************************************************************
** Routine: Time::HHMMSS
****************************************************************/
Time::HHMMSS = Func(
    Time( aTime ),
    String( delimiter ) := ":",
    TZ := @Time::Get Time Zone()
)
Returns( String(), Error() )
```

```slang
@Time::HHMMSS( Time( "01:23:45.678" ) );   // "01:23:45"
```

---

### Time::HHMMSSWithMilliseconds

**Format as `HH:MM:SS.mmm`.**

```
/****************************************************************
** Routine: Time::HHMMSSWithMilliseconds
****************************************************************/
Time::HHMMSSWithMilliseconds = Func(
    Time( aTime ),
    String( Delimiter ) := ":",
    String( MSecDelimiter ) := "."
)
Returns( String(), Error() )
```

```slang
@Time::HHMMSSWithMilliseconds( Time( "17:05:19.517" ) );   // "17:05:19.517"
```

---

### Time::DDMMMYY HHMM

**Format as `DDMmmYY HH:MM` (e.g. `"01Mar05 03:21"`). Day padded with leading zero.**

```
/****************************************************************
** Routine: Time::DDMMMYY HHMM
****************************************************************/
Time::DDMMMYY HHMM = Func(
    Any( Time ),
    String( Delimiter ) := ":"
)
Returns( String(), Error() )
```

```slang
@Time::DDMMMYY HHMM( Time( "1Mar05 3:21" ) );   // "01Mar05 03:21"
```

---

### Time::DDMMMYY HHMMSS

**Format as `DDMmmYY HH:MM:SS` (e.g. `" 1Mar05 03:21:45"`). Day padded with space.**

```
/****************************************************************
** Routine: Time::DDMMMYY HHMMSS
****************************************************************/
Time::DDMMMYY HHMMSS = Func(
    Time( Time ) = CurrentGMTime(),
    GMT := False
)
Returns( String(), Error() )
```

```slang
@Time::DDMMMYY HHMMSS( Time( "1Mar05 3:21:45" ) );   // " 1Mar05 03:21:45"
```

---

### Time::DDMMYYYY HHMMSS

**Format as `DD/MM/YYYY HH:MM:SS`.**

```
/****************************************************************
** Routine: Time::DDMMYYYY HHMMSS
****************************************************************/
Time::DDMMYYYY HHMMSS = Func(
    Any( Time ) = CurrentGMTime(),
    Double( PadZero ) = True,
    Double( Trim ) = False,
    TZ := GetEnv( "TZ" )
)
Returns( String(), Error() )
```

```slang
@Time::DDMMYYYY HHMMSS( Time( "31Dec2005 12:01:33 am" ) );   // "31/12/2005 00:01:33"
```

---

### Time::DDMMMYYYY HHMMSS

**Format as `DDMmmYYYY HH:MM:SS`.**

```
/****************************************************************
** Routine: Time::DDMMMYYYY HHMMSS
****************************************************************/
Time::DDMMMYYYY HHMMSS = Func(
    Any( Time ) = CurrentGMTime(),
    Double( PadZero ) = False,
    Double( Trim ) = False,
    TZ := GetEnv( "TZ" )
)
Returns( String(), Error() )
```

```slang
@Time::DDMMMYYYY HHMMSS( Time( "01Dec2005 12:01:33 am" ), True );   // "01Dec2005 00:01:33"
@Time::DDMMMYYYY HHMMSS( Time( "01Dec2005 12:01:33 am" ) );         // " 1Dec2005 00:01:33"
```

---

### Time::MMDDYYYY HHMM

**Format as `MM/DD/YY HH:MM` (or 4-digit year with named arg).**

```
/****************************************************************
** Routine: Time::MMDDYYYY HHMM
****************************************************************/
Time::MMDDYYYY HHMM = Func(
    Time( Time ) = CurrentGMTime(),
    Double( Four Digit Year ) := False
)
Returns( String(), Error() )
```

```slang
@Time::MMDDYYYY HHMM( Time( "1Mar05 3:21" ), Four Digit Year := True );   // "03/01/2005 03:21"
@Time::MMDDYYYY HHMM( Time( "1Mar05 3:21" ) );                            // "03/01/05 03:21"
```

---

### Time::MMDDYYYY HHMMSS

**Format as `MM/DD/YY HH:MM:SS` (or 4-digit year with named arg).**

```
/****************************************************************
** Routine: Time::MMDDYYYY HHMMSS
****************************************************************/
Time::MMDDYYYY HHMMSS = Func(
    Time( Time ) = CurrentGMTime(),
    Double( Four Digit Year ) := False
)
Returns( String(), Error() )
```

```slang
@Time::MMDDYYYY HHMMSS( Time( "1Mar05 3:21" ), Four Digit Year := True );   // "03/01/2005 03:21:00"
```

---

### Time::YYYYMMDD HHMMSS

**Format as `YYYYMMDD HH:MM:SS.mmm` (GMT by default).**

```
/****************************************************************
** Routine: Time::YYYYMMDD HHMMSS
****************************************************************/
Time::YYYYMMDD HHMMSS = Func(
    Time( CTime ) = CurrentGMTime(),
    Milliseconds := True,
    GMT := True,
    String( DT Delimiter ) := " "
)
Returns( String() )
```

```slang
T = Time( "1Jan08 00:00:00 GMT" ) + 0.9995;
@Time::YYYYMMDD HHMMSS( T, Milliseconds := True, GMT := True );     // "20080101 00:00:01.000"
@Time::YYYYMMDD HHMMSS( T, Milliseconds := False, GMT := True );    // "20080101 00:00:01"
```

---

### Time::YYYYMMDD HHMMSSSb

**Flexible YYYYMMDD + time format with timezone, date, and subsecond control.**

```
/****************************************************************
** Routine: Time::YYYYMMDD HHMMSSSb
****************************************************************/
Time::YYYYMMDD HHMMSSSb = Func(
    String( TZ ),
    Time( CTime ) = CurrentGMTime(),
    Date( Date ) = Pricing Date( "Security Database" ),
    Double( SubSec ) := True,
    String( Date Delimiter ) := "",
    String( DateTime Delimiter ) := " "
)
Returns( String(), Error() )
```

```slang
@Time::YYYYMMDD HHMMSSSb( "Europe/London", T, D );
// "20070101 12:15:30.123"

@Time::YYYYMMDD HHMMSSSb( "Europe/London", T, D, SubSec := False, Date Delimiter := "-", DateTime Delimiter := "T" );
// "2007-01-01T12:15:30"
```

---

### Time::To YYYYMMDDHHMMSS

**Format as compact `YYYYMMDDHHMMSS` with configurable delimiters.**

```
/****************************************************************
** Routine: Time::To YYYYMMDDHHMMSS
****************************************************************/
Time::To YYYYMMDDHHMMSS = Func(
    Time( aTime ),
    String( Delimiter ) := "",
    String( YT delimiter ) := "",
    String( Date Delimiter ) := "",
    TZ := GetEnv( "TZ" )
)
Returns( String(), Error() )
```

```slang
Now = Time( "1Mar05 3:21:45" );
@Time::To YYYYMMDDHHMMSS( Now );
// "20050301032145"

@Time::To YYYYMMDDHHMMSS( Now, Delimiter := ":", YT delimiter := " ", Date Delimiter := "/" );
// "2005/03/01 03:21:45"
```

---

### Time::To YYMMDDHHMMSS

**Format as compact `YYMMDDHHMMSS` with configurable delimiters.**

```
/****************************************************************
** Routine: Time::To YYMMDDHHMMSS
****************************************************************/
Time::To YYMMDDHHMMSS = Func(
    Time( aTime ),
    String( Delimiter ) := "",
    String( YT delimiter ) := "",
    String( Date Delimiter ) := "",
    TZ := GetEnv( "TZ" )
)
Returns( String(), Error() )
```

```slang
Now = Time( "1Mar05 3:21:45" );
@Time::To YYMMDDHHMMSS( Now );   // "050301032145"
```

---

### Time::To YYYYMMDDHHMMSSmmm

**Format as `YYYYMMDDHHMMSS.mmm` (with milliseconds).**

```
/****************************************************************
** Routine: Time::To YYYYMMDDHHMMSSmmm
****************************************************************/
Time::To YYYYMMDDHHMMSSmmm = Func(
    Time( aTime ),
    String( delimiter ) := "",
    String( YT delimiter ) := "",
    String( Date Delimiter ) := "",
    TZ := GetEnv( "TZ" )
)
Returns( String(), Error() )
```

```slang
@Time::To YYYYMMDDHHMMSSmmm( Time( "23May10 15:23:45.123" ) );   // "20100523152345.123"
```

---

### Time::CurrentGMTYYYYMMDDHHMMSS

**Format current (or given) GMT time as `YYYYMMDDHHMMSS`, optionally with milliseconds.**

```
/****************************************************************
** Routine: Time::CurrentGMTYYYYMMDDHHMMSS
****************************************************************/
Time::CurrentGMTYYYYMMDDHHMMSS = Func(
    Time( SetTime ) = CurrentGMTime(),
    Double( Include Milliseconds ) := FALSE,
    Double( Millisecond Precision ) := 3,
    String( Millisecond Delimiter ) := ""
)
Returns( String(), Error() )
```

```slang
@Time::CurrentGMTYYYYMMDDHHMMSS( Time( "31Dec2005 12:01:33.123 am" ) );
// "20051231000133"

@Time::CurrentGMTYYYYMMDDHHMMSS( Time( "31Dec2005 12:01:33.123 am" ), Include Milliseconds := True );
// "20051231000133123"
```

---

### Time::ToString

**Format a time as string with configurable verbosity.**

```
/****************************************************************
** Routine: Time::ToString
****************************************************************/
Time::ToString = Func(
    Time( T ),
    Double( Terse ) := False,
    Double( Suppress Day ) := Terse,
    Double( Suppress Date ) := Terse,
    Double( Suppress Seconds ) := False,
    Date( Relative Date ) := Today()
)
Returns( String() )
```

```slang
@Time::ToString( CurrentTime(), Terse := True );
// Compact form, e.g. "14:30"
```

---

### Time::ToStringWithMilliseconds

**Format time as string with millisecond precision.**

```
/****************************************************************
** Routine: Time::ToStringWithMilliseconds
****************************************************************/
Time::ToStringWithMilliseconds = Func(
    Time( T ),
    String( DateFormat ) = "%a %e%h%y %T",
    String( MSecDelimiter ) := ".",
    Any( TZ ) := Null
)
Returns( String() )
```

```slang
@Time::ToStringWithMilliseconds( CurrentTime() );
// "Wed 18Feb26 14:30:15.123"
```

---

### Time::Compact24HTime

**Compact 24-hour clock format.**

```
/****************************************************************
** Routine: Time::Compact24HTime
****************************************************************/
Time::Compact24HTime = Func(
    Time( Arg ),
    Double( NormalTimeOnError ) := False
)
Returns( String(), Error() )
```

---

### Time::OMATimeFormat

**Format for OMA: `DD-MMM-YYYY HH:MM:SS` in GMT.**

```
/****************************************************************
** Routine: Time::OMATimeFormat
****************************************************************/
Time::OMATimeFormat = Func(
    Time( Time )
)
Returns( String() )
```

```slang
@Time::OMATimeFormat( TimeFromDateNew( Date( "1Jan07" ), "GMT", 1, 2, 3 ) );
// "01-Jan-2007 01:02:03"
```

---

### Time::Sybase Time Format

**Format for Sybase: `YYYY-MM-DD HH:MM:SS.MMM`.**

```
/****************************************************************
** Routine: Time::Sybase Time Format
****************************************************************/
Time::Sybase Time Format = Func(
    Time( Time )
)
Returns( String() )
```

---

### Time::Sybase DateTime Format

**DateTime for Sybase: `YYYY-MM-DD HH:MM:SS.MMM` (with optional timezone).**

```
/****************************************************************
** Routine: Time::Sybase DateTime Format
****************************************************************/
Time::Sybase DateTime Format = Func(
    Time( Time ),
    Any( TimeZone ) := NULL
)
Returns( String() )
```

---

### Time::UDB DateTime Format

**Format for UDB: `YYYY-MM-DD-HH.MM.SS.MMMMMM`.**

```
/****************************************************************
** Routine: Time::UDB DateTime Format
****************************************************************/
Time::UDB DateTime Format = Func(
    Time( Time ),
    Double( GMT ) := False,
    Any( TimeZone ) := If( GMT ) "UTC" : NULL
)
Returns( String() )
```

---

## Elapsed-to-String Functions

### Time::SecondsToString

**Convert elapsed seconds to a human-readable string like `"1h 5m 3s"`.**

```
/****************************************************************
** Routine: Time::SecondsToString
****************************************************************/
Time::SecondsToString = Func(
    Double( T ),
    Double( nSignificant ) = 2,
    Double( Decimal Places ) = 0
)
Returns( String() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `T` | Double | -- | Seconds to format |
| `nSignificant` | Double | `2` | Number of time units to show |
| `Decimal Places` | Double | `0` | Sub-second decimal places |

```slang
@Time::SecondsToString( 3661, 1 );   // "1h"
@Time::SecondsToString( 3661, 2 );   // "1h 1m"
@Time::SecondsToString( 3661, 3 );   // "1h 1m 1s"
```

---

### Time::SecondsToHHMMSS

**Elapsed seconds as `HH:MM:SS`.**

```
/****************************************************************
** Routine: Time::SecondsToHHMMSS
****************************************************************/
Time::SecondsToHHMMSS = Func(
    Double( Seconds )
)
Returns( String() )
```

---

### Time::SecondsToDDDHHMMSS

**Elapsed seconds as `DDD:HH:MM:SS`.**

```
/****************************************************************
** Routine: Time::SecondsToDDDHHMMSS
****************************************************************/
Time::SecondsToDDDHHMMSS = Func(
    Double( Seconds )
)
Returns( String() )
```

---

### Time::SecondsToHHMM

**Elapsed seconds as `HH:MM`.**

```
/****************************************************************
** Routine: Time::SecondsToHHMM
****************************************************************/
Time::SecondsToHHMM = Func(
    Double( Seconds )
)
Returns( String() )
```

---

### Time::SecondsToMSS

**Elapsed seconds as `M:SS`.**

```
/****************************************************************
** Routine: Time::SecondsToMSS
****************************************************************/
Time::SecondsToMSS = Func(
    Double( Seconds )
)
Returns( String() )
```

---

### Time::Time Difference As String

**Human-readable difference between two times.**

```
/****************************************************************
** Routine: Time::Time Difference As String
****************************************************************/
Time::Time Difference As String = Func(
    Time( T1 ),
    Time( T2 ),
    String( Resolution ) := "Second",
    Double( Zero Diff As Empty String ) := True
)
Returns( String(), Error() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `T1` | Time | -- | First time |
| `T2` | Time | -- | Second time |
| `Resolution` | String | `"Second"` | Finest unit: `"Year"`, `"Week"`, `"Day"`, `"Hour"`, `"Minute"`, `"Second"` |
| `Zero Diff As Empty String` | Double | `True` | Return `""` instead of `"0 Seconds"` for zero diff |

```slang
T = CurrentTime();
@Time::Time Difference As String( T, T - 3665 );
// "1 Hour 1 Minute 5 Seconds"

@Time::Time Difference As String( T, T - 3665, Resolution := "Hour" );
// "1 Hour"

@Time::Time Difference As String( T, T );
// ""

@Time::Time Difference As String( T, T, Zero Diff As Empty String := False );
// "0 Seconds"
```

---

## String-to-Time Parsing Functions

### Time::YYYYMMDDHHMMSS

**Parse `"YYYYMMDDHHMMSS"` string to Time.**

```
/****************************************************************
** Routine: Time::YYYYMMDDHHMMSS
****************************************************************/
Time::YYYYMMDDHHMMSS = Func(
    String( YYYYMMDDHHMMSS ),
    String( TZ ) := ""
)
Returns( Time(), Error() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `YYYYMMDDHHMMSS` | String | -- | Exactly 14 characters |
| `TZ` | String | `""` | Empty = local timezone. Warning: unrecognized TZ defaults to UTC |

```slang
@Time::YYYYMMDDHHMMSS( "20100916180328" );
```

---

### Time::YYYYMMDDHHMMSSSb

**Parse `"YYYYMMDDHHMMSS.mmm"` string (with optional subseconds).**

```
/****************************************************************
** Routine: Time::YYYYMMDDHHMMSSSb
****************************************************************/
Time::YYYYMMDDHHMMSSSb = Func(
    String( YYYYMMDDHHMMSSSb )
)
Returns( Time(), Error() )
```

```slang
@Time::YYYYMMDDHHMMSSSb( "20100916180328.572" );
```

---

### Time::YYYYMMDDHHMM

**Parse `"YYYYMMDDHHMM"` (12 chars, no seconds).**

```
/****************************************************************
** Routine: Time::YYYYMMDDHHMM
****************************************************************/
Time::YYYYMMDDHHMM = Func(
    String( YYYYMMDDHHMM )
)
Returns( Time(), Error() )
```

---

### Time::TimeFromDateTimeString

**Parse `"DateStr HH:MM:SS"` to Time. Handles hours > 24.**

```
/****************************************************************
** Routine: Time::TimeFromDateTimeString
****************************************************************/
Time::TimeFromDateTimeString = Func(
    String( strDateTime )
)
Returns( Time() )
```

```slang
@Time::TimeFromDateTimeString( "01Aug99 23:00:00" );
@Time::TimeFromDateTimeString( "01Aug99 25:00:00" );  // rolls past midnight
```

---

### Time::TimeFromDateTimeStringPM

**Like `TimeFromDateTimeString` but also handles AM/PM suffix.**

```
/****************************************************************
** Routine: Time::TimeFromDateTimeStringPM
****************************************************************/
Time::TimeFromDateTimeStringPM = Func(
    String( strDateTime )
)
Returns( Time() )
```

```slang
@Time::TimeFromDateTimeStringPM( "01Aug99 11:00:00pm" );
@Time::TimeFromDateTimeStringPM( "01Aug99 11:00:00 PM" );
@Time::TimeFromDateTimeStringPM( "01Aug99 12:20:00 AM" );
```

---

### Time::FromStringWithMilliseconds

**Parse a time string (e.g. `"Tue 18Mar03 12:50:52.123"`) preserving milliseconds.**

```
/****************************************************************
** Routine: Time::FromStringWithMilliseconds
****************************************************************/
Time::FromStringWithMilliseconds = Func(
    String( TimeStr ),
    String( TimeZone ) = ""
)
Returns( Time() )
```

---

### Time::FromDateAndTimeString

**Construct a `Time()` from a `Date()` and a time string in a given timezone.**

```
/****************************************************************
** Routine: Time::FromDateAndTimeString
****************************************************************/
Time::FromDateAndTimeString = Func(
    Date( Date ),
    String( TimeString ),
    TZ := GetEnv( "TZ" ),
    Double( Milliseconds ) := False
)
Returns( Time() )
```

```slang
@Time::FromDateAndTimeString( Date( "11Nov2005" ), "17:00:00", TZ := "US/Eastern" );
// 5pm Eastern on 11/11/2005
```

---

### Time::FromYYYYMMDDHHMMSSString

**Parse `"YYYY/MM/DD HH:MM:SS"` with configurable delimiters.**

```
/****************************************************************
** Routine: Time::FromYYYYMMDDHHMMSSString
****************************************************************/
Time::FromYYYYMMDDHHMMSSString = Func(
    String( in ),
    String( DTDelim ) := " ",
    String( DDelim ) := "/",
    String( TDelim ) := ":",
    String( TZ ) := GetEnv( "TZ" )
)
Returns( Time() )
```

---

### Time::From DDMMYYYY HHMMSS

**Parse UK-format date/time `"DD/MM/YYYY HH:MM:SS"`.**

```
/****************************************************************
** Routine: Time::From DDMMYYYY HHMMSS
****************************************************************/
Time::From DDMMYYYY HHMMSS = Func(
    String( TimeString ),
    TZ := GetEnv( "TZ" ),
    String( Separator ) := "/",
    String( DTDelim ) := " "
)
Returns( Time() )
```

```slang
@Time::From DDMMYYYY HHMMSS( "06/12/2011 15:46:54" );
```

---

### Time::From YYYYMMDD HHMMSS

**Parse `"YYYYMMDD HH:MM:SS"` to Time.**

```
/****************************************************************
** Routine: Time::From YYYYMMDD HHMMSS
****************************************************************/
Time::From YYYYMMDD HHMMSS = Func(
    String( TimeString ),
    TZ := GetEnv( "TZ" ),
    String( DTDelim ) := " ",
    Double( Milliseconds ) := False
)
Returns( Time() )
```

```slang
@Time::From YYYYMMDD HHMMSS( "20090305 15:23:45" );
@Time::From YYYYMMDD HHMMSS( "20090305 15:23:45.123", Milliseconds := True );
```

---

### Time::FromYYYYMMDDHHMMSSmmmString

**Parse `"YYYY-MM-DD HH:MM:SS.mmm"` with configurable delimiters and timezone.**

```
/****************************************************************
** Routine: Time::FromYYYYMMDDHHMMSSmmmString
****************************************************************/
Time::FromYYYYMMDDHHMMSSmmmString = Func(
    String( in ),
    String( DTDelim ) := " ",
    String( DDelim ) := "/",
    String( TDelim ) := ":",
    String( MDelim ) := ".",
    String( Timezone ) := "GMT"
)
Returns( Time() )
```

```slang
@Time::FromYYYYMMDDHHMMSSmmmString( "2024-02-15 08:15:00.000", DDelim := "-" );
```

---

### Time::FromYYYYMMMDDHHMMSSmmmString

**Parse `"YYYY/mmm/DD HH:MM:SS.mmm"` (month as 3-letter abbreviation).**

```
/****************************************************************
** Routine: Time::FromYYYYMMMDDHHMMSSmmmString
****************************************************************/
Time::FromYYYYMMMDDHHMMSSmmmString = Func(
    String( in ),
    String( DTDelim ) := " ",
    String( DDelim ) := "/",
    String( TDelim ) := ":",
    String( MDelim ) := ".",
    String( Timezone ) := "GMT"
)
Returns( Time() )
```

```slang
@Time::FromYYYYMMMDDHHMMSSmmmString( "2024/jul/01 08:48:15.841" );
```

---

### Time::From UDB DateTime Format

**Parse UDB format `"YYYY-MM-DD-HH.MM.SS.MMMMMM"` to Time.**

```
/****************************************************************
** Routine: Time::From UDB DateTime Format
****************************************************************/
Time::From UDB DateTime Format = Func(
    String( Time String )
)
Returns( Time(), Error() )
```

```slang
@Time::From UDB DateTime Format( "2024-04-24-10.30.00.123456" );
// Wed 24Apr24 10:30:00 am
```

---

### Time::HHMMSSToSeconds

**Parse `"HH:MM:SS"` to seconds since midnight.**

```
/****************************************************************
** Routine: Time::HHMMSSToSeconds
****************************************************************/
Time::HHMMSSToSeconds = Func(
    String( HHMMSS )
)
Returns( Double() )
```

```slang
@Time::HHMMSSToSeconds( "01:30:00" );   // 5400
```

---

### Time::ConvertISO8601ToGMT

**Parse ISO 8601 `"YYYY-MM-DDTHH:MM:SS+/-ZZ:ZZ"` to GMT. (Deprecated: use `From ISO DateTime`.)**

```
/****************************************************************
** Routine: Time::ConvertISO8601ToGMT
****************************************************************/
Time::ConvertISO8601ToGMT = Func(
    String( LongTimeString ),
    Double( DecimalNotation ) = 0
)
Returns( Time(), Error() )
```

---

## ISO 8601 Functions

### Time::To ISO DateTime

**Format a Time as an ISO 8601 string with full control.**

```
/****************************************************************
** Routine: Time::To ISO DateTime
****************************************************************/
Time::To ISO DateTime = Func(
    Time( Time ) = CurrentTime(),
    Double( Precision ) := 0,
    Double( Extended ) := True,
    Double( Zulu ) := False,
    Double( UTC Offset ) := False,
    String( Time Zone ) := ""
)
Returns( String(), Error() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `Precision` | Double | `0` | Fractional-second digits (0-9) |
| `Extended` | Double | `True` | Use `-` and `:` delimiters |
| `Zulu` | Double | `False` | Render in UTC with `Z` suffix |
| `UTC Offset` | Double | `False` | Append `+/-HH:MM` offset |
| `Time Zone` | String | `""` | Convert to this timezone first |

```slang
T = Time( "28Feb06 01:23:45.123" );

@Time::To ISO DateTime( T );
// "2006-02-28T01:23:45"

@Time::To ISO DateTime( T, Zulu := True );
// "2006-02-28T06:23:45Z"

@Time::To ISO DateTime( T, Precision := 3, UTC Offset := True );
// "2006-02-28T01:23:45.123-05:00"

@Time::To ISO DateTime( T, Extended := False, Precision := 3, UTC Offset := True );
// "20060228T012345.123-0500"
```

---

### Time::From ISO DateTime

**Parse an ISO 8601 string to Time. Supports extended and basic formats, with or without timezone offset.**

```
/****************************************************************
** Routine: Time::From ISO DateTime
****************************************************************/
Time::From ISO DateTime = Func(
    String( ISO DateTime ),
    String( Local Time Zone ) := ""
)
Returns( Time(), Error() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ISO DateTime` | String | -- | ISO 8601 string |
| `Local Time Zone` | String | `""` | TZ to use when no zone designator in string |

Supported formats:
- `YYYY-MM-DDThh:mm:ss`, `YYYYMMDDThhmmss`
- `...Z`, `...+HH:MM`, `...-HHMM`
- Fractional seconds: `...T12:34:56.789Z`

```slang
@Time::From ISO DateTime( "2006-02-28T01:23:45Z" );
@Time::From ISO DateTime( "2006-02-28T01:23:45-05:00" );
@Time::From ISO DateTime( "20060228T012345Z" );
@Time::From ISO DateTime( "2006-02-28T01:23:45", Local Time Zone := "Asia/Hong_Kong" );
```

---

## RFC Functions

### Time::From RFC1123

**Parse an RFC 1123 string (e.g. `"Tue, 9 Nov 2010 17:45:05 GMT"`).**

```
/****************************************************************
** Routine: Time::From RFC1123
****************************************************************/
Time::From RFC1123 = Func(
    String( Time )
)
Returns( Time() )
```

---

### Time::To RFC1123

**Format a Time as RFC 1123 string.**

```
/****************************************************************
** Routine: Time::To RFC1123
****************************************************************/
Time::To RFC1123 = Func(
    Time( Time )
)
Returns( String() )
```

```slang
@Time::To RFC1123( Time( "9Nov2010 17:45:05 GMT" ) );
// "Tue,  9 Nov 2010 17:45:05 GMT"
```

---

### Time::To RFC822

**Format a Time as RFC 822 string (e.g. `"Fri, 21 Nov 2014 10:47:30 -0500"`).**

```
/****************************************************************
** Routine: Time::To RFC822
****************************************************************/
Time::To RFC822 = Func(
    Time( Time ),
    String( TZ ) := Check( GetEnv( "TZ" ) )
)
Returns( String(), Error() )
```

---

## Time-to/from-Date Functions

### Time::GetDateFromTime

**Extract the date from a Time, using new-style timezone resolution.**

```
/****************************************************************
** Routine: Time::GetDateFromTime
****************************************************************/
Time::GetDateFromTime = Func(
    Time( Time )
)
Returns( Date() )
```

```slang
D = @Time::GetDateFromTime( Time( "27Mar2008 12:00:00 pm GMT" ) );
```

---

### Time::From Date And Time

**Construct Time from a Date and the time-of-day part of another Time.**

```
/****************************************************************
** Routine: Time::From Date And Time
****************************************************************/
Time::From Date And Time = Func(
    Date( Date ),
    Time( Time ),
    TZ := GetEnv( "TZ" )
)
Returns( Time() )
```

```slang
@Time::From Date And Time( Date( "27Mar2008" ), Time( "12:01:33.123" ), TZ := "Europe/London" );
```

---

### Time::Midnight

**Get midnight on a given date in a given timezone.**

```
/****************************************************************
** Routine: Time::Midnight
****************************************************************/
Time::Midnight = Func(
    Date( Date ),
    String( TZ )
)
Returns( Time() )
```

```slang
M = @Time::Midnight( Date( "28Mar05" ), "Europe/London" );
```

---

### Time::Seconds Since Midnight

**Seconds elapsed since midnight in the given timezone.**

```
/****************************************************************
** Routine: Time::Seconds Since Midnight
****************************************************************/
Time::Seconds Since Midnight = Func(
    Time( Time ),
    String( TZ )
)
Returns( Double() )
```

```slang
@Time::Seconds Since Midnight( Time( "28Mar05 1:30pm GMT" ), "Europe/London" );
```

---

## Time-to/from-Integer Functions

### Time::ToIntegerTimestamp

**Convert time to a compact integer `HHMMSSmmm`.**

```
/****************************************************************
** Routine: Time::ToIntegerTimestamp
****************************************************************/
Time::ToIntegerTimestamp = Func(
    Time( T ) = CurrentTime()
)
Returns( Double() )
```

---

### Time::FromIntegerTimestamp

**Convert an integer timestamp `HHMMSSmmm` back to Time (on a given date).**

```
/****************************************************************
** Routine: Time::FromIntegerTimestamp
****************************************************************/
Time::FromIntegerTimestamp = Func(
    Double( D ),
    Date( Date ) = Today()
)
Returns( Time() )
```

---

### Time::FromMillisecondsSinceMidnight

**Convert milliseconds-since-midnight (e.g. Reuters QUOTIM_MS) to the most recent Time.**

```
/****************************************************************
** Routine: Time::FromMillisecondsSinceMidnight
****************************************************************/
Time::FromMillisecondsSinceMidnight = Func(
    Double( Milliseconds ),
    Time( Now ),
    String( Time Zone ) := "UTC"
)
Returns( Time() )
```

---

## Time-to/from-Structure Functions

### Time::TimeToStruct

**Convert Time to a Structure with Day, Month, Year, Hour, etc.**

```
/****************************************************************
** Routine: Time::TimeToStruct
****************************************************************/
Time::TimeToStruct = Func(
    Time( My Time ),
    String( Timezone )
)
Returns( Structure() )
```

Returns structure with keys: `Day`, `Month`, `Year`, `YearDay`, `Hour`, `Minute`, `Second`, `Millisecond`.

---

### Time::StructToTime

**Convert a Structure back to a Time.**

```
/****************************************************************
** Routine: Time::StructToTime
****************************************************************/
Time::StructToTime = Func(
    Structure( Struct ),
    String( Timezone )
)
Returns( Time() )
```

---

## Time-to/from-Epoch Functions

### Time::ToUnixTimestamp

**Convert Time to Unix epoch seconds (rounded to nearest second).**

```
/****************************************************************
** Routine: Time::ToUnixTimestamp
****************************************************************/
Time::ToUnixTimestamp = Func(
    Time( T ) = CurrentTime()
)
Returns( Double() )
```

```slang
@Time::ToUnixTimestamp( @Time::From ISO DateTime( "2006-02-28T01:23:45Z" ) );
// 1141089825
```

---

### Time::ToEpochMilli

**Convert Time to milliseconds since epoch.**

```
/****************************************************************
** Routine: Time::ToEpochMilli
****************************************************************/
Time::ToEpochMilli = Func(
    Time( T ) = CurrentTime()
)
Returns( Double() )
```

```slang
@Time::ToEpochMilli( @Time::From ISO DateTime( "2006-02-28T01:23:45.23Z" ) );
// 1141089825230
```

---

## Procmon String Functions

### Time::FromProcmonString

**Parse a procmon-style string (e.g. `"1b+17:00 TKO"`) to Time.**

```
/****************************************************************
** Routine: Time::FromProcmonString
****************************************************************/
Time::FromProcmonString = Func(
    Date( Procmon Date ),
    String( Procmon String ),
    String( Currency1 ) = String(),
    String( Currency2 ) = String(),
    String( Default Location ) := ""
)
Returns( Time(), Null )
```

The string format is `[dd[b?]+]hh:mm [location]`. `b` = business days, `d` or empty = calendar days. Location defaults to `"US/Eastern"`.

---

### Time::FromProcmonStringJSI

**JSI-compatible wrapper: returns milliseconds since Unix Epoch.**

```
/****************************************************************
** Routine: Time::FromProcmonStringJSI
****************************************************************/
Time::FromProcmonStringJSI = Func(
    Date( Procmon Date ),
    String( Procmon String ),
    String( Holiday Calendar 1 ) = String(),
    String( Holiday Calendar 2 ) = String(),
    String( Default Location ) := ""
)
Returns( Double(), Null )
```

---

### Time::ToProcmonString

**Format a Time as a procmon string relative to a date and location.**

```
/****************************************************************
** Routine: Time::ToProcmonString
****************************************************************/
Time::ToProcmonString = Func(
    Time( Time ),
    Date( Procmon Date ),
    String( Location ) := "NYC",
    Double( Strict ) := False
)
Returns( String(), Null )
```

```slang
@Time::ToProcmonString( T1, Date( 20080101 ), Location := "NYC" );
// "0+01:02 NYC"
```

---

## Elapsed / Arithmetic Functions

### Time::Elapsed

**Convert Days + Hours + Minutes + Seconds to total seconds.**

```
/****************************************************************
** Routine: Time::Elapsed
****************************************************************/
Time::Elapsed = Func(
    Double( Days ) := 0,
    Double( Hours ) := 0,
    Double( Minutes ) := 0,
    Double( Seconds ) := 0
)
Returns( Double() )
```

```slang
@Time::Elapsed( Days := 4, Hours := 3, Minutes := 2, Seconds := 1 );
// 345600 + 10800 + 120 + 1 = 356521
```

---

### Time::AddElapsed

**Add elapsed time to a Time value.**

```
/****************************************************************
** Routine: Time::AddElapsed
****************************************************************/
Time::AddElapsed = Func(
    Time( Addend ) = CurrentGMTime(),
    Double( Days ) := 0,
    Double( Hours ) := 0,
    Double( Minutes ) := 0,
    Double( Seconds ) := 0
)
Returns( Time() )
```

```slang
@Time::AddElapsed( BaseTime, Hours := 1, Minutes := 30 );
```

---

### Time::RDateAdd

**Add an RDate to a Time, preserving time-of-day.**

```
/****************************************************************
** Routine: Time::RDateAdd
****************************************************************/
Time::RDateAdd = Func(
    RDate( Increment ),
    Time( Time ),
    String( TZ ) = @Time::Get Time Zone(),
    Curr1 := NULL,
    Curr2 := NULL
)
Returns( Time() )
```

Extracts the date from Time, applies RDateAdd with holiday calendars, then re-combines with the original time-of-day.

```slang
Tomorrow Same Time = @Time::RDateAdd( RDate( "1d" ), CurrentTime() );
Next Bday Same Time = @Time::RDateAdd( RDate( "1b" ), CurrentTime(), Curr1 := "USD" );
```

---

## Rounding and Trimming Functions

### Time::Floor

**Truncate sub-second part of a time.**

```
/****************************************************************
** Routine: Time::Floor
****************************************************************/
Time::Floor = Func(
    Time( In )
)
Returns( Time() )
```

```slang
@Time::Floor( Time( "12:34:56.789" ) );
// 12:34:56.000
```

---

### Time::Ceil

**Round a time up to the next whole second.**

```
/****************************************************************
** Routine: Time::Ceil
****************************************************************/
Time::Ceil = Func(
    Time( In )
)
Returns( Time() )
```

```slang
@Time::Ceil( Time( "12:34:56.001" ) );
// 12:34:57.000
```

---

### Time::Trim

**Trim a time to a given resolution (e.g. to the nearest minute).**

```
/****************************************************************
** Routine: Time::Trim
****************************************************************/
Time::Trim = Func(
    Time( Time ),
    Double( Resolution ) := TIME::SECS_IN_MIN
)
Returns( Time() )
```

```slang
@Time::Trim( Time( "12:34:56.789" ) );
// 12:34:00.000  (trimmed to nearest minute)
```

---

### Time::Strip MilliSeconds

**Remove milliseconds from a time.**

```
/****************************************************************
** Routine: Time::Strip MilliSeconds
****************************************************************/
Time::Strip MilliSeconds = Func(
    Time( Time )
)
Returns( Time() )
```

---

## Comparison Functions

### Time::Similar

**Check whether two times are equal within a given resolution.**

```
/****************************************************************
** Routine: Time::Similar
****************************************************************/
Time::Similar = Func(
    Time( T1 ),
    Time( T2 ),
    Double( Resolution ) := TIME::SECS_IN_MIN
)
Returns( Double() )
```

```slang
@Time::Similar( Time( "12:34:56" ), Time( "12:34:01" ) );
// True (within same minute)
```

---

## Miscellaneous Functions

### Time::DSTAdjust

**Return DST adjustment for a date: +1 (spring forward), -1 (fall back), 0 (neither).**

```
/****************************************************************
** Routine: Time::DSTAdjust
****************************************************************/
Time::DSTAdjust = Func(
    Date( Date ),
    String( Timezone ) := GetEnv( "TZ" )
)
Returns( Double() )
```

---

### Time::DSTAdjustmentBetweenRange

**Calculate DST adjustment in hours between two times in a timezone.**

```
/****************************************************************
** Routine: Time::DSTAdjustmentBetweenRange
****************************************************************/
Time::DSTAdjustmentBetweenRange = Func(
    Time( Start Time ),
    Time( End Time ),
    String( TimeZone )
)
Returns( Double() )
```

Negative = fall back, positive = spring forward, 0 = no change.

```slang
@Time::DSTAdjustmentBetweenRange(
    Time( "2015-11-01T00:00:00 America/New_York" ),
    Time( "2015-11-01T02:00:00 America/New_York" ),
    "America/New_York"
);
// -1
```

---

### Time::Last Daytime Occurrence

**Find the most recent time when it was a given time-of-day in a timezone.**

```
/****************************************************************
** Routine: Time::Last Daytime Occurrence
****************************************************************/
Time::Last Daytime Occurrence = Func(
    Double( Hours ),
    Double( Minutes ),
    String( Time Zone ),
    Time( Relative To ) := CurrentTime()
)
Returns( Time() )
```

---

### Time::Next Daytime Occurrence

**Find the next time when it will be a given time-of-day in a timezone.**

```
/****************************************************************
** Routine: Time::Next Daytime Occurrence
****************************************************************/
Time::Next Daytime Occurrence = Func(
    Double( Hours ),
    Double( Minutes ),
    String( Time Zone ),
    Time( Relative To ) := CurrentTime()
)
Returns( Time() )
```

---

### Time::Next Time Increment Occurrence

**Find the next time that is an even multiple of a minute increment.**

```
/****************************************************************
** Routine: Time::Next Time Increment Occurrence
****************************************************************/
Time::Next Time Increment Occurrence = Func(
    Time( Initial Time ),
    Double( Minute Increment ),
    Boolean( Skip Initial Time ) := FalseBool
)
Returns( Time() )
```

For a 5-minute increment, if it's 10:13, returns 10:15.

---

### Time::Within Daily Time Window

**Check if a time falls within a daily repeating window.**

```
/****************************************************************
** Routine: Time::Within Daily Time Window
****************************************************************/
Time::Within Daily Time Window = Func(
    Time( Input Time ),
    Time( Daily Start Time ),
    Double( Duration ),
    String( Timezone )
)
Returns( Double() )
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `Input Time` | Time | Time to check |
| `Daily Start Time` | Time | Window start (recurring daily) |
| `Duration` | Double | Window duration in seconds (must be < 86400) |
| `Timezone` | String | Timezone for day boundaries |

---

### Time::Current Time

**Same as `CurrentTime()`, but mockable for regtests.**

```
/****************************************************************
** Routine: Time::Current Time
****************************************************************/
Time::Current Time = Func()
Returns( Time() )
```

---

---

# Part 2: Built-in Functions

The functions below are available without any `Link` statement.
For detailed examples see [workingWithTime.md](workingWithTime.md).

---

## Date (Constructor)

**Create a date from a string in DDMMMYYYY format.**

```
Date( DateString ) => Date
```

- `DD`: day (01-31, leading zero optional)
- `MMM`: month abbreviation (Jan-Dec, case-insensitive)
- `YYYY`: four-digit year

```slang
D = Date( "17Apr2025" );
D = Date( "1Jan2026" );
```

---

## Today

**Get today's date.**

```
Today() => Date
```

```slang
Current Date = Today();
```

---

## Time (Constructor / Current)

**Get the current timestamp.**

```
Time() => Time
```

```slang
Now = Time();
Print( Now, "\n" );                // "Thu 17Apr2025 02:30:15 pm"
```

---

## Date Components

Access properties directly on a Date value:

| Property | Returns | Example |
|----------|---------|---------|
| `.Day` | Day of month (1-31) | `D.Day` |
| `.Month` | Month number (1-12) | `D.Month` |
| `.Year` | Four-digit year | `D.Year` |
| `.DayOfWeek` | Day of week (0=Sun, 6=Sat) | `D.DayOfWeek` |

```slang
D = Date( "17Apr2025" );
Printf( "%02d/%02d/%04d\n", D.Month, D.Day, D.Year );   // 04/17/2025
```

---

## Time Components

Access properties on a Time value:

| Property | Returns |
|----------|---------|
| `.Date` | Date component |
| `.Hour` | Hour (0-23) |
| `.Minute` | Minute (0-59) |
| `.Second` | Second (0-59) |

---

## RDate (Relative Date)

**Create a relative date offset.**

```
RDate( OffsetString ) => RDate
```

| Suffix | Meaning | Example |
|--------|---------|---------|
| `b` | Business days | `RDate( "3b" )` |
| `d` | Calendar days | `RDate( "5d" )` |
| `m` | Months | `RDate( "1m" )` |
| `y` | Years | `RDate( "1y" )` |
| `w` | Weeks | `RDate( "2w" )` |
| `em` | End of month | `RDate( "em" )` |

Negative offsets: `RDate( "-5b" )` = 5 business days back.

```slang
D = Date( "10Apr2025" );
Next Bday = D + RDate( "1b" );
Last Month = D + RDate( "-1m" );
```

---

## Date Arithmetic

| Operation | Result | Example |
|-----------|--------|---------|
| `Date + N` | Date N calendar days later | `D + 7` |
| `Date - N` | Date N calendar days earlier | `D - 1` |
| `Date + RDate` | Date adjusted by relative offset | `D + RDate( "3b" )` |
| `Date2 - Date1` | Double (number of calendar days) | `End - Start` |

---

## Date Comparison

All standard comparison operators work on Date values:

```
==, !=, <, >, <=, >=
```

```slang
If( Date( "01Jan2025" ) < Date( "31Dec2025" ) )
{
    Print( "Earlier\n" );
};
```

---

## IsError (on Dates)

**Check if a date value is in an error state.**

```
IsError( DateValue ) => Double (True/False)
```

```slang
D = Date( "invalid" );
If( IsError( D ) )
{
    Print( "Bad date\n" );
};
```

---

## String (on Dates)

**Convert a date to its string representation.**

```
String( DateValue ) => String
```

```slang
String( Date( "17Apr2025" ) );     // "17Apr25"
```

---

## ProcessCpuTime

**Get elapsed CPU time for benchmarking.**

```
ProcessCpuTime() => Double
```

```slang
Start = ProcessCpuTime();
// ... work ...
Elapsed = ProcessCpuTime() - Start;
Printf( "Took %.3f seconds\n", Elapsed );
```

---

## TimeIt

**Measure and print execution time of a block.**

```slang
TimeIt
{
    // code to measure
};
```

---

## Time::Hour

**Get the hour of a Time value in a given timezone.**

```
Time::Hour( Time, Timezone ) => Double
```

```slang
Time::Hour( Time(), "America/New_York" );    // e.g. 14
```

---

## Time::Minutes

**Get the minutes of a Time value in a given timezone.**

```
Time::Minutes( Time, Timezone ) => Double
```

```slang
Time::Minutes( Time(), "America/New_York" ); // e.g. 30
```

---

## Time::Seconds

**Get the seconds of a Time value.**

```
Time::Seconds( Time, Timezone ) => Double
```

---

## Time::MilliSeconds

**Get the milliseconds of a Time value.**

```
Time::MilliSeconds( Time ) => Double
```

---

## Time::Month

**Get the month of a Time value in a given timezone.**

```
Time::Month( Time, Timezone ) => Double
```

> **Note:** Result is **0-based** (0 = January, 11 = December). This differs from `Date.Month` which is 1-based.

```slang
Time::Month( Time(), "America/New_York" );   // 0-based month
```

---

## Time::Year

**Get the year (including century) of a Time value in a given timezone.**

```
Time::Year( Time, Timezone ) => Double
```

```slang
Time::Year( Time(), "America/New_York" );    // e.g. 2026
```

---

## Time::DayOfMonth

**Get the day of month (1-31) of a Time value in a given timezone.**

```
Time::DayOfMonth( Time, Timezone ) => Double
```

---

## Time::DayOfWeek

**Get the day of week (0-based, 0 = Sunday) of a Time value in a given timezone.**

```
Time::DayOfWeek( Time, Timezone ) => Double
```

```slang
Time::DayOfWeek( Time(), "America/New_York" ); // 0=Sun, 1=Mon, ..., 6=Sat
```

---

## Time::ISO8601Format

**Format a Time as an ISO 8601 string.**

```
Time::ISO8601Format( Time [, Basic [, Zulu [, UtcOffset [, Prec [, TimeZone]]]]] ) => String
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `Basic` | `False` | Use basic (compact) format |
| `Zulu` | `False` | Use UTC designator `Z` |
| `UtcOffset` | `True` | Include UTC offset |
| `Prec` | `0` | Decimal places of sub-second precision |
| `TimeZone` | local | Timezone for conversion |

```slang
Time::ISO8601Format( Time() );
// "2026-02-18T14:30:15-05:00"

Time::ISO8601Format( Time(), False, True, False, 3 );
// "2026-02-18T19:30:15.000Z"
```

---

## Time::ODBCFormat

**Format a Time as an ODBC canonical string.**

```
Time::ODBCFormat( Time [, Prec [, TimeZone]] ) => String
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `Prec` | `0` | Decimal places of sub-second precision |
| `TimeZone` | local | Timezone for conversion |

```slang
Time::ODBCFormat( Time(), 0, "America/New_York" );
// "2026-02-18 14:30:15"
```

---

## GMTimeParts

**Break a Time value into UTC time parts.**

```
GMTimeParts( Time ) => Structure
```

Returns a Structure with fields like `Year`, `Month`, `Day`, `Hour`, `Minute`, `Second`, etc., all expressed in UTC.

```slang
Parts = GMTimeParts( Time() );
Print( Parts, "\n" );
```

---

## LocalTimeParts

**Break a Time value into local time parts for a given timezone.**

```
LocalTimeParts( Time [, TimeZone] ) => Structure
```

If `TimeZone` is not supplied, the current local timezone is used.

```slang
Parts = LocalTimeParts( Time(), "America/New_York" );
Print( Parts.Hour, ":", Parts.Minute, "\n" );
```

---

## AllowNegativeDates

**Enable or disable negative (pre-epoch) dates.**

```
AllowNegativeDates( OnOff ) => void
```

---

## See Also

- [workingWithTime.md](workingWithTime.md) -- full guide with patterns and examples
- [examples.md](examples.md) -- practical recipes drawn from `Test: Time Functions`
- `.github/builtins.md` -- complete built-in function reference
