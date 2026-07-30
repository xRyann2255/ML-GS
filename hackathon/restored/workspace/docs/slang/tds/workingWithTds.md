# Working with TDS (Tabular Data Sets) in Slang

## Overview

A **Tabular Data Set (TDS)** in Slang is a powerful mechanism for analyzing large tabular data. It is conceptually similar to a table in a relational database or a Pandas DataFrame, but it allows direct manipulation within Slang using a rich set of optimized operators.

**Key characteristics:**

| Feature | Description |
|---------|-------------|
| **Purpose** | Optimized for data analysis, not transactional operations |
| **Scalability** | Can process datasets larger than virtual memory |
| **Row-by-row** | Pipelined architecture -- memory usage is independent of total dataset size |
| **Indexing** | Supports database indexes for fast search |
| **Operators** | Rich set of mathematical, statistical, and relational operators |
| **Storage** | Binary files efficient for read/write across Linux and Windows |

The two core objects are:

- **`TdsSchema`** -- defines the column structure (names, types, primary keys), like a DDL in SQL.
- **`TdsDataSet`** -- holds the data itself; the base class for all TDS operators.

---

## TDS Column Types

TDS supports a variety of column types. The most common are:

| TDS Type | Slang Equivalent | Description |
|----------|------------------|-------------|
| `"double"` | `Double` | 64-bit floating point |
| `"float"` | -- | 32-bit floating point |
| `"int32"` | -- | 32-bit signed integer |
| `"int64"` | -- | 64-bit signed integer |
| `"uint8"` | -- | 8-bit unsigned (often used for booleans) |
| `"uint32"` | -- | 32-bit unsigned integer |
| `"date"` | `Date` | Calendar date |
| `"time"` | `Time` | Date and time |
| `"string"` | `String` | Variable-length string |
| `"fstring8"` | -- | Fixed-width string (8 bytes) |
| `"fstring16"` | -- | Fixed-width string (16 bytes) |
| `"fstring32"` | -- | Fixed-width string (32 bytes) |
| `"fstring64"` | -- | Fixed-width string (64 bytes) |

> **Tip:** Fixed-width strings (`fstringN`) are faster for comparisons and sorting. Use variable-length `"string"` only when column values vary greatly in length.

---

## Creating a TdsSchema

A `TdsSchema` defines the columns, their types, and optionally a primary key:

```slang
// Basic schema: column names and types
Schema = TdsSchema(
    [ "Name", "Age", "City" ],
    [ "fstring32", "double", "fstring16" ]
);

// Schema with a primary key (3rd argument)
Schema = TdsSchema(
    [ "StudentID", "Major", "GPA" ],
    [ "fstring16", "fstring16", "double" ],
    [ "StudentID" ]
);

// Compound primary key
Schema = TdsSchema(
    [ "Company", "Date", "Price" ],
    [ "fstring64", "date", "double" ],
    [ "Company", "Date" ]
);
```

### Inspecting a Schema

```slang
Schema.ColumnNames();       // [ "Name", "Age", "City" ]
Schema.ColumnTypes();       // [ "fstring32", "double", "fstring16" ]
Schema.PrimaryKey();        // [] or [ "StudentID" ]
Schema.nCols();             // 3
Schema.ColumnExists( "Age" ); // True
Schema.ColumnIndex( "Age" ); // 1
```

### Specialized Schema Constructors

```slang
// Date-series schema (ID column is a date)
DS Schema = TdsDateSerSchema( [ "Price", "Volume" ], [ "double", "double" ] );

// Time-series schema (ID column is a time)
TS Schema = TdsTimeSerSchema( [ "Value" ], [ "double" ] );

// Schema from a Structure or Typed Structure
S = {| "Name" := "Alice", "Age" := 30 |};
Auto Schema = TdsStructSchema( S );
```

---

## Creating a TdsDataSet

### From an Array of Arrays (`TdsArray`)

