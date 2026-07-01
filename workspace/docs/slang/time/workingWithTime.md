# Working with Dates and Time in Slang

## Overview

Slang has three core temporal data types:

| Type | Description | Example |
|------|-------------|---------|
| **Date** | Calendar date (no time component) | `Date( "17Apr2025" )` |
| **Time** | Full timestamp (date + time) | `Time()` returns current time |
| **RDate** | Relative date offset | `RDate( "3b" )` = 3 business days |

## Date

### Creating Dates

The standard format is `DDMMMYYYY`:

- `DD` -- day of month (01-31)
- `MMM` -- abbreviated month name (Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec; case-insensitive)
- `YYYY` -- four-digit year

```slang
My Date = Date( "10Apr2025" );
New Year = Date( "01Jan2026" );
Short Form = Date( "1Jan2026" );     // leading zero is optional
```

### Accessing Date Components

```slang
D = Date( "17Apr2025" );
Print( D.Month, "\n" );             // 4
Print( D.Day, "\n" );               // 17
Print( D.Year, "\n" );              // 2025
```

### Today's Date

```slang
Today = Date( Today() );
// Or use Today() directly where a date is expected
```

### Casting to String

```slang
D = Date( "10Apr2025" );
S = String( D );                    // "10Apr25"
```

### Formatted Output

```slang
D = Date( "17Apr2025" );
Printf( "Date: %s\n", String( D ) );
Msg = Sprintf( "The date is %s", String( D ) );
```

## Date Arithmetic

### Adding/Subtracting Calendar Days

Dates support arithmetic with numeric offsets (in calendar days):

```slang
D = Date( "10Apr2025" );
Tomorrow = D + 1;                   // 11Apr2025
Yesterday = D - 1;                  // 09Apr2025
Next Week = D + 7;                  // 17Apr2025
```

### Difference Between Dates

Subtracting two dates gives the number of calendar days between them:

```slang
Start = Date( "01Jan2025" );
End   = Date( "31Jan2025" );
Days  = End - Start;                // 30
```

### Using RDate for Business Day Arithmetic

`RDate` represents relative date offsets with awareness of business days, months, and years:

```slang
D = Date( "10Apr2025" );

// Business days (skip weekends/holidays)
Three Bdays Later = D + RDate( "3b" );

// Calendar months
Next Month = D + RDate( "1m" );

// Calendar years
Next Year = D + RDate( "1y" );

// Negative offsets
Last Week Bday = D + RDate( "-5b" );
```

Common RDate suffixes:

| Suffix | Meaning |
|--------|---------|
| `b` | Business days |
| `d` | Calendar days |
| `m` | Months |
| `y` | Years |
| `w` | Weeks |

### End of Month

```slang
D = Date( "15Mar2025" );
End Of Mar = D + RDate( "em" );     // end of month
```

## Date Comparison

Dates support all comparison operators:

```slang
D1 = Date( "01Jan2025" );
D2 = Date( "31Dec2025" );

If( D1 < D2 )
{
    Print( "D1 is before D2\n" );
};

If( D1 == D2 )
{
    Print( "Same date\n" );
};

If( D1 != D2 )
{
    Print( "Different dates\n" );
};
```

## Error Checking on Dates

Use `IsError()` to check if a date is valid:

```slang
D = Date( "invalid" );
If( IsError( D ) )
{
    Print( "Invalid date\n" );
};
```

## Time

### Current Time

```slang
Now = Time();                       // current timestamp
Print( Now, "\n" );                 // e.g., "Thu 17Apr2025 02:30:15 pm"
```

### Time Components

```slang
Now = Time();
Print( Now.Date, "\n" );           // Date component
Print( Now.Hour, "\n" );           // Hour (0-23)
Print( Now.Minute, "\n" );         // Minute (0-59)
Print( Now.Second, "\n" );         // Second (0-59)
```

### Time Arithmetic

```slang
Now = Time();
// Times can be compared
If( Time1 < Time2 )
{
    Print( "Time1 is earlier\n" );
};
```

### Measuring Elapsed Time

