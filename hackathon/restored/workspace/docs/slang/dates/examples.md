# Date Functions -- Practical Examples

Real-world patterns and recipes using `_LIB Date Functions`.
All examples assume `Link( "_LIB Date Functions" )` is in scope.

---

## Table of Contents

1. [Date Formatting for Reports](#date-formatting-for-reports)
2. [Parsing Dates from External Sources](#parsing-dates-from-external-sources)
3. [Business Day Calculations](#business-day-calculations)
4. [Holiday-Aware Logic](#holiday-aware-logic)
5. [Period Boundaries (Month / Quarter / Year)](#period-boundaries-month--quarter--year)
6. [Date Range Iteration](#date-range-iteration)
7. [Month Name and Letter Conversions](#month-name-and-letter-conversions)
8. [GS Reporting Period Logic](#gs-reporting-period-logic)
9. [Tenor and Year Fraction Calculations](#tenor-and-year-fraction-calculations)
10. [Date Comparison and Validation](#date-comparison-and-validation)
11. [Combining Multiple Patterns](#combining-multiple-patterns)

---

## Date Formatting for Reports

### Format a date for a US-style report header

```slang
Today = Date( "15Apr2025" );

// "April 15, 2025"
Header = @DateFns::Full Date String( Today );

// "Apr 15, 2025"
Short Header = @DateFns::Full Date String( Today, Terse Month Name := True );

// UK style: "15 April 2025"
UK Header = @DateFns::Full Date String( Today, True );
```

### Format a date as ISO for file names or APIs

```slang
Today = Date( "15Apr2025" );

ISO = @DateFns::YYYYMMDD( Today, Delimiter := "-" );
// "2025-04-15"

Compact = @DateFns::YYYYMMDD( Today );
// "20250415"

File Name = "report_" + @DateFns::YYYYMMDD( Today ) + ".csv";
// "report_20250415.csv"
```

### Format with Ascftime for maximum flexibility

```slang
Today = Date( "08May2025" );

// "Thursday, May 8th, 2025"
Pretty = @DateFns::Ascftime( "%A, %B %E, %Y", Today );

// "2Q 2025"
Quarter Label = @DateFns::Ascftime( "%Q %Y", Today );

// "K25" (futures month-letter code)
Futures Code = @DateFns::Ascftime( "%q%y", Today );
```

### Multi-language month formatting

```slang
D = Date( "15Mar2025" );

// English (default)
@DateFns::DDMMMYYYY w Hyphen( D, True );                              // "15-Mar-2025"

// Spanish
@DateFns::DDMMMYY( D, True, Delimiter := "-", Language := "Short Spanish" );  // "15-Mar-25"

// Italian (full month names)
@DateFns::MonthName( D.Month, "Italian" );                            // "Marzo"
```

---

## Parsing Dates from External Sources

### Parse various string formats

```slang
// From a CSV with MM/DD/YYYY
D1 = @DateFns::DateFromStringMMDDYYYY( "04/15/2025" );      // 15Apr25

// From a European system with DD/MM/YYYY
D2 = @DateFns::DateFromStringDDMMYYYY( "15/04/2025" );      // 15Apr25

// From an API returning ISO 8601
D3 = @DateFns::DateFromStringISO( "2025-04-15T14:30:00" );   // 15Apr25

// From a Bloomberg-style YYYYMMDD
D4 = @DateFns::DateFromStringYYYYMMDD( "20250415", "" );     // 15Apr25

// From a compact futures-style "K25"
D5 = @DateFns::DateFromStringLYY( "K25" );                   // 1May25
```

### Parse with error handling

```slang
Input = "not-a-date";
Result = @DateFns::DateFromStringISO( Input );
If( IsError( Result ) )
{
    Printf( "Failed to parse date: %s\n", Input );
};
```

---

## Business Day Calculations

### Get all business days in a date range

```slang
Start = Date( "01Jan2025" );
End   = Date( "10Jan2025" );

// Without any holiday calendar (weekends only)
Biz Days = @DateFns::CalcBizDates( Start, End );

// With NYC holiday calendar
NYC Biz Days = @DateFns::CalcBizDates( Start, End, "NYC" );

// Count them
Num Days = @DateFns::CountBizDates( Start, End, "NYC" );
Printf( "There are %d business days\n", Num Days );
```

### Find the most recent business day

```slang
Today = Date( "04Jul2025" );   // Independence Day

// Most recent business day (on or before)
Last Biz = @DateFns::Most Recent Business Day( Today, "USD" );
// 3Jul2025

// Previous business day (excluding today)
Prev Biz = @DateFns::Most Recent Business Day( Today, "USD", Exclude Date := True );
```

### Move off a non-business day

```slang
Date To Check = Date( "04Jul2025" );

// Move forward to next biz day
Next Biz = @DateFns::Move Off NonBusiness Day( Date To Check, "USD", Move Up := True );

// Move backward to prior biz day
Prev Biz = @DateFns::Move Off NonBusiness Day( Date To Check, "USD", Move Up := False );
```

### Signed business day count from a reference date

```slang
Ref = Date( "01Jan2025" );
Target = Date( "10Jan2025" );

Forward = @DateFns::CountBizDates from RefDate( Ref, Target, "NYC" );
// Positive number

Backward = @DateFns::CountBizDates from RefDate( Target, Ref, "NYC" );
// Negative number (Target is after Ref, so Ref < Target means positive; Ref > Target means negative)
```

---

## Holiday-Aware Logic

### Check if a date is a holiday

```slang
D = Date( "04Jul2025" );

Is Hol = @DateFns::IsHoliday( D, "GS_NYC" );          // True
Is Hol LDN = @DateFns::IsHoliday( D, "GS_LDN" );      // False

// Check multiple calendars at once (ANY match)
Is Hol Any = @DateFns::IsHoliday( D, [ "GS_NYC", "GS_LDN" ] );  // True

// Weekends: by default weekends ARE treated as holidays
Is Weekend Hol = @DateFns::IsHoliday( Date( "05Jul2025" ), "GS_NYC" );   // True (Saturday)
// Skip weekends:
Is Non Weekend Hol = @DateFns::IsHoliday( Date( "05Jul2025" ), "GS_NYC", True );  // False
```

### Check if holiday on ALL calendars simultaneously

```slang
// Christmas is a holiday in both NYC and LDN
@DateFns::IsHolidaySimultaneous( Date( "25Dec2025" ), [ "GS_LDN", "GS_NYC" ] );  // True

// July 4th is only a US holiday
@DateFns::IsHolidaySimultaneous( Date( "04Jul2025" ), [ "GS_LDN", "GS_NYC" ] );  // False
```

### Get the name of a holiday

```slang
Name = @DateFns::Holiday Name( Date( "04Jul2025" ), "GS_NYC" );
// "(GS_NYC) Independence Day"

Name No Cal = @DateFns::Holiday Name( Date( "04Jul2025" ), "GS_NYC", Include Cal Name := False );
// "Independence Day"
```

### List all holidays in a date range

```slang
Hol Curve = @DateFns::Holiday Curve( "GS_NYC", Date( "01Jan2025" ), Date( "31Dec2025" ) );
// GCurve with all NYC holidays in 2025
```

---

## Period Boundaries (Month / Quarter / Year)

### Month start and end

```slang
D = Date( "15Mar2025" );

// Calendar boundaries
First = @DateFns::GetBeginningOfMonth( D );     // 1Mar25
Last  = @DateFns::GetLastDateOfMonth( D );      // 31Mar25

// Business day boundaries
First Biz = @DateFns::Start Of Month( D, "USD" );   // First biz day of March
Last Biz  = @DateFns::End Of Month( D, "USD" );     // Last biz day of March
```

### Quarter start and end

```slang
D = Date( "15May2025" );

Q Start = @DateFns::Start Of Quarter( D, "USD" );   // First biz day of Q2
Q End   = @DateFns::End Of Quarter( D, "USD" );     // Last biz day of Q2

Q Label = @DateFns::Date To Quarter( D );            // "2Q25"
Q Num   = @DateFns::Calendar Quarter( D );           // 2
```

### Year start and end

```slang
D = Date( "15May2025" );

Y Start = @DateFns::Start Of Year( D, "USD" );      // First biz day of 2025
Y End   = @DateFns::End Of Year( D, "USD" );         // Last biz day of 2025
```

### Check if a date is a period boundary

```slang
D = Date( "31Mar2025" );

@DateFns::Is Last Business Day Of Month( D );        // True/False
@DateFns::Is Last Business Day Of Week( D );          // True/False
@DateFns::Is First Business Day Of Week( D );          // True/False
@DateFns::IsCalendarMonthStart( Date( "01Mar2025" ) ); // True
```

### Get arrays of period-end dates

```slang
// Last 12 month-ends
Month Ends = @DateFns::Get Last N Month Ends( 12, Today(), Holiday Calendar := "NYC" );

// Last 4 week-ends
Week Ends = @DateFns::Get Last N Week Ends( 4, Today(), Holiday Calendar := "NYC" );

// Last 5 year-ends
Year Ends = @DateFns::Get Last N Year Ends( 5, Today(), Holiday Calendar := "NYC" );
```

---

## Date Range Iteration

### Iterate over business days in a range

```slang
Biz Dates = @DateFns::CalcBizDates( Date( "01Jan2025" ), Date( "31Jan2025" ), "NYC" );

ForEach( D, Biz Dates )
{
    Printf( "Processing: %s (%s)\n", String( D ), @DateFns::Day of Week( D, Use Full Day Name := False ) );
};
```

### Iterate over calendar days

```slang
Cal Days = @DateFns::CalcCalDays( Date( "01Jan2025" ), Date( "05Jan2025" ) );

ForEach( D, Cal Days )
{
    If( @DateFns::IsWeekend( D ) )
        Printf( "%s is a weekend\n", String( D ) )
    :
        Printf( "%s is a weekday\n", String( D ) );
};
```

### Generate dates at regular intervals

```slang
Link( "_LIB Date Functions" );

Start = Date( "01Jan2025" );
End   = Date( "31Dec2025" );
Dates = [];

@DateFns::Calculate Dates( Start, End, "NYC", RDate( "1m" ), &Dates );
// Dates is now populated with monthly dates
```

---

## Month Name and Letter Conversions

### Round-trip: date -> letter -> month name -> number -> date

```slang
D = Date( "15May2025" );

// Date -> letter
Letter = @DateFns::DateToLetter( D );                   // "K"

// Letter -> month name
Month = @DateFns::LetterToMonth( Letter );               // "May"

// Month name -> number
Num = @DateFns::MonthNumber( Month, "Short" );           // 5

// Reconstruct
New Date = DateFromMDY( Num, 1, D.Year );                // 1May2025
```

### Build a map of month letters for display

```slang
For( I = 1; I <= 12; I++ )
{
    Printf( "%s = %s (%s)\n",
        @DateFns::MonthLetter( I ),
        @DateFns::MonthName( I ),
        @DateFns::MonthName( I, "EnglishFull" )
    );
};
// F = Jan (January)
// G = Feb (February)
// ...
// Z = Dec (December)
```

---

## GS Reporting Period Logic

### Get GS reporting month boundaries

```slang
D = Date( "15Mar2025" );

GS Month End   = @DateFns::Goldman Reporting Month End( D );
GS Month Start = @DateFns::Goldman Reporting Month Start( D );

Printf( "GS month: %s to %s\n", String( GS Month Start ), String( GS Month End ) );
```

### Get all GS reporting month-ends in a range

```slang
Month Ends = @DateFns::Goldman Reporting Month End Dates In Range(
    Date( "01Jan2025" ),
    Date( "31Dec2025" )
);

ForEach( ME, Month Ends )
{
    Printf( "GS Month End: %s\n", String( ME ) );
};
```

### Check if today is a GS reporting boundary

```slang
D = Today();

If( @DateFns::IsGoldmanReportingMonthEnd( D ) )
    Print( "Today is a GS reporting month end\n" );

If( @DateFns::IsGoldmanReportingQuarterEnd( D ) )
    Print( "Today is a GS reporting quarter end\n" );

If( @DateFns::IsGoldmanReportingYearEnd( D ) )
    Print( "Today is a GS reporting year end\n" );
```

---

## Tenor and Year Fraction Calculations

### Compute the tenor between two dates

```slang
Start = Date( "01Jan2025" );
End   = Date( "01Apr2025" );

Tenor = @DateFns::ComputeTenor( Start, End );
// RDate approximately "3m"

// Get individual components (years, months, weeks, days)
Tenors = @DateFns::ComputeTenors( Start, End );
```

### Convert between tenor strings and months

```slang
@DateFns::Tenor String From Months( 60 );     // "5y"
@DateFns::Tenor String From Months( 18 );     // "18m"
@DateFns::Months From Tenor String( "5y" );    // 60
@DateFns::Months From Tenor String( "3m" );    // 3
```

### Year fraction calculations

```slang
Start = Date( "01Jan2025" );
End   = Date( "01Jul2025" );

Frac = @DateFns::YearFractionActAct( Start, End );
// ~0.4959 (181 / 365)
```

### Map frequency names to RDates

```slang
@DateFns::Map Frequencies To RDates( "Annually" );    // RDate( "1y" )
@DateFns::Map Frequencies To RDates( "Quarterly" );   // RDate( "3m" )
@DateFns::Map Frequencies To RDates( "Monthly" );     // RDate( "1m" )
@DateFns::Map Frequencies To RDates( "Weekly" );      // RDate( "1w" )
```

---

## Date Comparison and Validation

### Validate a holiday calendar

```slang
If( @DateFns::Is Valid Holiday Calendar( "GS_NYC" ) )
    Print( "Valid calendar\n" )
:
    Print( "Invalid calendar\n" );
```

### Check if a year is a leap year

```slang
@DateFns::IsLeapYear( 2024 );                    // True
@DateFns::IsLeapYear( 2025 );                    // False
@DateFns::IsLeapYear( Date( "01Jan2024" ) );     // True (accepts Date too)

Days = @DateFns::ComputeDaysInYear( 2024 );      // 366
```

### Weekend / weekday checks

```slang
@DateFns::IsWeekend( Date( "05Jul2025" ) );       // True (Saturday)
@DateFns::IsWeekday( Date( "07Jul2025" ) );       // True (Monday)
```

### Age calculation

```slang
DOB = Date( "15Jun1990" );
Today = Date( "15Jun2025" );

Age = @DateFns::Age From Dates( DOB, Today );     // 35
```

---

## Combining Multiple Patterns

### Generate a report for each business day in a quarter

```slang
D = Date( "15Feb2025" );

Q Start = @DateFns::Start Of Quarter( D, "USD" );
Q End   = @DateFns::End Of Quarter( D, "USD" );

Biz Days = @DateFns::CalcBizDates( Q Start, Q End, "NYC" );

Printf( "Quarter %s: %d business days from %s to %s\n",
    @DateFns::Date To Quarter( D ),
    Size( Biz Days ),
    @DateFns::YYYYMMDD( Q Start, Delimiter := "-" ),
    @DateFns::YYYYMMDD( Q End, Delimiter := "-" )
);

ForEach( Day, Biz Days )
{
    // Process each business day
    Printf( "  %s (%s)\n",
        @DateFns::DDMMMYYYY w Hyphen( Day, True ),
        @DateFns::Day of Week( Day, Use Full Day Name := False )
    );
};
```

### Build a holiday summary for multiple calendars

```slang
Calendars = [ "GS_NYC", "GS_LDN" ];
Start = Date( "01Jan2025" );
End   = Date( "31Dec2025" );

ForEach( Cal, Calendars )
{
    Hol Curve = @DateFns::Holiday Curve( Cal, Start, End );
    Printf( "\n=== %s Holidays ===\n", Cal );

    ForComponent( Knot, Hol Curve )
    {
        Printf( "  %s: %s\n",
            @DateFns::DDMMMYYYY w Hyphen( Knot.Date, True ),
            Knot.Value
        );
    };
};
```

### Find differences between two holiday calendars

```slang
Diffs = @DateFns::Diff Calendar Holidays( "GS_NYC", "GS_LDN", Date( "01Jan2025" ), Date( "31Dec2025" ) );
// Holidays in NYC but not in LDN

Printf( "NYC has %d holidays that LDN does not:\n", Size( Diffs ) );
ForEach( D, Diffs )
{
    Name = @DateFns::Holiday Name( D, "GS_NYC", Include Cal Name := False );
    Printf( "  %s: %s\n", @DateFns::DDMMMYYYY w Hyphen( D, True ), Name );
};
```

### DST-aware time zone processing

```slang
Check Date = Date( "15Jul2025" );

NYC DST = @DateFns::Daylight Saving Time( Check Date, "NYC" );
LDN DST = @DateFns::Daylight Saving Time( Check Date, "LDN" );

Printf( "On %s: NYC DST=%s, LDN DST=%s\n",
    String( Check Date ),
    If( NYC DST ) "Yes" : "No",
    If( LDN DST ) "Yes" : "No"
);
```