The simplest way. The first row determines the schema if no explicit schema is provided:

```slang
Data = [
    [ "Alice",   30, "New York" ],
    [ "Bob",     24, "London"   ],
    [ "Charlie", 35, "Paris"    ]
];

// Auto-detect schema from first row
Tds = TdsArray( Data );

// Or provide an explicit schema for type control
Schema = TdsSchema( [ "Name", "Age", "City" ], [ "fstring32", "double", "fstring16" ] );
Tds = TdsArray( Data, Schema := Schema );
```

### From an Array of Structures

```slang
Data = [
    {| "Name" := "Alice", "Age" := 30 |},
    {| "Name" := "Bob",   "Age" := 24 |}
];
Tds = TdsArray( Data );
```

### From a Structure of Arrays

```slang
Data = {| "Name" := [ "Alice", "Bob" ], "Age" := [ 30, 24 ] |};
Tds = TdsArray( Data );
```

### Building Row by Row (`TdsInMemory`)

When you need to build a TDS incrementally:

```slang
Schema = TdsSchema(
    [ "StudentID", "Major", "GPA" ],
    [ "fstring16", "fstring16", "double" ],
    [ "StudentID" ]
);

Records = TdsInMemory( Schema );
Records.Append( [ "M11123", "History",     2.11 ] );
Records.Append( [ "M11355", "Mathematics", 2.89 ] );
Records.Append( [ "M10788", "English",     2.55 ] );
Records.SortByPK();
```

### Dummy / Test Data

```slang
Schema = TdsSchema( [ "A", "B", "C" ], [ "double", "double", "fstring16" ] );
Dummy = TdsDummyDataSet( Schema, 100 );  // 100 rows of test data
```

---

## Accessing Data

### Printing

```slang
Print( My Tds );          // pretty-printed table
Print( My Tds, "\n" );    // with trailing newline
```

### Basic Properties

```slang
My Tds.Size();            // number of rows
My Tds.nCols();           // number of columns
My Tds.IsEmpty();          // True if no rows (faster than Size() == 0)
My Tds.schema();           // returns the TdsSchema
```

### Extracting Rows

```slang
// Get rows by range (0-indexed, inclusive)
First 10 = My Tds.Rows( 0, 9 );
Last 5   = My Tds.Rows( -5, 0 );   // negative = from end
First Row = My Tds.Rows( 0, 0 );

// Top / Bottom N by column ranking
Top 5 = TdsTop( My Tds, 5, [ "GPA" ] );
Bottom 5 = TdsBottom( My Tds, 5, [ "GPA" ] );
```

### Extracting Columns

```slang
// Select specific columns
Subset = TdsColumns( My Tds, [ "Name", "Age" ] );
// or equivalently
Subset = TdsProject( My Tds, [ "Name", "Age" ] );

// All columns except some
Without Age = TdsProjectAllBut( My Tds, [ "Age" ] );

// Column range by index
First 3 Cols = TdsColumnRange( My Tds, 0, 2 );
```

### Converting to Other Types

```slang
Arr   = My Tds.toArray();          // Array of Arrays
Structs = My Tds.toStructArray();  // Array of Structures
SOA   = My Tds.toStructOfArrays(); // Structure of Arrays
Col   = My Tds.toColumnArray( "Name" ); // Single column as flat Array
CSV   = TdsCsvWriteStr( My Tds );  // CSV string
```

---

## Filtering Rows

### TdsRestrict (Lambda Predicate)

Filter rows using a boolean lambda:

```slang
// Keep only rows where GPA > 3.0
High GPA = TdsRestrict( My Tds, \row -> row.GPA > 3.0 );

// Method syntax
High GPA = My Tds.Restrict( \row -> row.GPA > 3.0 );
```

### TdsWhere (SQL-like WHERE Clause)

Two syntax options -- lambda (recommended) or string expression:

