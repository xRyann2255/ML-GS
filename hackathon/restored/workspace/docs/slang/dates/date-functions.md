# DateFns:: Library Functions

The `_LIB Date Functions` library provides a comprehensive set of date manipulation, formatting, parsing, and business-day-aware functions. It is built on Slang's native `Date`, `RDate`, and related types and adds hundreds of utility functions under the `DateFns::` namespace.

> **New to Dates in Slang?** Start with [dates-base.md](dates-base.md) for the core `Date` and `RDate` types, arithmetic, comparisons, and validation. This file covers the `DateFns::` *library* functions.

## Linking

Only one link is needed -- the library stub pulls in both underlying libraries:

```slang
Link( "_LIB Date Functions" );
```

This internally links `_LIB Date Functions I` and `_LIB Date Functions II`. **Never link those directly.**, link _LIB Date Functions only

All functions are called with the `@DateFns::` prefix, e.g. `@DateFns::YYYYMMDD( Date( "01Jan06" ) )`.

Source: `_LIB Date Functions I`, `_LIB Date Functions II` | Test: `Test: Date Functions I`, `Test: Date Functions II`

## Quick Orientation

| Category | What it covers | Examples |
|----------|---------------|----------|
| **Month Conversion** | Month names, numbers, letters, maps | `@DateFns::MonthName`, `@DateFns::MonthNumber`, `@DateFns::MonthLetter` |
| **Date Calculation** | Business/calendar day arrays, counting | `@DateFns::CalcBizDates`, `@DateFns::CalcCalDays`, `@DateFns::CountBizDates` |
| **Holiday Functions** | Holiday detection, curves, names | `@DateFns::IsHoliday`, `@DateFns::Holiday Curve`, `@DateFns::Holiday Name` |
| **GS Reporting** | Goldman reporting month/quarter/year boundaries | `@DateFns::Goldman Reporting Month End`, `@DateFns::Goldman Reporting Quarter End` |
| **Date -> String** | Many output formats (YYYYMMDD, DDMMMYY, ISO, etc.) | `@DateFns::YYYYMMDD`, `@DateFns::DDMMMYYYY w Hyphen`, `@DateFns::Ascftime` |
| **String -> Date** | Parsing from many input formats | `@DateFns::DateFromStringYYYYMMDD`, `@DateFns::DateFromStringISO` |
| **Week/Month/Quarter/Year boundaries** | Start/end of periods, business day boundaries | `@DateFns::Start Of Month`, `@DateFns::End Of Quarter`, `@DateFns::Start Of Year` |
| **Boolean Tests** | Weekend, weekday, leap year, holiday checks | `@DateFns::IsWeekend`, `@DateFns::IsLeapYear`, `@DateFns::Is Last Business Day Of Month` |
| **Tenor & Year Fraction** | RDate differences, year fractions | `@DateFns::ComputeTenor`, `@DateFns::YearFractionActAct` |
| **Date Generation** | Generate date arrays at intervals | `@DateFns::CalcDatesFromPeriod`, `@DateFns::Calculate Dates` |
| **Miscellaneous** | Age calculation, DST, rolling dates, Ascftime formatting | `@DateFns::Age From Dates`, `@DateFns::Daylight Saving Time` |

---

## Constants (`_Const DateFns`)

The constants file provides pre-defined arrays and values used throughout the library:

| Constant | Value |
|----------|-------|
| `DateFns::Months` | `[ "Jan", "Feb", "Mar", ... "Dec" ]` |
| `DateFns::MonthsFull` | `[ "January", "February", ... "December" ]` |
| `DateFns::MonthLetters` | `[ "F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z" ]` |
| `DateFns::Weekdays` | `[ "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun" ]` |
| `DateFns::WeekdaysFull` | `[ "Monday", "Tuesday", ... "Sunday" ]` |
| `DateFns::WeekdaysMonToFri` | `[ "Mon", "Tue", "Wed", "Thu", "Fri" ]` |
| `DateFns::LastDayOfMonth` | 2-row array: ordinary year / leap year day counts per month |
| `DateFns::GoldmanReportingCalendars` | Allowed holiday calendars for GS reporting functions |

Multi-language month name constants are also available: Spanish, Italian, Portuguese, German, French, Dutch (both full and short forms).

---

# Part 1: `_LIB Date Functions I`

## Table of Contents (Part 1)

