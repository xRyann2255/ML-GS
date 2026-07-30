# Time Functions -- Practical Examples

Recipes drawn from `Test: Time Functions`. All examples require:

```slang
Link( "_LIB Time Functions" );
```

---

## Table of Contents

1. [Formatting Times as Strings](#1-formatting-times-as-strings)
2. [Parsing Strings to Times](#2-parsing-strings-to-times)
3. [ISO 8601 Round-Tripping](#3-iso-8601-round-tripping)
4. [Timezone Validation and Lookup](#4-timezone-validation-and-lookup)
5. [Location-Based Conversions](#5-location-based-conversions)
6. [Time Difference as Human-Readable String](#6-time-difference-as-human-readable-string)
7. [Epoch and Unix Timestamps](#7-epoch-and-unix-timestamps)
8. [Elapsed Time and Arithmetic](#8-elapsed-time-and-arithmetic)
9. [Midnight, Seconds Since Midnight](#9-midnight-seconds-since-midnight)
10. [Floor, Ceil, and Rounding](#10-floor-ceil-and-rounding)
11. [Procmon Strings](#11-procmon-strings)
12. [Structure Conversion](#12-structure-conversion)
13. [Millisecond Handling](#13-millisecond-handling)
14. [DST and Daily Windows](#14-dst-and-daily-windows)

---

## 1. Formatting Times as Strings

### DD/MM/YYYY and MM/DD/YYYY Variants

```slang
T = Time( "31Dec2005 12:01:33 am" );

// UK format DD/MM/YYYY
@Time::DDMMYYYY HHMMSS( T );
// "31/12/2005 00:01:33"

// US format MM/DD/YYYY
@Time::MMDDYYYY HHMM( T, Four Digit Year := True );
// "12/31/2005 00:01"

@Time::MMDDYYYY HHMMSS( T, Four Digit Year := True );
// "12/31/2005 00:01:33"

// Short year
@Time::MMDDYYYY HHMM( T );
// "12/31/05 00:01"
```

### DDMMMYY Variants

```slang
T = Time( "1Mar05 3:21:45" );

@Time::DDMMMYY HHMM( T );
// "01Mar05 03:21"

@Time::DDMMMYY HHMMSS( T );
// " 1Mar05 03:21:45"
```

### Compact YYYYMMDD Variants

```slang
T = Time( "1Mar05 3:21:45" );

// No delimiters
@Time::To YYYYMMDDHHMMSS( T );
// "20050301032145"

// With time colons
@Time::To YYYYMMDDHHMMSS( T, Delimiter := ":" );
// "2005030103:21:45"

// With space between date and time
@Time::To YYYYMMDDHHMMSS( T, YT delimiter := " " );
// "20050301 032145"

// With date slashes
@Time::To YYYYMMDDHHMMSS( T, Date Delimiter := "/" );
// "2005/03/01032145"

// Short year
@Time::To YYMMDDHHMMSS( T );
// "050301032145"

// With milliseconds
@Time::To YYYYMMDDHHMMSSmmm( Time( "23May10 15:23:45.123" ) );
// "20100523152345.123"
```

### Time-Only Formats

```slang
@Time::HHMM( Time( "01:23:45" ) );                    // "01:23"
@Time::HMMpm( Time( "17:00:00" ) );                   // " 5:00pm"
@Time::HMMpm( Time( "00:00:00" ) );                   // "12:00am"
@Time::HHMMSS( Time( "01:23:45.678" ) );               // "01:23:45"
@Time::HHMMSSWithMilliseconds( Time( "17:05:19.517" ) ); // "17:05:19.517"
```

### GMT and OMA Formats

```slang
T = Time( "31Dec2005 12:01:33.123 am" );
@Time::CurrentGMTYYYYMMDDHHMMSS( T );
// "20051231000133"

@Time::CurrentGMTYYYYMMDDHHMMSS( T, Include Milliseconds := True );
// "20051231000133123"

@Time::CurrentGMTYYYYMMDDHHMMSS( T, Include Milliseconds := True, Millisecond Precision := 2 );
// "2005123100013312"

@Time::OMATimeFormat( TimeFromDateNew( Date( "1Jan07" ), "GMT", 1, 2, 3 ) );
// "01-Jan-2007 01:02:03"
```

### SecondsToString

```slang
@Time::SecondsToString( 3661, 1 );   // "1h"
@Time::SecondsToString( 3661, 2 );   // "1h 1m"
@Time::SecondsToString( 3661, 3 );   // "1h 1m 1s"
@Time::SecondsToString( 0 );         // "0s"
```

---

## 2. Parsing Strings to Times

### YYYYMMDDHHMMSS

```slang
T = @Time::YYYYMMDDHHMMSS( "20100916180328" );
// Parses to 16Sep10 18:03:28

// With subseconds
T = @Time::YYYYMMDDHHMMSSSb( "20100916180328.572" );
```

### DateTimeString (handles > 24 hours and AM/PM)

```slang
@Time::TimeFromDateTimeString( "01Aug99 23:00:00" );
@Time::TimeFromDateTimeString( "01Aug99 25:00:00" );   // rolls to 02Aug99 01:00

@Time::TimeFromDateTimeStringPM( "01Aug99 11:00:00pm" );
@Time::TimeFromDateTimeStringPM( "01Aug99 12:20:00 AM" );
```

### From Date + Time String

```slang
D = Date( "11Nov2005" );
T = @Time::FromDateAndTimeString( D, "17:00:00", TZ := "US/Eastern" );
// 5pm Eastern on 11/11/2005
```

### From UK and ISO Date Formats

```slang
// UK format: DD/MM/YYYY
@Time::From DDMMYYYY HHMMSS( "06/12/2011 15:46:54" );

// ISO format: YYYYMMDD
@Time::From YYYYMMDD HHMMSS( "20090305 15:23:45" );

// With milliseconds
@Time::From YYYYMMDD HHMMSS( "20090305 15:23:45.123", Milliseconds := True );
```

### With Custom Delimiters

```slang
@Time::FromYYYYMMDDHHMMSSmmmString(
    "2024-01-01T12X30X30Y000",
    DDelim := "-",
    DTDelim := "T",
    TDelim := "X",
    MDelim := "Y"
);

@Time::FromYYYYMMMDDHHMMSSmmmString( "2024/jul/01 08:48:15.841" );
```

### UDB Format

```slang
@Time::From UDB DateTime Format( "2024-04-24-10.30.00.123456" );
// Wed 24Apr24 10:30:00 am
```

---

## 3. ISO 8601 Round-Tripping

### Formatting

```slang
@Time::Set Time Zone( "America/New_York" );
T = Time( Date( "20060228" ) ) + ( Time( "01:23:45" ) - Time( Today() ) ) + .1234;

@Time::To ISO DateTime( T );
// "2006-02-28T01:23:45"

@Time::To ISO DateTime( T, Zulu := True );
// "2006-02-28T06:23:45Z"

@Time::To ISO DateTime( T, Precision := 3, UTC Offset := True );
// "2006-02-28T01:23:45.123-05:00"

@Time::To ISO DateTime( T, Precision := 3, UTC Offset := True, Time Zone := "Europe/London" );
// "2006-02-28T06:23:45.123+00:00"

@Time::To ISO DateTime( T, Extended := False, Precision := 3, UTC Offset := True );
// "20060228T012345.123-0500"
```

### Parsing

```slang
@Time::From ISO DateTime( "2006-02-28T01:23:45Z" );
@Time::From ISO DateTime( "2006-02-28T01:23:45-05:00" );
@Time::From ISO DateTime( "20060228T012345Z" );
@Time::From ISO DateTime( "2006-02-28T01:23:45", Local Time Zone := "Asia/Hong_Kong" );
```

### Identity Checks

```slang
// These should be equal (same instant in time):
@Time::From ISO DateTime( "2006-02-28T12:00:00Z" )
    == @Time::From ISO DateTime( "2006-02-28T13:00:00+01:00" );
// True

@Time::From ISO DateTime( "2006-02-28T12:00:00Z" )
    == @Time::From ISO DateTime( "2006-02-28T11:00:00-01:00" );
// True
```

---

## 4. Timezone Validation and Lookup

```slang
// Valid timezone checks (case-sensitive!)
@Time::Is Valid TimeZone( "GMT" );              // True
@Time::Is Valid TimeZone( "gmt" );              // False
@Time::Is Valid TimeZone( "Europe/London" );    // True
@Time::Is Valid TimeZone( "Europe/london" );    // False

// New-style validation (requires continent prefix)
@Time::Is Valid TimeZone New( "Europe/London" );  // True
@Time::Is Valid TimeZone New( "EST" );            // False
@Time::Is Valid TimeZone New( "Etc/UTC" );        // True (special case)

// DST disambiguator support
@Time::Is Valid TimeZone( "Europe/London!earliest" );  // True
@Time::Is Valid TimeZone( "Europe/London!latest" );    // True
@Time::Is Valid TimeZone( "Europe/London!either" );    // False

// Location-to-timezone
@Time::Time Zone From Location( "NYC" );   // "EST5EDT"
@Time::Time Zone From Location( "LDN" );   // "GB"
```

---

## 5. Location-Based Conversions

```slang
// Convert "18:00 LDN" to NYC local time
Exit Time = @Time::FromTimeAndLocation( "18:00 LDN", Location := "NYC" );

// Self-reference: should equal the literal time
@Time::FromTimeAndLocation( "08:12 " + GetEnv( "Location" ) ) == Time( "08:12" );
// True

// Cross-timezone comparison (LDN vs FFT = 1 hour apart)
@Time::FromTimeAndLocation( "29Mar11 08:00 FFT", Time Zone New := True )
    == @Time::FromTimeAndLocation( "29Mar11 08:00 LDN", Time Zone New := True ) - Time::SECS_IN_HOUR;
// True
```

---

## 6. Time Difference as Human-Readable String

```slang
T = CurrentTime();

@Time::Time Difference As String( T, T );
// "" (empty -- zero diff)

@Time::Time Difference As String( T, T, Zero Diff As Empty String := False );
// "0 Seconds"

@Time::Time Difference As String( T, T - 1 );
// "1 Second"

@Time::Time Difference As String( T, T - 65 );
// "1 Minute 5 Seconds"

@Time::Time Difference As String( T, T - 65, Resolution := "Minute" );
// "1 Minute"

@Time::Time Difference As String( T, T - 3661 );
// "1 Hour 1 Minute 1 Second"

@Time::Time Difference As String( T, T - 86400 );
// "1 Day"

@Time::Time Difference As String( LowLimit( "Time" ), HighLimit( "Time" ) );
// "986 Years 18 Weeks 2 Days 4 Hours 59 Minutes 59 Seconds"

@Time::Time Difference As String( LowLimit( "Time" ), HighLimit( "Time" ), Resolution := "Year" );
// "986 Years"
```

---

## 7. Epoch and Unix Timestamps

### ToEpochMilli

```slang
@Time::ToEpochMilli( @Time::From ISO DateTime( "2006-02-28T01:23:45Z" ) );
// 1141089825000

@Time::ToEpochMilli( @Time::From ISO DateTime( "2006-02-28T01:23:45.23Z" ) );
// 1141089825230

@Time::ToEpochMilli( @Time::From ISO DateTime( "1970-01-01T00:00:00Z" ) );
// 0
```

### ToUnixTimestamp

```slang
@Time::ToUnixTimestamp( @Time::From ISO DateTime( "2006-02-28T01:23:45Z" ) );
// 1141089825

// Note: sub-second values are rounded
@Time::ToUnixTimestamp( @Time::From ISO DateTime( "2006-02-28T01:23:45.899Z" ) );
// 1141089826
```

---

## 8. Elapsed Time and Arithmetic

### Computing Elapsed Seconds

```slang
@Time::Elapsed( Seconds := 1 );     // 1
@Time::Elapsed( Minutes := 2 );     // 120
@Time::Elapsed( Hours := 3 );       // 10800
@Time::Elapsed( Days := 4 );        // 345600

@Time::Elapsed( Days := 4, Hours := 3, Minutes := 2, Seconds := 1 );
// 356521
```

### Adding Elapsed Time

```slang
Base = CurrentGMTime();

@Time::AddElapsed( Base, Seconds := 1 ) == Base + 1;
@Time::AddElapsed( Base, Minutes := 1 ) == Base + Time::SECS_IN_MIN;
@Time::AddElapsed( Base, Hours := 1 )   == Base + Time::SECS_IN_HOUR;
@Time::AddElapsed( Base, Days := 1 )    == Base + Time::SECS_IN_DAY;
// All True
```

### RDateAdd on Times

```slang
The Date = Date( "15Feb2008" );
The Time = @Time::FromDateAndTimeString( The Date, "09:00:00", TZ := "Europe/London" );

// Advance by 1 business day (using GBP calendar)
Next Bday Time = @Time::RDateAdd( RDate( "1u" ), The Time, "Europe/London", Curr1 := "GBP" );
```

---

## 9. Midnight, Seconds Since Midnight

```slang
TZ = "Europe/London";
D  = Date( "28Mar05" );
T  = Time( "28Mar05 1:30pm GMT" );

// Get midnight
M = @Time::Midnight( D, TZ );

// Verify it's truly midnight
Time::Hour( M, TZ );       // 0
Time::Minutes( M, TZ );    // 0
Time::Seconds( M, TZ );    // 0

// Seconds since midnight
@Time::Seconds Since Midnight( M, TZ );    // 0
@Time::Seconds Since Midnight( T, TZ );    // T - M
```

---

## 10. Floor, Ceil, and Rounding

```slang
N = CurrentTime();

// Floor: truncate sub-second
F = @Time::Floor( N );
// F has .Millisecond == 0

// Ceil: round up to next whole second
C = @Time::Ceil( N );
// If N had any milliseconds, C is one second later with .Millisecond == 0

// Trim: to nearest minute
@Time::Trim( Time( "12:34:56.789" ) );
// 12:34:00

// Similar: are two times within the same minute?
@Time::Similar( Time( "12:34:56" ), Time( "12:34:01" ) );
// True

// Strip milliseconds
@Time::Strip MilliSeconds( Time( "12:34:56.789" ) );
// 12:34:56.000
```

---

## 11. Procmon Strings

### Formatting

```slang
D1 = Date( 20080101 );
T1 = TimeFromDateNew( D1, "US/Eastern", 01, 02, 00 );
T2 = TimeFromDateNew( D1 + 1, "Asia/Tokyo", 17, 00, 00 );

@Time::ToProcmonString( T1, D1, Location := "NYC" );
// "0+01:02 NYC"

@Time::ToProcmonString( T2, D1, Location := "TKO" );
// "1+17:00 TKO"

// Negative offset (time before the procmon date)
@Time::ToProcmonString( T2, D1 + 3, Location := "TKO" );
// "-2+17:00 TKO"

// UTC location
@Time::ToProcmonString( T1, D1, Location := "UTC" );
// "0+06:02 UTC"
```

### Parsing

```slang
D = Date( 20080101 );
T = @Time::FromProcmonString( D, "0+01:02 NYC" );
// TimeFromDateNew( D, "US/Eastern", 1, 2, 0 )
```

---

## 12. Structure Conversion

```slang
TZ = "Europe/London";
T  = Time( "27Mar2008 12:01:33.123" );

// Time -> Structure
S = @Time::TimeToStruct( T, TZ );
// S.Day, S.Month, S.Year, S.YearDay, S.Hour, S.Minute, S.Second, S.Millisecond

// Structure -> Time
T2 = @Time::StructToTime( S, TZ );
// Round-trips (milliseconds may differ slightly)
```

---

## 13. Millisecond Handling

### Preserving Milliseconds Across Conversions

```slang
// String -> Time with milliseconds preserved
T = @Time::FromStringWithMilliseconds( "Tue 18Mar03 12:50:52.123" );

// Time -> String with milliseconds
S = @Time::ToStringWithMilliseconds( T );
// "Tue 18Mar03 12:50:52.123"

// Round-trip check
T2 = @Time::FromStringWithMilliseconds( S );
Sprintf( "%0.3f", Double( T ) ) == Sprintf( "%0.3f", Double( T2 ) );
// True

// HHMMSSWithMilliseconds round-trip
Test Times = [ Time( "17:05:19.517" ), Time( "01:37:29.927" ), Time( "19:19:59.999" ), Time( "00:00:00.000" ) ];
ForEach( TT, Test Times )
    Time( @Time::HHMMSSWithMilliseconds( TT ) ) == TT;
// True for all

// YYYYMMDD HHMMSS can optionally ignore or keep milliseconds
@Time::From YYYYMMDD HHMMSS( "20090305 15:23:45.123" ).Milliseconds();
// 0 (default: ignored)

@Time::From YYYYMMDD HHMMSS( "20090305 15:23:45.123", Milliseconds := True ).Milliseconds();
// 123
```

### YYYYMMDD HHMMSSSb with Timezone

```slang
D = Date( "1Jan07" );
T = @Time::LocationToLocal( "4Jan07 12:15:30.123", "NYC" );

@Time::YYYYMMDD HHMMSSSb( Time Zone New( "NYC" ), T, D );
// "20070101 12:15:30.123"

@Time::YYYYMMDD HHMMSSSb( Time Zone New( "NYC" ), T, D, SubSec := False );
// "20070101 12:15:30"

@Time::YYYYMMDD HHMMSSSb( Time Zone New( "NYC" ), T, D, SubSec := False, Date Delimiter := "-", DateTime Delimiter := "T" );
// "2007-01-01T12:15:30"
```

---

## 14. DST and Daily Windows

### DST Adjustment Between Range

```slang
// "Fall Back" in NYC (Nov 1, 2015)
@Time::DSTAdjustmentBetweenRange(
    Time( "2015-11-01T00:00:00 America/New_York" ),
    Time( "2015-11-01T02:00:00 America/New_York" ),
    "America/New_York"
);
// -1

// Not quite crossing the boundary
@Time::DSTAdjustmentBetweenRange(
    Time( "2015-11-01T00:00:00 America/New_York" ),
    Time( "2015-11-01T01:59:59 America/New_York" ),
    "America/New_York"
);
// 0

// Crossing both spring and fall -- net 0
@Time::DSTAdjustmentBetweenRange(
    Time( "2015-01-25T00:00:00 America/New_York" ),
    Time( "2015-11-15T00:00:00 America/New_York" ),
    "America/New_York"
);
// 0
```

### Next / Last Daytime Occurrence

```slang
TZ = "Europe/London";

// British Summer Time 2008: clocks forward at 2008-03-30 01:00 GMT
Summer Start = TimeFromDateNew( Date( "30Mar2008" ), TZ, 0, 0, 0 );
Next Summer  = TimeFromDateNew( Date( "31Mar2008" ), TZ, 0, 0, 0 );

// Last midnight before next summer day
@Time::Last Daytime Occurrence( 0, 0, TZ, Relative To := Next Summer );
// == Summer Start (midnight on Mar 30)

// Next midnight after 1 minute into summer start
@Time::Next Daytime Occurrence( 0, 0, TZ, Relative To := Summer Start + 60 );
// == Next Summer (midnight on Mar 31)
```

### Next Time Increment Occurrence

```slang
T = Time( "10:13:00" );

// Next 5-minute mark
@Time::Next Time Increment Occurrence( T, 5 );
// 10:15:00

// If already on a mark, and skip is False, returns same time
T2 = Time( "10:15:00" );
@Time::Next Time Increment Occurrence( T2, 5 );
// 10:15:00

// With Skip Initial Time
@Time::Next Time Increment Occurrence( T2, 5, Skip Initial Time := TrueBool );
// 10:20:00
```

---

## See Also

- [commonFunctions.md](commonFunctions.md) -- full function reference (Part 1: Library, Part 2: Built-in)
- [workingWithTime.md](workingWithTime.md) -- conceptual guide