```slang
// Lambda form (recommended)
Result = TdsWhere( My Tds, \r -> r.Major == "Biology" && r.GPA > 3.0 );

// String form
Result = TdsWhere( My Tds, "Major == \"Biology\" && GPA > 3.0" );

// Date comparisons
Result = TdsWhere( My Tds, \r -> r.Date >= Date( "1Jan2020" ) );
```

### Boolean TDS Filtering

Create boolean masks and use them to index:

```slang
Mask = TdsGt( My Tds, 3.0 );      // boolean TDS: 1 where col > 3.0
Filtered = My Tds[ Mask ];         // apply mask

// Combining conditions
Mask A = My Tds.Gt( 3.0 );
Mask B = My Tds.Lt( 4.0 );
Combined = TdsAnd( Mask A, Mask B );
Filtered = My Tds[ Combined ];

// Other comparison operators
TdsEq( tds, value )    // ==
TdsNe( tds, value )    // !=
TdsGt( tds, value )    // >
TdsGe( tds, value )    // >=
TdsLt( tds, value )    // <
TdsLe( tds, value )    // <=
TdsIn( tds, [ val1, val2 ] )        // value in set
TdsBetween( tds, minVal, maxVal )    // value in range
```

### Key-based Filtering (Index Search)

For fast lookups using binary search on indexed/primary-key columns:

```slang
// Exact match on key columns
Result = TdsKeyEq( My Tds, [ "Company" ], [ "IBM" ] );

// Range search
Result = TdsKeyRange( My Tds, [ "Date" ], [ Date( "1Jan2020" ) ], [ Date( "31Dec2020" ) ] );

// Multiple value lookup
Result = TdsKeyIn( My Tds, [ "Company" ], [ [ "IBM" ], [ "AAPL" ], [ "GOOG" ] ] );
```

### Null Handling

```slang
TdsIsNull( tds )       // boolean: 1 where first column is null
TdsIsNotNull( tds )    // boolean: 1 where first column is not null
TdsRemoveNulls( tds )  // remove rows with any null in any column
TdsFillFwd( tds )      // fill nulls forward
TdsReplaceNulls( tds, 0 )  // replace all nulls with 0
TdsReplaceNulls( tds, {| "Price" := 0.0, "Name" := "Unknown" |} );  // per-column defaults
```

---

## Adding and Transforming Columns

### TdsExtend (Add Columns)

Add new columns computed from existing data:

```slang
// Constant column
Extended = TdsExtend( My Tds, "IBM", "Ticker", "fstring8" );

// Computed column using a lambda
Extended = TdsExtend( My Tds, \r -> r.Price * r.Volume, "Notional", "double" );

// Multiple new columns with a lambda
Extended = TdsExtend( My Tds,
    \r -> [ r.GPA / 4 * 100, r.GPA > 3.0 ],
    [ "Percentage", "Honor Roll" ],
    [ "double", "uint8" ]
);

// Multiple constant columns
Extended = TdsExtend( My Tds, [ "NYU", 2024 ], [ "University", "Year" ], [ "fstring16", "uint32" ] );

// Using an existing TDS expression
Extended = TdsExtend( My Tds, My Tds.Price * My Tds.Volume, "Notional", "double" );
```

### TdsMap (Single-column Result)

Create a new single-column TDS from a transformation:

```slang
// Lambda
Sums = TdsMap( My Tds, \row -> row.A + row.B, "Total", "double" );

// Constant
Ones = TdsMap( My Tds, 1, "Flag", "uint8" );
```

### TdsSelect (SQL-like SELECT)

Combines column selection, new column creation, and filtering in one call:

```slang
// Select columns + add new columns + filter
Result = TdsSelect( My Tds,
    [ "Company", "Price", "NewCol=Price+1" ],
    "Price > 50"
);

// Select all columns + add columns
Result = TdsSelect( My Tds,
    [ "*", "Doubled=Price*2" ],
    \r -> r.Volume > 1000000
);
```

### Renaming Columns

