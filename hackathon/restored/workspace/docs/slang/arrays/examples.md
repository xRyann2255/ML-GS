# Array Library -- Practical Examples

Real-world patterns and recipes using `_LIB Array Functions`.
All examples assume `Link( "_LIB Array Functions" )` is in scope.

---

## Table of Contents

1. [Filtering and Selecting Data](#filtering-and-selecting-data)
2. [Set Operations: Comparing Two Lists](#set-operations-comparing-two-lists)
3. [Grouping and Classification](#grouping-and-classification)
4. [Sorting and Ranking](#sorting-and-ranking)
5. [Flattening, Splitting, and Reshaping](#flattening-splitting-and-reshaping)
6. [Building Arrays from Scratch](#building-arrays-from-scratch)
7. [Extracting Fields from Arrays of Structures](#extracting-fields-from-arrays-of-structures)
8. [Deduplication and Uniqueness](#deduplication-and-uniqueness)
9. [Searching and Binary Search](#searching-and-binary-search)
10. [Shuffling and Sampling](#shuffling-and-sampling)
11. [Aggregation and Summation](#aggregation-and-summation)
12. [Array Manipulation: Splice, Rotate, Merge](#array-manipulation-splice-rotate-merge)
13. [Combining Multiple Patterns](#combining-multiple-patterns)

---

## Filtering and Selecting Data

### Keep only elements matching a condition

```slang
Numbers = [ 1, 2, 3, 4, 5, 6, 7, 8 ];
Evens = @Array::Grep( Numbers, \x -> Mod( x, 2 ) == 0 );
// Evens = [ 2, 4, 6, 8 ]
```

### Get indices of matching elements

```slang
Data = [ 10, 20, 30, 40, 50 ];
High Indices = @Array::Grep Indices( Data, \x -> x >= 30 );
// High Indices = [ 2, 3, 4 ]
```

### Filter by data type

```slang
Mixed = [ 1, "hello", 3.14, "world", Null ];
Strings Only = @Array::Grep Type( Mixed, "String" );
// Strings Only = [ "hello", "world" ]
```

### Boolean mask selection

```slang
Names = [ "Alice", "Bob", "Charlie", "Diana" ];
Mask  = [ True, False, True, False ];
Selected = @Array::Select( Names, Mask );
// Selected = [ "Alice", "Charlie" ]
```

### Delete elements matching a property in place

```slang
Scores = [ 85, 42, 91, 37, 78, 55 ];
@Array::DeleteByProperty( &Scores, \x -> x < 50 );
// Scores = [ 85, 91, 78, 55 ]
```

### Find the first element satisfying a condition

```slang
Items = [ "alpha", "beta", "gamma", "delta" ];
First Long = @Array::First( Items, \s -> Size( s ) > 4 );
// First Long = "alpha"

// With a default if nothing matches:
First Z = @Array::First( Items, \s -> StrSearch( s, "z" ) >= 0, Default := "none", Throw := False );
// First Z = "none"
```

### Take elements while a condition holds

```slang
Sorted Vals = [ 1, 2, 3, 10, 20, 30 ];
Small Prefix = @Array::Take While( Sorted Vals, \x -> x < 10 );
// Small Prefix = [ 1, 2, 3 ]
```

---

## Set Operations: Comparing Two Lists

### Find elements only in one list (relative complement)

```slang
Current = [ "USD", "EUR", "GBP", "JPY" ];
Old     = [ "USD", "EUR", "CHF" ];

// What's new?
Added = @Array::Diff( Current, Old );
// Added = [ "GBP", "JPY" ]

// What was removed?
Removed = @Array::Diff( Old, Current );
// Removed = [ "CHF" ]
```

### Full set comparison in one call

```slang
Left  = [ 1, 3, 5, 7, 9 ];
Right = [ 2, 3, 5, 8, 9 ];

R = @Array::Diff All( Left, Right,
    Do Intersection := True,
    Do Union := True,
    Sort Outputs := True,
);
// R.Left Only    = [ 1, 7 ]
// R.Right Only   = [ 2, 8 ]
// R.Intersection = [ 3, 5, 9 ]
// R.Union        = [ 1, 2, 3, 5, 7, 8, 9 ]
```

### Case-sensitive string diffs

```slang
A = [ "AAA", "aAA", "aaa" ];
B = [ "aaA", "AAA" ];

R = @Array::Diff All( A, B,
    Case Sensitive := True,
    Do Intersection := True,
    Sort Outputs := True,
);
// R.Left Only    = [ "aAA", "aaa" ]
// R.Right Only   = [ "aaA" ]
// R.Intersection = [ "AAA" ]
```

### Intersection of multiple lists

```slang
Lists = [ [ 1, 3, 5, 6, 7, 9 ],
          [ 3, 6, 6, 9 ],
          [ 2, 4, 6, 8, 9 ] ];

Common = @Array::Intersection Many( Lists, Sort := True );
// Common = [ 6, 9 ]
```

### Union of multiple arrays

```slang
All Currencies = @Array::Union( [ "USD", "EUR" ], [ "EUR", "GBP" ], [ "JPY" ] );
// All Currencies = [ "EUR", "GBP", "JPY", "USD" ] (sorted and unique)
```

### Check if two lists are disjoint

```slang
@Array::Disjoint( [ 1, 2, 3 ], [ 4, 5, 6 ] );  // True
@Array::Disjoint( [ 1, 2, 3 ], [ 3, 4, 5 ] );  // False
```

---

## Grouping and Classification

### Group by a function

```slang
Data = [ 1, 2, 3, 4, 5, 6, 7, 8, 9 ];
Groups = @Array::Group By( Data, \x -> If( Mod( x, 2 ) == 0 ) "Even" : "Odd" );
// Groups = Structure( "Even", [ 2, 4, 6, 8 ]; "Odd", [ 1, 3, 5, 7, 9 ] )
```

### Partition into two buckets (True/False)

```slang
Items = [ 10, -5, 3, -2, 7, -1 ];
Parts = @Array::Partition( Items, \x -> x > 0 );
// Parts = GStructure( True, [ 10, 3, 7 ]; False, [ -5, -2, -1 ] )
```

### Group by multiple keys

```slang
Trades = [
    {| Currency := "USD", Amount := 200 |},
    {| Currency := "USD", Amount := 50 |},
    {| Currency := "EUR", Amount := 200 |},
    {| Currency := "EUR", Amount := 75 |},
];

Grouped = @Array::MultiKey Group By(
    Trades,
    [ "Currency", "Large" ],
    [ \t -> t.Currency, \t -> t.Amount > 100 ],
);
// Returns array of structures with "Currency", "Large", and "Data" keys
```

### Count element frequencies

```slang
Words = [ "the", "cat", "sat", "on", "the", "mat", "the" ];
Freq = @Array::Element Frequencies( Words );
// Freq = GStructure( "the", 3; "cat", 1; "sat", 1; "on", 1; "mat", 1 )

Most Common = @Array::Most Frequent Elements( Words );
// Most Common = [ "the" ]
```

### Bucket parallel arrays

```slang
Regions   = [ "US", "US", "EU", "US", "EU", "EU" ];
Revenues  = [ 100,  200,  150,  300,  250,  175 ];

By Region = @Array::Bucket Pairwise( Regions, Revenues, \x -> Sum( x ) );
// GStructure( "US", 600; "EU", 575 )
```

---

## Sorting and Ranking

### Sort and get a copy (RValue)

```slang
Sorted = @Array::Sort( [ 5, 3, 8, 1 ] );
// Sorted = [ 1, 3, 5, 8 ]  (original unchanged)
```

### Sort by a custom key

```slang
Words = [ "banana", "apple", "plum", "kiwi" ];
By Length = @Array::Sort( Words, Ordering := \a, b -> Size( a ) <=> Size( b ) );
// By Length = [ "plum", "kiwi", "apple", "banana" ]
```

### Get sort order (for sync-sort)

```slang
Values = [ 30, 10, 20 ];
Idx = @Array::Sort Indices( Values );
// Idx = [ 1, 2, 0 ]

// Apply same reordering to a parallel array:
Labels = [ "C", "A", "B" ];
Sorted Labels = @Array::Extract Selection( Labels, Idx );
// Sorted Labels = [ "A", "B", "C" ]
```

### Rank elements

```slang
Scores = [ 100, 11, -4, 11, 9, 11 ];
Ranks = @Array::Rank( Scores );
// Ranks = [ 0, 1, 5, 1, 4, 1 ]

// With average for duplicates:
Avg Ranks = @Array::Rank With Possible Duplicates( Scores, Dups_Avg := True );
// Avg Ranks = [ 0, 2, 5, 2, 4, 2 ]
```

### Verify an array is sorted

```slang
@Array::Is Sorted( [ 1, 2, 3 ] );                                // True
@Array::Is Sorted( [ 1, 2, 2, 3 ] );                             // Error(...)
@Array::Is Sorted( [ 1, 2, 2, 3 ], Allow Duplicates := True );   // True
```

---

## Flattening, Splitting, and Reshaping

### Flatten nested arrays

```slang
Nested = [ 3, [ 1 ], [ [ 4 ] ], [ 1, 5, 9 ] ];
Flat = @Array::Flatten( Nested );
// Flat = [ 3, 1, 4, 1, 5, 9 ]
```

### Round-trip flatten/unflatten

```slang
Matrix = [ [ 1, 2, 3 ], [ 4, 5, 6 ] ];
Flat = @Array::Flatten( Matrix );
// Flat = [ 1, 2, 3, 4, 5, 6 ]

Restored = @Array::Unflatten( Flat, [ 2, 3 ] );
// Restored = [ [ 1, 2, 3 ], [ 4, 5, 6 ] ]
```

### Split into fixed-size chunks

```slang
Data = @Array::FillRange( 1, 100 );
Chunks = @Array::Split( Data, 25 );
// 4 chunks of 25 elements each
```

### Split into a fixed number of buckets

```slang
Items = [ 1, 2, 3, 4, 5, 6, 7 ];
Buckets = @Array::Bucketize( Items, 3 );
// [ [ 1, 2, 3 ], [ 4, 5 ], [ 6, 7 ] ]
```

### Transpose a matrix

```slang
M = [ [ 1, 2 ], [ 3, 4 ], [ 5, 6 ] ];
T = @Array::Transpose( M );
// T = [ [ 1, 3, 5 ], [ 2, 4, 6 ] ]
```

### Select columns from a table

```slang
Table = [ [ "Alice", 30, "NYC" ],
          [ "Bob",   25, "LA"  ],
          [ "Carol", 35, "SF"  ] ];

Names And Cities = @Array::Table Projection( Table, [ 0, 2 ] );
// [ [ "Alice", "NYC" ], [ "Bob", "LA" ], [ "Carol", "SF" ] ]
```

---

## Building Arrays from Scratch

### Generate a range

```slang
@Array::FillRange( 1, 5 );           // [ 1, 2, 3, 4, 5 ]
@Array::FillRange( 10, 0, -3 );      // [ 10, 7, 4, 1 ]
```

### Generate with a function

```slang
Squares = @Array::Generate( 5, \i -> i * i );
// [ 0, 1, 4, 9, 16 ]

Dates = @Array::Generate( 7, \i -> Today() + i );
// Next 7 days
```

### Generate a date sequence

```slang
Monthly = @Array::Gen Line( Date( "2024-01-01" ), Date( "2024-12-01" ), RDate( "1m" ) );
// First of each month in 2024
```

### Linearly spaced values

```slang
Points = @Array::ArrayLinspace( 0, 1, 11 );
// [ 0, 0.1, 0.2, ..., 1.0 ]
```

### Repeat a pattern

```slang
Pattern = @Array::Repeat( [ 1, 0 ], 4 );
// [ 1, 0, 1, 0, 1, 0, 1, 0 ]
```

---

## Extracting Fields from Arrays of Structures

### Pluck a single field

```slang
People = [
    {| Name := "Alice", Age := 30 |},
    {| Name := "Bob",   Age := 25 |},
    {| Name := "Carol", Age := 35 |},
];

Names = @Array::Pluck( People, "Name" );
// [ "Alice", "Bob", "Carol" ]

Ages = @Array::Array from Array of Structs( People, "Age" );
// [ 30, 25, 35 ]
```

### Handle missing fields

```slang
Mixed = [
    {| Name := "Alice", Dept := "Eng" |},
    {| Name := "Bob" |},               // No Dept
    {| Name := "Carol", Dept := "HR" |},
];

// Include Null for missing:
Depts = @Array::Pluck( Mixed, "Dept" );
// [ "Eng", Null, "HR" ]

// Skip missing:
Depts = @Array::Pluck( Mixed, "Dept", Skip Missing Elements := True );
// [ "Eng", "HR" ]
```

### Union structures together

```slang
Defaults = {| Color := "Red", Size := 10, Weight := 5 |};
Override = {| Color := "Blue", Material := "Steel" |};

Config = @Array::StructureUnion( [ Override, Defaults ] );
// {| Color := "Blue", Material := "Steel", Size := 10, Weight := 5 |}
// First value seen for each key wins
```

---

## Deduplication and Uniqueness

### Sorted unique

```slang
@Array::Unique( [ 3, 1, 2, 1, 3 ] );
// [ 1, 2, 3 ]
```

### Stable unique (preserve insertion order)

```slang
@Array::Unique Stable( [ 5, 2, 4, 5, 2, 3 ] );
// [ 5, 2, 4, 3 ]
```

### Find duplicates

```slang
@Array::Duplicates( [ "a", "b", "a", "c", "b", "a" ] );
// [ "a", "b" ]
```

### Check uniqueness

```slang
@Array::Is Unique( [ 1, 2, 3 ] );      // True
@Array::Is Unique( [ 1, 2, 1 ] );      // False
```

### Remove duplicates in place

```slang
A = [ 3, 1, 4, 3, 3 ];
@Array::Remove Duplicates( &A, SortIt := True );
// A = [ 1, 3, 4 ]
```

### Find sequential repeats

```slang
@Array::Get Sequential Repeats( [ 1, 3, 4, 4, 5, 5, 2, 2, 1 ] );
// [ [ 4, 4 ], [ 5, 5 ], [ 2, 2 ] ]

// With tabular output:
@Array::Get Sequential Repeats( [ 1, 3, 4, 4, 5, 5, 2, 2, 1 ], Tabular Output := True );
// [ {| Value := 4, Count := 2 |}, {| Value := 5, Count := 2 |}, {| Value := 2, Count := 2 |} ]
```

---

## Searching and Binary Search

### Simple search with index output

```slang
Idx = -1;
Found = @Array::Contains( [ "apple", "banana", "cherry" ], "banana", Index := Idx );
// Found = True, Idx = 1
```

### Binary search on sorted data

```slang
Sorted = [ 10, 20, 30, 40, 50 ];
@Array::LowerBound( Sorted, 25 );  // 2 (first position >= 25)
@Array::UpperBound( Sorted, 30 );  // 3 (first position > 30)
```

### Binary search with predicate

```slang
// Array must have property: once predicate becomes True, it stays True
Data = [ 1, 1, 1, 4, 4 ];
@Array::Binary Search First( Data, \x -> Mod( x, 2 ) == 0 );
// 3
```

### Find subarray location

```slang
Haystack = [ "A", "B", "C", "D", "E" ];
@Array::Find SubArray( Haystack, [ "C", "D" ] );  // 2
@Array::Find SubArray( Haystack, [ "D", "C" ] );  // -1
```

### Find nearest value

```slang
Pillars = [ 10, 20, 30, 40, 50 ];
@Array::Find Nearest( Pillars, 27 );                       // 2 (index of 30)
@Array::Find Nearest( Pillars, 27, Return Value := True );  // 30
@Array::Find Nearest( Pillars, 27, Return Both := True );   // [ 2, 30 ]
```

---

## Shuffling and Sampling

### Reproducible shuffle

```slang
A = [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ];
Shuffled = @Array::Deterministic Shuffle( A, 42 );
// Same result every time with seed 42
```

### In-place shuffle without touching global Random state

```slang
B = [ "a", "b", "c", "d", "e" ];
@Array::Shuffle In Place Stateless( &B, 12345 );
// B is now shuffled reproducibly
```

### Random sample without replacement

```slang
Population = @Array::FillRange( 1, 100 );
Sample = @Array::Random Sample( Population, 10, Seed := 42 );
// 10 unique random elements from 1..100
```

---

## Aggregation and Summation

### Sum ignoring errors

```slang
Data = [ 1, 2, Error Value, 4, Error Value ];
@Array::Sum( Data );           // 7 (errors skipped by default)
@Array::Sum( Data, False );    // would include errors and fail
```

### Check if values sum to zero within tolerance

```slang
Weights = [ 0.1, 0.2, 0.3, 0.4 ];
@Array::Sums To Within Tolerance( Weights, 1.0 );  // True
```

### Running sum

```slang
@Array::Running Sum( [ 1, 2, 3, 4 ] );
// [ 1, 3, 6, 10 ]
```

### Find minimum/maximum with index

```slang
@Array::Min Index( [ 30, 10, 20 ] );
// {| Value := 10, Index := 1 |}

@Array::Max Index( [ 30, 10, 20 ] );
// {| Value := 30, Index := 0 |}
```

### Argmin/Argmax by a function

```slang
@Array::Arg Min( [ 1, -5, 2 ], \x -> Abs( x ) );
// {| Index := 0, Value := 1 |}   -- smallest absolute value

@Array::Arg Max( [ 1, -5, 2 ], \x -> Abs( x ) );
// {| Index := 1, Value := -5 |}  -- largest absolute value
```

### Add totals row to a table

```slang
Table = [ [ "Q1", 100, 200 ],
          [ "Q2", 150, 250 ],
          [ "Q3", 200, 300 ] ];

With Totals = @Array::Add Totals( &Table, 1 );
// Appends [ "TOTAL", 450, 750 ]
```

---

## Array Manipulation: Splice, Rotate, Merge

### Remove and replace elements (Splice)

```slang
A = [ "a", "b", "c", "d", "e", "f" ];
Removed = @Array::Splice( &A, 2, 3, "x", "y" );
// A       = [ "a", "b", "x", "y", "f" ]
// Removed = [ "c", "d", "e" ]
```

### Splice with a replacement array

```slang
A = [ "a", "b", "c", "d", "e", "f" ];
B = [ "w", "x", "y", "z" ];
@Array::Splice Add In Replacement Array( &A, 2, 3, B );
// A = [ "a", "b", "w", "x", "y", "z", "f" ]
```

### Insert after a value

```slang
Steps = [ "Init", "Validate", "Execute", "Cleanup" ];
@Array::Insert After Value( Steps, "Validate", "Authorize" );
// [ "Init", "Validate", "Authorize", "Execute", "Cleanup" ]
```

### Rotate array

```slang
@Array::Rotate( [ 1, 2, 3, 4, 5 ], 2 );
// [ 3, 4, 5, 1, 2 ]

@Array::Rotate( [ 1, 2, 3, 4, 5 ], -1 );
// [ 5, 1, 2, 3, 4 ]
```

### Shift (with fill)

```slang
@Array::Shift( [ 1, 2, 3, 4, 5 ], 2 );
// [ 3, 4, 5, Error Value, Error Value ]

@Array::Shift( [ 1, 2, 3, 4, 5 ], -2, Fill := 0 );
// [ 0, 0, 1, 2, 3 ]
```

### Merge arrays with fallback

```slang
Primary   = [ 1, Null, 3, Null ];
Fallback  = [ 10, 20, 30, 40 ];
Merged = @Array::Merge( Primary, Fallback, Null );
// [ 1, 20, 3, 40 ]
```

### Interleave two arrays

```slang
@Array::Interlace Array( [ 1, 2, 3 ], [ "a", "b" ] );
// [ 1, "a", 2, "b", 3 ]
```

---

## Combining Multiple Patterns

### Deduplicated union of config overrides

```slang
// Priority: User > Team > Global
User Config   = {| Theme := "Dark", Font Size := 14 |};
Team Config   = {| Theme := "Light", Language := "EN" |};
Global Config = {| Language := "FR", Tab Size := 4 |};

Final = @Array::StructureUnion( [ User Config, Team Config, Global Config ] );
// {| Theme := "Dark", Font Size := 14, Language := "EN", Tab Size := 4 |}
```

### Sync-sort two parallel arrays

```slang
Names  = [ "Charlie", "Alice", "Bob" ];
Scores = [ 75, 90, 85 ];

Idx = @Array::Sort Indices( Scores );
Sorted Names  = @Array::Extract Selection( Names, Idx );
Sorted Scores = @Array::Extract Selection( Scores, Idx );
// Sorted Names  = [ "Charlie", "Bob", "Alice" ]
// Sorted Scores = [ 75, 85, 90 ]
```

### Filter, group, then aggregate

```slang
Transactions = [
    {| Region := "US", Amount := 100 |},
    {| Region := "EU", Amount := -50 |},
    {| Region := "US", Amount := 200 |},
    {| Region := "EU", Amount := 150 |},
    {| Region := "US", Amount := -30 |},
];

// Step 1: Keep positive amounts only
Positive = @Array::Grep( Transactions, \t -> t.Amount > 0 );

// Step 2: Group by region
By Region = @Array::Group By( Positive, \t -> t.Region );

// Step 3: Sum each group
ForComponent( Region, By Region )
{
    Amounts = @Array::Pluck( By Region[ Region ], "Amount" );
    Printf( "%s: %f\n", Region, Sum( Amounts ) );
};
// US: 300
// EU: 150
```

### Flatten nested results and deduplicate

```slang
Search Results = [ [ "A", "B" ], [ "B", "C", "D" ], [ "A", "E" ] ];
All Unique = @Array::Flatten Unique( &Search Results );
// [ "A", "B", "C", "D", "E" ]
```

### Bin-pack items into fixed-capacity containers

```slang
Items = [ 7, 3, 2, 5, 4, 1, 6 ];
Unpacked = [];
Packed = @Array::Bin Pack( Items, 10, &Unpacked );
// Packed groups items so each bin's sum <= 10
// Unpacked receives any item exceeding bin size
```

---

## See Also

- [commonFunctions.md](commonFunctions.md) -- full function reference (signatures, parameters)
- [workingWithArrays.md](workingWithArrays.md) -- built-in array operations guide
- Source: `_LIB Array Functions`, `Test: Lib Array Functions`