Use `TimeIt` to measure how long a block takes:

```slang
TimeIt
{
    // Code to measure
    For( I = 0; I < 10000; I++ )
    {
        X = I * I;
    };
};
// Prints elapsed time to output
```

Or measure manually:

```slang
Start = ProcessCpuTime();
// ... work ...
End = ProcessCpuTime();
Elapsed = End - Start;
Printf( "Elapsed CPU time: %.3f seconds\n", Elapsed );
```

## Practical Patterns

### Iterating Over a Date Range

```slang
/****************************************************************
**  Routine: Private::Process Date Range
**
**  Iterates over each calendar day in a range.
****************************************************************/
Private::Process Date Range = Func(
    Date( Start Date ),
    Date( End Date ),
)
Returns()
{
    Current = Start Date;
    While( Current <= End Date )
    {
        Printf( "Processing: %s\n", String( Current ) );
        Current = Current + 1;
    };
};

@Private::Process Date Range( Date( "01Jan2025" ), Date( "05Jan2025" ) );
```

### Checking if a Date Falls on a Weekend

```slang
/****************************************************************
**  Routine: Private::Is Weekend
**
**  Returns True if the given date is a Saturday or Sunday.
**  DayOfWeek: 0=Sun, 1=Mon, ..., 5=Fri, 6=Sat
****************************************************************/
Private::Is Weekend = Func(
    Date( D ),
)
Returns( Double() )
{
    Day Of Week = D.DayOfWeek;
    Return( Day Of Week == 0 || Day Of Week == 6 );
};
```

### Formatting Dates for Display

```slang
D = Date( "17Apr2025" );

// Custom format using Sprintf and components
Formatted = Sprintf( "%02d/%02d/%04d", D.Month, D.Day, D.Year );
// "04/17/2025"

// ISO-like format
Iso = Sprintf( "%04d-%02d-%02d", D.Year, D.Month, D.Day );
// "2025-04-17"
```

### Date Validation

```slang
/****************************************************************
**  Routine: Private::Parse Date Safe
**
**  Attempts to parse a date string; returns Null on failure.
****************************************************************/
Private::Parse Date Safe = Func(
    String( Date String ),
)
Returns( Date(), Null )
{
    Try( Ex )
    {
        D = Date( Date String );
        If( IsError( D ) )
        {
            Return( Null );
        };
        Return( D );
    }
    :
    {
        Return( Null );
    };
};

Result = @Private::Parse Date Safe( "29Feb2025" );
If( TypeOf( Result ) == "Null" )
{
    Print( "Invalid date\n" );
};
```

## Quick Reference

| Task | Function / Operator | Example |
|------|---------------------|---------|
| Create date | `Date( "DDMMMYYYY" )` | `Date( "17Apr2025" )` |
| Today | `Today()` | Returns today's date |
| Current time | `Time()` | Full timestamp |
| Get month | `D.Month` | 1-12 |
| Get day | `D.Day` | 1-31 |
| Get year | `D.Year` | e.g. 2025 |
| Day of week | `D.DayOfWeek` | 0=Sun, 6=Sat |
| Add days | `D + N` | Calendar days |
| Business days | `D + RDate( "3b" )` | Skip weekends/holidays |
| Add months | `D + RDate( "1m" )` | Calendar months |
| Date difference | `D2 - D1` | Number of calendar days |
| Compare | `<`, `>`, `==`, `!=`, `<=`, `>=` | Standard comparison |
| Validate | `IsError( D )` | True if invalid |
| Cast to string | `String( D )` | e.g. "17Apr25" |
| CPU time | `ProcessCpuTime()` | For benchmarking |
| Measure block | `TimeIt { ... }` | Prints elapsed time |

---

## See Also

- [Date type and RDate](../dates/dates-base.md) -- creating dates, date arithmetic, RDate offsets, comparisons
- [DateFns:: library](../dates/date-functions.md) -- formatting, parsing, holidays, business days
- [Time:: library functions](commonFunctions.md) -- Time formatting, parsing, timezone, ISO 8601
- [Time:: examples](examples.md) -- practical recipes for Time functions