```slang
Renamed = TdsRename( My Tds, [ "Old Name" ], [ "New Name" ] );
```

---

## Sorting and Primary Keys

```slang
// Set the primary key
My Tds.PrimaryKey( [ "Company", "Date" ] );

// Sort by primary key
My Tds.SortByPK();

// Sort by arbitrary columns
My Tds.Sort( [ "GPA" ] );          // ascending
My Tds.Sort( [ "GPA" ], [ 1 ] );   // descending (1 = descending)

// Check if sorted
My Tds.IsSortedByPK();   // True/False
```

---

## Joins

TDS supports SQL-style joins:

```slang
// Inner Join
Result = TdsJoin( Left Tds, Right Tds, [ "Key" ] );

// Left Outer Join
Result = TdsLeftJoin( Left Tds, Right Tds, [ "Key" ] );

// Right Outer Join
Result = TdsRightJoin( Left Tds, Right Tds, [ "Key" ] );

// Full Outer Join (Union Join)
Result = TdsUnionJoin( Left Tds, Right Tds, [ "Key" ] );

// Merge by Key (Union Join + remove duplicate columns)
Result = TdsMergeByKey( Left Tds, Right Tds, [ "Key" ] );

// Semi Join (keep LHS rows that have a match in RHS)
Result = TdsSemiJoin( Left Tds, Right Tds, [ "Key" ] );

// Semi Minus (keep LHS rows that do NOT have a match in RHS)
Result = TdsSemiMinus( Left Tds, Right Tds, [ "Key" ] );
```

> **Tip:** After a join, use `TdsUniqColumns()` to remove duplicate key columns.

### Join with Different Key Names

```slang
Result = TdsJoin( Left Tds, Right Tds, [ "LeftKey" ], [ "RightKey" ] );
```

---

## Aggregation and Grouping

### TdsGroupBy

SQL-style GROUP BY with reduction operators:

```slang
// Count by Major
Counts = TdsGroupBy( Records, [ "Major" ], [ [ "*", "COUNT" ] ] );

// Average GPA by Major
Avg GPA = TdsGroupBy( Records, [ "Major" ], [ [ "GPA", "AVG" ] ] );

// Multiple aggregations
Stats = TdsGroupBy( Records, [ "Major" ], [
    [ "GPA", "AVG" ],
    [ "GPA", "MIN" ],
    [ "GPA", "MAX" ],
    [ "*", "COUNT" ]
]);

// Function-form syntax
Stats = TdsGroupBy( Records, [ "Major" ], [ "AVG(GPA)", "COUNT(Major)" ] );
```

Available reduction operators: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `FIRST`, `LAST`, `UNIQ`.

### Whole-Dataset Aggregation

```slang
TdsSum( My Tds )          // sum of each numeric column (1 row)
TdsAvg( My Tds )          // average of each numeric column
TdsMin( My Tds )          // min
TdsMax( My Tds )          // max
TdsStd( My Tds )          // standard deviation
TdsMedian( My Tds )       // median
TdsSummaryStats( My Tds ) // all stats in one pass
```

### Moving Window and Cumulative

For time/date series:

```slang
// 5-period moving average
MA 5 = TdsAvg( My Tds, 5 );

// Cumulative sum
Cum Sum = TdsSum( My Tds, 0, cumul := 1 );

// Exponential moving average
EMA = TdsMovAvgExp( My Tds, 20 );
```

---

## Concatenation and Merging

```slang
// Vertical concatenation (stack rows)
Combined = TdsConcat( [ Tds1, Tds2, Tds3 ] );

// Horizontal merge (align by ID/row)
Merged = TdsMerge( [ Tds1, Tds2 ] );

// Zip (assumes rows align perfectly)
Zipped = TdsZip( [ Tds1, Tds2 ] );
```

---

## Arithmetic Operations

TDS supports element-wise arithmetic between two TDS or a TDS and a scalar:

```slang
Sum  = TdsAdd( A, B );     // A + B
Diff = TdsSub( A, B );     // A - B
Prod = TdsMul( A, B );     // A * B
Quot = TdsDiv( A, B );     // A / B

// Also works with Slang operators on TDS columns
Result = My Tds.Price * My Tds.Volume;
```

---

## Removing Duplicates

```slang
// Remove duplicate rows based on all columns
Unique = TdsUniq( My Tds );

// Remove duplicates based on specific columns
Unique = TdsUniq( My Tds, [ "Name", "Date" ] );
```

---

## File I/O

### Reading and Writing TDS Binary Files

```slang
// Select a database
DB = TdsDB( "local" );

// Save to disk
TdsSave( My Tds, "my_table", DB );

// Read from disk
Loaded = TdsRead( "my_table", DB );

// Save as temp file (auto-deleted when process ends)
Temp = TdsTemp( My Tds );
```

### CSV I/O

```slang
// Read CSV file
Tds = TdsCsvReadFile( "data.csv" );

// Read CSV string
Tds = TdsCsvReadStr( CSV String );

// Write CSV file
TdsCsvWriteFile( My Tds, "output.csv" );

// Write CSV string
CSV = TdsCsvWriteStr( My Tds );
```

### Parquet I/O

```slang
// Write to Parquet
TdsToParquet( My Tds, "my_table", DB );

// Read from Parquet
Tds = TdsFromParquet( "my_table", DB );
```

---

## Caching

```slang
// Cache entire TDS in memory (must fit)
Cached = My Tds.Cache();

// The result of most TDS operations is lazy.
// Use .Cache() when you need to materialize
// or will iterate multiple times.
```

---

## Iteration

### ForEach-Style Row Iteration

Use `TdsMap`, `TdsExtend`, or `TdsRestrict` with lambdas for row-level operations -- these are the idiomatic approach. Direct row iteration is also available via `TdsKeyIter`:

```slang
// Iterate over groups by partial key
Iter = TdsKeyIter( My Tds, [ "Company" ] );
While( Iter.More() )
{
    Sub Tds = Iter.Next();
    Key = Iter.Key();
    Print( "Company: ", Key, " rows: ", Sub Tds.Size(), "\n" );
};
```

---

## Time Series

```slang
// Lag (yesterday's values for today)
Lagged = TdsLag( My Tds, 1 );

// Lead (tomorrow's values for today)
Forward = TdsLead( My Tds, 5 );

// Daily returns
Returns = ( My Tds - TdsLag( My Tds, 1 ) ) / TdsLag( My Tds, 1 );

// Time range extraction
Subset = TdsTimeRange( My Tds, Date( "1Jan2020" ), Date( "31Dec2020" ) );
```

---

## Quick Comparison: TDS vs SQL

| SQL | TDS Equivalent |
|-----|----------------|
| `SELECT *` | `TdsColumns( tds, [] )` or `TdsSelect( tds, [ "*" ] )` |
| `SELECT col1, col2` | `TdsColumns( tds, [ "col1", "col2" ] )` |
| `SELECT *, col1+col2 AS total` | `TdsExtend( tds, \r -> r.col1 + r.col2, "total", "double" )` |
| `WHERE condition` | `TdsWhere( tds, \r -> condition )` or `TdsRestrict( tds, \r -> condition )` |
| `ORDER BY col` | `tds.Sort( [ "col" ] )` |
| `GROUP BY col` | `TdsGroupBy( tds, [ "col" ], [ ... ] )` |
| `INNER JOIN` | `TdsJoin( left, right, [ "key" ] )` |
| `LEFT JOIN` | `TdsLeftJoin( left, right, [ "key" ] )` |
| `UNION ALL` | `TdsConcat( [ tds1, tds2 ] )` |
| `DISTINCT` | `TdsUniq( tds )` |
| `COUNT(*) GROUP BY` | `TdsGroupBy( tds, [ "col" ], [ [ "*", "COUNT" ] ] )` |