- [Month Conversion Functions](#month-conversion-functions)
- [Date Calculation and Counting](#date-calculation-and-counting)
- [Holiday Functions](#holiday-functions)
- [Goldman Reporting Functions](#goldman-reporting-functions)
- [Date to String Conversion Functions](#date-to-string-conversion-functions)
- [Miscellaneous Functions (Part 1)](#miscellaneous-functions-part-1)

---

## Month Conversion Functions

### DateFns::MonthName

**Given a month number (1-12), return the corresponding month name.**

```
DateFns::MonthName = Func(
    Double( MonthNumber ),
    String( Language ) = "English"
)
Returns( String(), Double() )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MonthNumber` | Double | -- | Month number 1-12 |
| `Language` | String | `"English"` | Language for month names. See `@DateFns::MonthList` for supported values. |

```slang
@DateFns::MonthName( 1 );                        // "Jan"
@DateFns::MonthName( 1, "Short Spanish" );        // "Ene"
@DateFns::MonthName( 1, "Italian" );              // "Gennaio"
@DateFns::MonthName( 13 );                        // Err()
```

---

### DateFns::MonthList

**Return an array of month names in the specified language.**

```
DateFns::MonthList = Func(
    String( Language ) = "EnglishFull"
)
Returns( Array(), Error() )
```

Supported languages: `"EnglishFull"` (default), `"English"` / `"Short"`, `"Letter"`, `"FrenchFull"`, `"French"`, `"DutchFull"`, `"Dutch"`, `"Spanish"`, `"Short Spanish"`, `"Italian"`, `"Portuguese"`, `"Short Portuguese"`, `"German"`, `"Short German"`.

```slang
@DateFns::MonthList()[ 0 ];              // "January"
@DateFns::MonthList( "Short" )[ 1 ];     // "Feb"
@DateFns::MonthList( "Letter" )[ 0 ];    // "F"
```

---

### DateFns::MonthMap

**Return a Structure mapping month names to month numbers.**

```
DateFns::MonthMap = Func(
    String( Language ) = "EnglishFull",
    Double( Case Sensitive ) := False,
)
Returns( Structure(), StructureCase(), Error() )
```

```slang
@DateFns::MonthMap().January;                              // 1
@DateFns::MonthMap( "Short" ).Mar;                         // 3
@DateFns::MonthMap( "Short", Case Sensitive := True ).Mar; // 3
```

---

### DateFns::MonthNumber

**Given a month name, return the month number (1-12).**

```
DateFns::MonthNumber = Func(
    String( MonthName ),
    String( Language ) = "English"
)
Returns( Double() )
```

Note: `"English"` is remapped to `"EnglishFull"`, so the default expects full month names like `"January"`.

```slang
@DateFns::MonthNumber( "January" );           // 1
@DateFns::MonthNumber( "Jan", "Short" );      // 1
@DateFns::MonthNumber( "F", "Letter" );       // 1
```

---

### DateFns::MonthLetter

**Given a month number (1-12), return the futures month letter.**

```
DateFns::MonthLetter = Func(
    Double( MonthNumber ),
)
Returns( String(), Double() )
```

```slang
@DateFns::MonthLetter( 1 );    // "F"
@DateFns::MonthLetter( 5 );    // "K"
```

---

### DateFns::LetterToMonth

**Given a futures month letter, return the abbreviated month name.**

```
DateFns::LetterToMonth = Func(
    String( Letter )
)
Returns( String(), Double() )
```

```slang
@DateFns::LetterToMonth( "J" );   // "Apr"
@DateFns::LetterToMonth( "F" );   // "Jan"
```

---

### DateFns::LetterToMonthNumber

**Given a futures month letter, return the month number (1-12).**

```
DateFns::LetterToMonthNumber = Func(
    String( Letter )
)
Returns( Double(), Error() )
```

```slang
@DateFns::LetterToMonthNumber( "J" );   // 4
```

---

### DateFns::MonthToLetter

**Given an abbreviated month name, return the futures month letter.**

```
DateFns::MonthToLetter = Func(
    String( MonthName )
)
Returns( String(), Double() )
```

```slang
@DateFns::MonthToLetter( "Jan" );   // "F"
```

---

## Date Calculation and Counting

### DateFns::CalcBizDates

**Return an array of business dates between start and end, inclusive. Supports holiday calendars and joint calendars (pipe-separated).**

```
DateFns::CalcBizDates = Func(
    Date( Start Date ),
    Date( End Date ),
    Holiday1 = Null,
    Holiday2 = Null,
    Boolean( Strict ) := FalseBool,
)
Returns( Array(), Null )
```

```slang
@DateFns::CalcBizDates( Date( "01Jan25" ), Date( "05Jan25" ) );
// [ 1Jan25, 2Jan25, 3Jan25 ]

@DateFns::CalcBizDates( Date( "01Jan06" ), Date( "05Jan06" ), "USD" );
// [ 3Jan06, 4Jan06, 5Jan06 ]

@DateFns::CalcBizDates( Date( "01Jan06" ), Date( "05Jan06" ), "TKO|NYC" );
// [ 4Jan06, 5Jan06 ]
```

---

### DateFns::CalcCalDays

**Return an array of calendar dates between start and end, inclusive. End defaults to end of month if omitted.**

```
DateFns::CalcCalDays = Func(
    Start Date = "",
    End Date   = "",
)
Returns( Array(), Error() )
```

```slang
@DateFns::CalcCalDays( Date( "30Jan06" ) );
// [ 30Jan06, 31Jan06 ]

@DateFns::CalcCalDays( Date( "30Jan06" ), Date( "02Feb06" ) );
// [ 30Jan06, 31Jan06, 1Feb06, 2Feb06 ]
```

---

### DateFns::CountBizDates

**Count business dates between start and end, inclusive.**

```
DateFns::CountBizDates = Func(
    Date( Start Date ),
    Date( End Date ),
    Holiday1 = Null,
    Holiday2 = Null,
)
Returns( Double(), Null )
```

```slang
@DateFns::CountBizDates( Date( "01Jan25" ), Date( "05Jan25" ) );         // 3
@DateFns::CountBizDates( Date( "01Jan25" ), Date( "05Jan25" ), "NYC" );  // 2
```

---

### DateFns::CountBizDates from RefDate

**Signed count of business dates between a reference date and a date of interest. Inclusive of Date of Interest, exclusive of RefDate.**

```
DateFns::CountBizDates from RefDate = Func(
    Date( RefDate ),
    Date( Date of Interest ),
    Any( Holiday1 ) = Null,
    Any( Holiday2 ) = Null,
    Boolean( Strict ) := FalseBool,
)
Returns( Double(), Error() )
```

```slang
@DateFns::CountBizDates from RefDate( Date( "01Jan25" ), Date( "05Jan25" ), "NYC" );  // 2
@DateFns::CountBizDates from RefDate( Date( "03Jan25" ), Date( "02Jan25" ), "NYC" );  // -1
```

---

### DateFns::Normalize RDate

**Convert an absolute RDate to a relative RDate (in business days) with respect to a base date.**

```
DateFns::Normalize RDate = Func(
    RDate( src ),
    Date( Base Date ) := Today(),
    Any( Holiday Calendar ) := Null,
    Any( Second Holiday Calendar ) := Null,
)
Returns( RDate() )
```

```slang
@DateFns::Normalize RDate( RDate( "6Oct06" ), Base Date := Date( "10Oct06" ) );  // -2b
@DateFns::Normalize RDate( RDate( "2b" ) );                                      // 2b
```

---

## Holiday Functions

### DateFns::IsHoliday

**Check if a date is a holiday for any of the specified calendar(s). Returns True/False. Weekends are holidays by default unless SkipWeekends is True.**

```
DateFns::IsHoliday = Func(
    Date( Date ),
    CalOrArray,
    Double( SkipWeekends ) = False,
    Double( Weekend BizDays ) = False,
)
Returns( Double(), Error() )
```

```slang
@DateFns::IsHoliday( Date( "04Jul06" ), "GS_NYC" );                     // True
@DateFns::IsHoliday( Date( "08Jul06" ), "GS_NYC" );                     // True (weekend)
@DateFns::IsHoliday( Date( "08Jul06" ), "GS_NYC", True );               // False (skip weekends)
```

---

### DateFns::IsHolidaySimultaneous

**Check if a date is a holiday on ALL specified calendars (not just any).**

```
DateFns::IsHolidaySimultaneous = Func(
    Date( Date ),
    CalOrArray,
    Double( SkipWeekends ) = False,
    Double( Weekend BizDays ) = False,
)
Returns( Double() )
```

```slang
@DateFns::IsHolidaySimultaneous( Date( "25Dec12" ), [ "GS_LDN", "GS_NYC" ] );  // True
@DateFns::IsHolidaySimultaneous( Date( "04Jul06" ), [ "GS_LDN", "GS_NYC" ] );  // False
```

---

### DateFns::Holiday Curve

**Return a GCurve of holiday dates for a calendar. Optionally restrict to a date range.**

```
DateFns::Holiday Curve = Func(
    String( Calendar ),
    Date( Start Date ) = LowLimit( "Date" ),
    Date( End Date ) = ...,
)
Returns( GCurve(), Error() )
```

```slang
@DateFns::Holiday Curve( "GS_NYC", Date( "01Jul06" ), Date( "10Jul06" ) );
// 4Jul06: Independence Day
```

---

### DateFns::Holiday Name

**If a date is a holiday, return the calendar and holiday name; otherwise return False.**

```
DateFns::Holiday Name = Func(
    Date( Date ),
    CalOrArray,
    Double( Include Cal Name ) := True,
)
Returns( String(), Double() )
```

```slang
@DateFns::Holiday Name( Date( "04Jul06" ), "GS_NYC" );
// "(GS_NYC) Independence Day"

@DateFns::Holiday Name( Date( "04Jul06" ), "GS_NYC", Include Cal Name := False );
// "Independence Day"
```

---

### DateFns::Calendar Quarter

**Return the calendar quarter (1-4) for a date.**

```
DateFns::Calendar Quarter = Func(
    Date( Date ),
)
Returns( Double() )
```

```slang
@DateFns::Calendar Quarter( Date( "01Jan06" ) );   // 1
@DateFns::Calendar Quarter( Date( "26Aug06" ) );   // 3
```

---

### DateFns::IsHolidayOnCurve

**Check if any date on a Curve is a holiday.**

```
DateFns::IsHolidayOnCurve = Func(
    Curve( Curve ),
    CalOrArray,
    Double( SkipWeekends ) = False,
    Double( SkipEmptyCal ) := False,
)
Returns( Double(), Error() )
```

---

## Goldman Reporting Functions

### DateFns::Goldman Reporting Month End

**Return the GS reporting month end for a date. Uses last-Friday-of-month logic (pre-2009) or last-business-day logic (2009+).**

```
DateFns::Goldman Reporting Month End = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
    Double( Allow All Calendars ) := False,
    Double( Ignore Holidays ) := False,
    String( Holiday Calendar ) := "GS_NYC",
)
Returns( Date(), Error() )
```

```slang
@DateFns::Goldman Reporting Month End( Date( "01Jan06" ) );   // 27Jan06
@DateFns::Goldman Reporting Month End( Date( "28Jan06" ) );   // 24Feb06 (rolls to next month)
```

---

### DateFns::Goldman Reporting Month Start

**Return the GS reporting month start for a date.**

```
DateFns::Goldman Reporting Month Start = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
    String( Holiday Calendar ) := "GS_NYC",
)
Returns( Date(), Error() )
```

---

### DateFns::Goldman Reporting Quarter End / Quarter Start

```
DateFns::Goldman Reporting Quarter End = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
    String( Holiday Calendar ) := "GS_NYC",
)
Returns( Date(), Error() )

DateFns::Goldman Reporting Quarter Start = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
    String( Holiday Calendar ) := "GS_NYC",
)
Returns( Date(), Error() )
```

---

### DateFns::Goldman Reporting Year End / Year Start

```
DateFns::Goldman Reporting Year End = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
)
Returns( Date(), Error() )

DateFns::Goldman Reporting Year Start = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
)
Returns( Date(), Error() )
```

---

### DateFns::Goldman Reporting Month End Dates In Range

**Return all GS reporting month-end dates within a date range.**

```
DateFns::Goldman Reporting Month End Dates In Range = Func(
    Date( Start Date ),
    Date( End Date ),
    Double( Allow All Calendars ) := False,
    Double( Ignore Holidays ) := False,
    String( Holiday Calendar ) := "GS_NYC",
)
Returns( Array(), Error() )
```

---

### Boolean GS Reporting Tests

```
DateFns::IsGoldmanReportingMonthEnd = Func( Date( Date ), ... ) Returns( Double(), Error() )
DateFns::IsGoldmanReportingQuarterEnd = Func( Date( Date ), ... ) Returns( Double(), Error() )
DateFns::IsGoldmanReportingYearEnd = Func( Date( Date ) ) Returns( Double(), Error() )
DateFns::IsCalendarMonthStart = Func( Date( Date ), ... ) Returns( Double(), Error() )
```

---

## Date to String Conversion Functions

### Numeric Formats

| Function | Example Input | Example Output |
|----------|--------------|----------------|
| `DateFns::YYYYMMDD( Date, Delimiter )` | `Date( "01Jan06" )` | `"20060101"` |
| `DateFns::YYYYMM( Date, Delimiter )` | `Date( "01Jan06" )` | `"200601"` |
| `DateFns::YYYYWW( Date, Delimiter )` | `Date( "31Dec06" )` | `"200652"` |
| `DateFns::YYMMDD( Date, Delimiter, Padding )` | `Date( "01Jan06" )` | `"060101"` |
| `DateFns::YYMM( Date )` | `Date( "01Jan06" )` | `"0601"` |
| `DateFns::MMDDYYYY w Slash( Date, Slash, Padding )` | `Date( "01Feb06" )` | `"02/01/2006"` |
| `DateFns::MMDDYY w Slash( Date, Slash, Padding )` | `Date( "01Feb06" )` | `"02/01/06"` |
| `DateFns::MMDDYY( Date )` | `Date( "01Jan06" )` | `"010106"` |
| `DateFns::DDMMYYYY w Slash( Date, Slash )` | `Date( "01Jan06" )` | `"01/01/2006"` |
| `DateFns::DDMMYY( Date, Delimiter, Padding )` | `Date( "01Jan06" )` | `"010106"` |
| `DateFns::DDMM( Date, Delimiter, Padding )` | `Date( "01Jan06" )` | `"0101"` |
| `DateFns::MMDD( Date, Delimiter )` | `Date( "01Jan06" )` | `"0101"` |
| `DateFns::MMYY( Date, Slash )` | `Date( "01Jan06" )` | `"0106"` |
| `DateFns::MDYYYY w Slash( Date, Slash )` | `Date( "01Feb06" )` | `"2/1/2006"` |

### Month-Name Formats

| Function | Example Input | Example Output |
|----------|--------------|----------------|
| `DateFns::DDMMMYYYY( Date, PadZero )` | `Date( "01Jan06" ), True` | `"01Jan2006"` |
| `DateFns::DDMMMYY( Date, PadZero, Delimiter, Language )` | `Date( "01Jan06" ), True` | `"01Jan06"` |
| `DateFns::DDMMMYYYY w Hyphen( Date, PadZero, Hyphen, Language )` | `Date( "01Jan06" ), True` | `"01-Jan-2006"` |
| `DateFns::DDMMM( Date, PadZero, Separator, Language )` | `Date( "01Jan06" ), True` | `"01Jan"` |
| `DateFns::MMMDD( Date, Delimiter, Language )` | `Date( "01Jan06" )` | `"Jan01"` |
| `DateFns::MMMYY( Date, Delimit, Delimiter, Language )` | `Date( "01Jan06" )` | `"JAN06"` |
| `DateFns::MMMYYYY( Date, Delimit, Delimiter, Language )` | `Date( "01Jan06" ), True` | `"Jan 2006"` |
| `DateFns::MMMMYYYY( Date, Delimit, Language )` | `Date( "01Jan09" ), True` | `"January 2009"` |
| `DateFns::MMMMDDYYYY( Date, Include Comma )` | `Date( "01Jan09" ), True` | `"January  1, 2009"` |
| `DateFns::MMMDDYYYY( Date, Include Comma )` | `Date( "01Jan09" ), True` | `"Jan 01, 2009"` |
| `DateFns::YYYYMMMDD( Date, Delimiter )` | `Date( "01Jan06" )` | `"2006Jan01"` |
| `DateFns::YYYYMMM w Hyphen( Date, Hyphen )` | `Date( "01Jan06" )` | `"2006-Jan"` |
| `DateFns::MonthAbbreviatedDateNumberYear( Date, Language )` | `Date( "01Jan06" )` | `"Jan  1 2006"` |
| `DateFns::Full Date String( Date, Style, Terse Month Name )` | `Date( "01Dec06" )` | `"December 1, 2006"` |

### Futures/Letter Formats

| Function | Example Input | Example Output |
|----------|--------------|----------------|
| `DateFns::MYY( Date )` | `Date( "01Jan06" )` | `"F06"` |
| `DateFns::MY( Date )` | `Date( "01Jan06" )` | `"F6"` |
| `DateFns::YYM( Date )` | `Date( "01Jan06" )` | `"06F"` |
| `DateFns::YM( Date )` | `Date( "01Jan06" )` | `"6F"` |
| `DateFns::YY( Date )` | `Date( "01Jan06" )` | `"06"` |
| `DateFns::YYYY( Date )` | `Date( "01Jan06" )` | `"2006"` |

### Other Converters

| Function | Description |
|----------|-------------|
| `DateFns::String( Date )` | Convert date to string, padding leading blanks with `"0"` |
| `DateFns::ShortDateFromDate( Date )` | Compact Base36 representation |
| `DateFns::DateFromShortDate( String )` | Reverse of ShortDateFromDate |
| `DateFns::DateToLetter( Date )` | Month letter from a date (e.g. `"K"` for May) |
| `DateFns::DateFromStringLYY( String )` | Parse `"K06"` -> first of May 2006 |
| `DateFns::MYY From YYYYMM( Double )` | `201404` -> `"J14"` |
| `DateFns::FiscalMonth( Date, Fiscal, Language )` | GS fiscal month name |
| `DateFns::FiscalDate( Date )` | GS fiscal date string (e.g. `"Jan07"`) |
| `DateFns::FiscalYr( Date, ReturnType )` | GS fiscal year (`"2007"` or `"07"`) |

---

## Miscellaneous Functions (Part 1)

### DateFns::Calendar Month End / Calendar Month Start

```
DateFns::Calendar Month End = Func(
    Date( DayOfTheMonth ),
    String( Holiday Location ) = "NYC",
)
Returns( Date(), Error() )

DateFns::Calendar Month Start = Func(
    Date( DateOfTheMonth ),
    String( Holiday Location ) = "NYC",
    Double( DayOfTheMonth ) = 1,
    Double( Restrict to Month ) = False,
)
Returns( Date(), Error() )
```

---

### DateFns::Most Recent Business Day

**Return the closest business day on or before the given date.**

```
DateFns::Most Recent Business Day = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
    String( Cal ) = "USD",
    Double( Exclude Date ) := False,
)
Returns( Date(), Error() )
```

```slang
@DateFns::Most Recent Business Day( Date( "04Jul06" ) );                         // 3Jul06
@DateFns::Most Recent Business Day( Date( "04Jul06" ), "GBP" );                  // 4Jul06
@DateFns::Most Recent Business Day( Date( "10Mar11" ), Exclude Date := True );   // 9Mar11
```

---

### DateFns::Move Off NonBusiness Day

**If business day, return as-is. Otherwise return the nearest business day (forward if Move Up, backward otherwise).**

```
DateFns::Move Off NonBusiness Day = Func(
    Date( Date ) = Pricing Date( "Security Database" ),
    String( Cal ) = "USD",
    Double( Move Up ) := True,
)
Returns( Date(), Error() )
```

---

### DateFns::Map Frequencies To RDates

**Convert a frequency string to an RDate.**

```
DateFns::Map Frequencies To RDates = Func(
    String( Frequency ),
)
Returns( RDate(), Error() )
```

Supported: `"Biennially"`, `"Annual"` / `"Annually"`, `"Semi-annual"` / `"Semi-annually"` / `"SemiAnnually"`, `"Quarterly"`, `"Monthly"`, `"Weekly"`, `"Daily/Business Days"`, `"Daily"`.

---

### DateFns::Difference in Months

```
DateFns::Difference in Months = Func(
    Date( Future ),
    Date( Past ),
)
Returns( Double(), Error() )
```

---

### DateFns::Week Number From Date

```
DateFns::Week Number From Date = Func(
    Date( Date ),
    Double( Legacy Behaviour ) := True,
)
Returns( Double() )
```

Use `Legacy Behaviour := False` for correct results when Jan 1 is a Monday.

---

### DateFns::Find First Day Iter

**Find the first occurrence of a specific weekday after (or before, if Reverse) a date.**

```
DateFns::Find First Day Iter = Func(
    Date( Date ),
    String( WeekD ),
    Double( Reverse ) := False,
)
Returns( Date(), Double() )
```

---

### DateFns::Daylight Saving Time

```
DateFns::Daylight Saving Time = Func(
    TimeOrDate,
    String( Location ),
)
Returns( Double(), Error() )
```

Supports `"NYC"` and `"LDN"` locations.

---

### DateFns::Age From Dates / Age From GsDtDates

```
DateFns::Age From Dates = Func( Date( DateOfBirth ), Date( AsOfDate ) ) Returns( Double() )
DateFns::Age From GsDtDates = Func( GsDtDate( DateOfBirth ), GsDtDate( AsOfDate ) ) Returns( Double() )
```

---

### DateFns::ComputeDaysInYear

```
DateFns::ComputeDaysInYear = Func( Double( Year ) ) Returns( Double() )
```

Returns 365 or 366.

---

### DateFns::Current Date In TimeZone

```
DateFns::Current Date In TimeZone = Func(
    String( TimeZone ),
    Double( Offset Mins ) := 0,
)
Returns( Date() )
```

---

### DateFns::Garish Age String

**Return a florid description of how old something is (e.g. "Jurassic", "Medieval", "New").**

```
DateFns::Garish Age String = Func( Date( RunDate ), Date( Date ) ) Returns( String() )
```

---

# Part 2: `_LIB Date Functions II`

## Table of Contents (Part 2)

- [String to Date Parsing Functions](#string-to-date-parsing-functions)
- [Ascftime Formatting](#ascftime-formatting)
- [Day of Week](#day-of-week)
- [Date to String (ISO)](#date-to-string-iso)
- [Week Functions](#week-functions)
- [Month Functions](#month-functions)
- [Quarter and Semester Functions](#quarter-and-semester-functions)
- [Year Functions](#year-functions)
- [Year Fraction and Tenor Functions](#year-fraction-and-tenor-functions)
- [Boolean / Test Functions](#boolean--test-functions)
- [Date Array Generation Functions](#date-array-generation-functions)
- [Rolling and Lagged Date Functions](#rolling-and-lagged-date-functions)
- [IMM and Index Rebalance Dates](#imm-and-index-rebalance-dates)
- [Miscellaneous Functions (Part 2)](#miscellaneous-functions-part-2)

---

## String to Date Parsing Functions

All parsing functions return `Date()` or an error.

| Function | Format | Default Separator | Example |
|----------|--------|-------------------|---------|
| `DateFns::DateFromStringYYYYMMDD` | YYYY-MM-DD | `"-"` | `"2006-01-01"` -> `1Jan06` |
| `DateFns::DateFromStringYYYYMMMDD` | YYYYMmmDD | `""` | `"2006Jan01"` -> `1Jan06` |
| `DateFns::DateFromStringMMDDYYYY` | MM/DD/YYYY | `"/"` | `"01/01/2006"` -> `1Jan06` |
| `DateFns::DateFromStringDDMMYYYY` | DD/MM/YYYY | `"/"` | `"01/01/2006"` -> `1Jan06` |
| `DateFns::DateFromStringMMDDYY` | MM/DD/YY | `"/"` | `"01/01/06"` -> `1Jan06` |
| `DateFns::DateFromStringDDMMYY` | DD/MM/YY | `"/"` | `"01/01/06"` -> `1Jan06` |
| `DateFns::DateFromStringYYMMDD` | YY/MM/DD | `"/"` | `"06/01/01"` -> `1Jan06` |
| `DateFns::DateFromStringDDMMMYY` | DDMmmYY | `""` | `"01Jan06"` -> `1Jan06` |
| `DateFns::DateFromStringMMMYY` | MMMYY | `""` | `"JAN15"` -> `1Jan15` |
| `DateFns::DateFromStringISO` | ISO 8601 | -- | `"2009-12-25"` -> `25Dec09` |
| `DateFns::Date From String Weekday DDMMMYY` | `"Thu 06May21"` | -- | Validates weekday |

Note on YY years: year > 51 maps to 19xx; year <= 51 maps to 20xx.

---

## Ascftime Formatting

**`DateFns::Ascftime` -- strftime-like date/time formatter.**

```
DateFns::Ascftime = Func(
    String( Format ),
    TimeOrDate,
    Option = Null,
    TZ := Null,
)
Returns( String(), Error() )
```

Key format specifiers:

| Specifier | Meaning | Example |
|-----------|---------|---------|
| `%Y` | 4-digit year | `"2006"` |
| `%y` | 2-digit year | `"06"` |
| `%G` | ISO week-numbering year (NOT calendar year) | `"2005"` for 1Jan06 |
| `%m` | Month number (01-12) | `"05"` |
| `%d` | Day (01-31, zero-padded) | `"08"` |
| `%e` | Day (1-31, space-padded) | `" 8"` |
| `%E` | Day with ordinal suffix | `"8th"` |
| `%b`, `%h` | Abbreviated month | `"May"` |
| `%B` | Full month name | `"May"` |
| `%a` | Abbreviated weekday | `"Sat"` |
| `%A` | Full weekday name | `"Saturday"` |
| `%H` | Hour 24h (00-23) | `"20"` |
| `%I` | Hour 12h (01-12) | `"08"` |
| `%M` | Minute (00-59) | `"05"` |
| `%S` | Second (00-59) | `"45"` |
| `%p` | am/pm | `"pm"` |
| `%T` | `%H:%M:%S` | `"13:23:45"` |
| `%D` | `%m/%d/%y` | `"05/08/06"` |
| `%Q` | Quarter (1Q-4Q) | `"2Q"` |
| `%q` | Futures month letter | `"K"` |
| `%V` | ISO 8601 week number | `"19"` |
| `%j` | Day of year (001-366) | `"128"` |
| `%Z` | Timezone name | `"GMT"` |

```slang
@DateFns::Ascftime( "%Y-%m-%d", Date( "08May06" ) );          // "2006-05-08"
@DateFns::Ascftime( "%B %E, %Y", Date( "08May06" ) );         // "May 8th, 2006"
@DateFns::Ascftime( "%Q %Y", Date( "08May06" ) );             // "2Q 2006"
```

---

## Day of Week

```
DateFns::Day of Week = Func(
    Date( Date ),
    Double( Use Full Day Name ) := True,
)
Returns( String() )
```

```slang
@DateFns::Day of Week( Date( "15Jan2025" ) );                  // "Wednesday"
@DateFns::Day of Week( Date( "15Jan2025" ), Use Full Day Name := False );  // "Wed"
```

---

## Date to String (ISO)

```
DateFns::DateToStringISO = Func( Date( Date ) ) Returns( String(), Error() )
```

```slang
@DateFns::DateToStringISO( Date( "25Dec09" ) );   // "2009-12-25T00:00:00"
```

---

## Week Functions

| Function | Description |
|----------|-------------|
| `DateFns::First Business Day Of Week( Date, Calendar )` | First business day of the week |
| `DateFns::Last Business Day Of Week( Date, Calendar )` | Last business day of the week |
| `DateFns::Is First Business Day Of Week( Date, Calendar )` | True if date is first biz day of week |
| `DateFns::Is Last Business Day Of Week( Date, Calendar )` | True if date is last biz day of week |
| `DateFns::Previous Last Business Day Of Week( Date, Calendar )` | Prior week's last biz day |
| `DateFns::Previous WeekDay( Date, Day, Calendar )` | Most recent occurrence of a specific weekday |
| `DateFns::Get Last N Week Ends( N, Base Date, Calendar )` | Array of last N weeks' end dates |
| `DateFns::WeekNumberToDate( WeekNumber, DateYear, Year )` | Week number -> date |
| `DateFns::WeekDayToDate( WeekDayStr, GivenDate, ForcePastOrFuture )` | Find nearest specific weekday |

---

## Month Functions

| Function | Description |
|----------|-------------|
| `DateFns::Start Of Month( Date, Cal )` | First day (or first biz day if Cal specified) |
| `DateFns::End Of Month( Date, Cal )` | Last business day of the month |
| `DateFns::GetBeginningOfMonth( Date )` | 1st calendar day |
| `DateFns::GetLastDateOfMonth( Date )` | Last calendar day |
| `DateFns::GetLastDayOfMonth( Date )` | Day number of last day (e.g. 31) |
| `DateFns::ComputeDaysInMonth( Date )` | Number of days in the month |
| `DateFns::Last Friday Of Month( Date )` | Last Friday |
| `DateFns::Last Xday Of Month( WeekDay, Date )` | Last occurrence of a weekday |
| `DateFns::LastBizdayOfMonth( Date, Hol )` | Last business day |
| `DateFns::Is Last Business Day Of Month( Date, Calendar )` | Boolean check |
| `DateFns::Xth Weekday Of Month( X, Weekday, Date )` | Nth occurrence of weekday (e.g. 3rd Sunday) |
| `DateFns::First Biz Weekday Of Month( Weekday, Date, Calendar )` | First business-day occurrence of weekday |
| `DateFns::Get Last N Month Ends( N, Base Date, Calendar )` | Array of last N months' end dates |
| `DateFns::RDateBtwStartOfMonths( Start, End )` | RDate difference between start-of-months |
| `DateFns::MonthsBtwStartOfMonths( Start, End )` | Month count between start-of-months |
| `DateFns::ComputeNumMonths( Date1, Date2 )` | Months between two dates |
| `DateFns::Different Months( D1, D2 )` | Signed month difference |

---

## Quarter and Semester Functions

| Function | Description |
|----------|-------------|
| `DateFns::Start Of Quarter( Date, Cal )` | First biz day of the quarter |
| `DateFns::End Of Quarter( Date, Cal, Months )` | Last biz day of the quarter |
| `DateFns::Start Of Semester( Date, Cal )` | First biz day of H1/H2 |
| `DateFns::End Of Semester( Date, Cal )` | Last biz day of half-year |
| `DateFns::Start Of N Monthly Period( Date, Nmonths, Cal, Offset )` | First biz day of an N-monthly period |
| `DateFns::Date To Quarter( Date, Year Format )` | `"2Q06"` or `"2Q2006"` |
| `DateFns::Quarter to Next Quarter( Quarter )` | Roll forward (e.g. `"3Q05"` -> `"4Q05"`) |
| `DateFns::Quarter to Previous Quarter( Quarter )` | Roll backward |
| `DateFns::General Quarter Roller( Quarter, N )` | Roll by N quarters |
| `DateFns::Quarter Month Ends( Date, Cal )` | All month-end biz dates in the quarter |
| `DateFns::Quarter Str To Quarter Start Date( Quarter, Cal )` | `"4Q12"` -> start date |
| `DateFns::Quarter Str To Quarter End Date( Quarter, Cal )` | `"4Q12"` -> end date |
| `DateFns::Last Calendar Day for Quarter( Date, Cal )` | Last calendar day of the quarter |
| `DateFns::First Calendar Day for Quarter( Date, Cal )` | First calendar day of the quarter |
| `DateFns::Get Last N Calendar Quarter Ends( N, Begin Date )` | Array of last N quarter-end dates |

---

## Year Functions

| Function | Description |
|----------|-------------|
| `DateFns::Start Of Year( Date, Cal )` | First day (or first biz day) of the year |
| `DateFns::End Of Year( Date, Cal )` | Last biz day of the year |
| `DateFns::Day Of Year( Date )` | Day number 1-366 |
| `DateFns::First Day Of Year from Year( Year )` | Jan 1st of given year |
| `DateFns::LastBizdayOfYear( Date, Hol )` | Last business day of the year |
| `DateFns::Get Last N Year Ends( N, Base Date, Calendar )` | Array of last N years' end dates |
| `DateFns::Last Day Of Fiscal Year( Date )` | Last date of fiscal year |
| `DateFns::First Day Of Fiscal Year( Date )` | First date of fiscal year |
| `DateFns::IsLeapYear( Year )` | True if leap year |
| `DateFns::ComputeDaysInYear( Year )` | 365 or 366 |

---

## Year Fraction and Tenor Functions

| Function | Description |
|----------|-------------|
| `DateFns::ComputeTenor( StartDate, EndDate, Calendar )` | RDate expressing difference between two dates |
| `DateFns::ComputeTenors( BaseDate, EndDate, Calendar )` | Array of RDates decomposing the difference |
| `DateFns::Tenor String From Months( Months )` | `60` -> `"5y"` |
| `DateFns::Months From Tenor String( RDate )` | `"5y"` -> `60` |
| `DateFns::RDate To Frequency( Freq )` | RDate -> `"Weekly"`, `"Monthly"`, etc. |
| `DateFns::GetYearFractionFromString( RDate )` | RDate string -> year fraction |
| `DateFns::GetStringFromYearFraction( YearFrac )` | Year fraction -> RDate string |
| `DateFns::YearFractionActAct( Start, End )` | Actual/Actual year fraction |
| `DateFns::YearFractionBiz( Holidays, Start, End )` | Business-day year fraction |
| `DateFns::AddYearFraction( Start, YearFraction )` | Add a year fraction to a date |

---

## Boolean / Test Functions

| Function | Description |
|----------|-------------|
| `DateFns::IsWeekend( Date, CalOrArray )` | True if weekend |
| `DateFns::IsWeekday( Date, CalOrArray )` | True if weekday |
| `DateFns::IsLeapYear( Year )` | True if leap year |
| `DateFns::IsEuroContractMonth( Date )` | True if Mar/Jun/Sep/Dec |
| `DateFns::IsEarlyClose( Date, Calendar )` | True if early close day |
| `DateFns::Is Last Business Day Of Week( Date, Calendar )` | True if last biz day of week |
| `DateFns::Is Last Business Day Of Month( Date, Calendar )` | True if last biz day of month |
| `DateFns::Is First Business Day Of Week( Date, Calendar )` | True if first biz day of week |
| `DateFns::Is Valid Holiday Calendar( Cal )` | True if valid calendar name |
| `DateFns::Is Date Within Relative Range( Input, Begin, Range, Ccy1, Ccy2 )` | True if within RDate range |

---

## Date Array Generation Functions

| Function | Description |
|----------|-------------|
| `DateFns::CalcDatesFromPeriod( Start, End, Offset, GsDateGen )` | Dates at interval between start/end |
| `DateFns::Calculate Dates( Start, End, Calendar, Interval, &Dates )` | Populate array by reference |
| `DateFns::Calculate Dates with RefDate( Start, End, RDate, Calendar, RefDate )` | Dates using multiples of RDate from reference |
| `DateFns::CalcBizDatesDateGen( Start, End, GsDateGen )` | Biz dates using GsDt calendar |
| `DateFns::Increasingly Spaced Dates( Start, Spacing, DateGen )` | Dates with increasing intervals |

---

## Rolling and Lagged Date Functions

| Function | Description |
|----------|-------------|
| `DateFns::Rolling Date( Reference Date, Rolling Months )` | Date N months back |
| `DateFns::ComputeLaggedDate( lag, date )` | Date lagged by string offset (e.g. `"1m"`, `"5y"`) |

---

## IMM and Index Rebalance Dates

| Function | Description |
|----------|-------------|
| `DateFns::Next IMM( Date, N, Roll )` | Nth next IMM date |
| `DateFns::Get Previous Russell Rebalance Date( Date )` | Last Russell Reconstitution (last Fri of June) |
| `DateFns::Get Previous Triple Witching Date( Date )` | Last Triple Witching (3rd Fri of Mar/Jun/Sep/Dec) |
| `DateFns::Get Previous MSCI Date( Date, Calendar )` | Last MSCI rebalance date |
| `DateFns::Get Last N MSCI Dates( N, Date, Calendar )` | Array of last N MSCI dates |
| `DateFns::Get Last N Triple Witching Dates( N, Date )` | Array of last N triple witching dates |
| `DateFns::Get Last N Russell Rebalance Dates( N, Date )` | Array of last N Russell dates |

---

## Miscellaneous Functions (Part 2)

| Function | Description |
|----------|-------------|
| `DateFns::Day To Number Mapping( Day )` | `"Mon"` -> number |
| `DateFns::DateRuleApply( Date, Rule, Cal1, Cal2 )` | Like built-in but handles absolute rules |
| `DateFns::From Time( Time, TZ )` | Convert Time to Date in timezone |
| `DateFns::Extract Date RegEx( template, re format )` | Extract date from string via regex |
| `DateFns::Extract Dates RegEx( template, re formats )` | Extract multiple dates |
| `DateFns::Contract Months Short( Contract Months )` | Compact contract month string |
| `DateFns::From Matlab Serial Date( Matlab Serial Date )` | Matlab serial date -> Slang Date |
| `DateFns::DatePart( Part, Date )` | SQL-style datepart extractor |
| `DateFns::Consecutive Date Ranges( Dates, Calendar )` | Group dates into consecutive ranges |
| `DateFns::Days To String( Days, nSignificant, Base Date )` | `1000` -> `"2y 8m"` |
| `DateFns::Diff Calendar Holidays( A, B, Start, End )` | Holidays in A but not in B |
| `DateFns::Next Holiday( Date, Calendar )` | Find the next holiday date |
| `DateFns::ISO 8601 Start Of First Week( Date )` | Monday of ISO week 1 |
| `DateFns::PromptForDateDialog( Default Date )` | UI dialog to select a date |

---

## Quick Reference

| Task | Function | Example |
|------|----------|---------|
| Month number -> name | `@DateFns::MonthName( N )` | `@DateFns::MonthName( 3 )` -> `"Mar"` |
| Month name -> number | `@DateFns::MonthNumber( Name, Lang )` | `@DateFns::MonthNumber( "Jan", "Short" )` -> `1` |
| Business dates in range | `@DateFns::CalcBizDates( Start, End, Cal )` | Returns array of dates |
| Count business days | `@DateFns::CountBizDates( Start, End, Cal )` | Returns integer |
| Is date a holiday? | `@DateFns::IsHoliday( Date, Cal )` | Returns True/False |
| Format YYYYMMDD | `@DateFns::YYYYMMDD( Date )` | `"20060101"` |
| Format DD-MMM-YYYY | `@DateFns::DDMMMYYYY w Hyphen( Date, True )` | `"01-Jan-2006"` |
| Parse YYYY-MM-DD | `@DateFns::DateFromStringYYYYMMDD( Str )` | Returns Date |
| Parse ISO 8601 | `@DateFns::DateFromStringISO( Str )` | Returns Date |
| Start of month | `@DateFns::Start Of Month( Date, Cal )` | First biz day of month |
| End of month | `@DateFns::End Of Month( Date, Cal )` | Last biz day of month |
| Start of quarter | `@DateFns::Start Of Quarter( Date, Cal )` | First biz day of quarter |
| End of quarter | `@DateFns::End Of Quarter( Date, Cal )` | Last biz day of quarter |
| Is weekend? | `@DateFns::IsWeekend( Date )` | True/False |
| Is leap year? | `@DateFns::IsLeapYear( Year )` | True/False |
| Compute tenor | `@DateFns::ComputeTenor( Start, End )` | Returns RDate |
| Flexible format | `@DateFns::Ascftime( Fmt, Date )` | strftime-like |
| GS month end | `@DateFns::Goldman Reporting Month End( Date )` | Returns Date |
