# Working with Arrays in Slang

## Overview

Arrays in Slang are ordered, 0-indexed collections that can hold elements of **mixed types** (Strings, Doubles, Dates, Structures, other Arrays, etc.). They are one of the most commonly used data types in Slang.

## Creating Arrays

### Literal Syntax (Preferred)

```slang
Fruits = [ "apple", "banana", "cherry" ];
Numbers = [ 1, 2, 3, 4, 5 ];
Mixed = [ "hello", 42, Date( "10Apr2025" ), [ 1, 2 ] ];
Empty = [];
```

### Constructor Syntax

```slang
My Array = Array();               // empty array
My Array = Array( 10 );           // array pre-allocated with 10 null elements
```

> **Prefer `[]` over `Array()`.** The literal syntax is cleaner and more idiomatic.

## Accessing Elements

Arrays are **0-indexed**:

```slang
Fruits = [ "apple", "banana", "cherry" ];
First  = Fruits[ 0 ];             // "apple"
Last   = Fruits[ 2 ];             // "cherry"

// Negative indexing is NOT supported in Slang.
// Use Size() to get the last element:
Last   = Fruits[ Size( Fruits ) - 1 ];  // "cherry"
```

## Modifying Elements

```slang
Fruits = [ "apple", "banana", "cherry" ];
Fruits[ 1 ] = "blueberry";        // replace "banana"
// Fruits is now [ "apple", "blueberry", "cherry" ]
```

## Size / Length

```slang
Count = Size( Fruits );           // 3
If( Size( My Array ) == 0 )
{
    Print( "Array is empty\n" );
};
```

## Concatenation

Use `++` to concatenate two arrays into a new array:

```slang
A = [ 1, 2, 3 ];
B = [ 4, 5, 6 ];
C = A ++ B;                       // [ 1, 2, 3, 4, 5, 6 ]
```

Use `ArrayConcat` to append one array onto another in place:

```slang
A = [ 1, 2, 3 ];
B = [ 4, 5, 6 ];
ArrayConcat( A, B );
// A is now [ 1, 2, 3, 4, 5, 6 ]
```

## Iteration

### ForEach

The idiomatic way to iterate. `Element` receives a **copy** of each value; use `&Element` for a modifiable reference:

```slang
Fruits = [ "apple", "banana", "cherry" ];
ForEach( Fruit, Fruits )
{
    Print( Fruit, "\n" );
};

// Modify in place with &
Numbers = [ 1, 2, 3 ];
ForEach( &Num, Numbers )
{
    Num *= 2;
};
// Numbers is now [ 2, 4, 6 ]
```

### For Loop (Index-Based)

```slang
For( I = 0; I < Size( Fruits ); I++ )
{
    Print( I, ": ", Fruits[ I ], "\n" );
};
```

### ForComponent (Iterates Indices)

When you pass an array to `ForComponent`, it iterates over **indices** (0, 1, 2, ...):

```slang
ForComponent( Idx, Fruits )
{
    Print( Idx, " => ", Fruits[ Idx ], "\n" );
};
```

## Inserting Elements

### ArrayInsert

Inserts one or more null slots before a given index. You then assign values to those slots:

```slang
A = [ "a", "b", "c" ];
ArrayInsert( A, 1, 2 );           // insert 2 nulls before index 1
// A is now [ "a", Null, Null, "b", "c" ]
A[ 1 ] = "x";
A[ 2 ] = "y";
// A is now [ "a", "x", "y", "b", "c" ]
```

To insert a single element:

```slang
A = [ 10, 20, 30 ];
ArrayInsert( A, 1 );              // inserts 1 null before index 1
A[ 1 ] = 15;
// A is now [ 10, 15, 20, 30 ]
```

## Deleting Elements

### ArrayDelete

Removes elements from an array starting at a given index:

```slang
A = [ 1, 2, 3, 4, 5 ];
ArrayDelete( A, 2, 1 );           // delete 1 element at index 2
// A is now [ 1, 2, 4, 5 ]

ArrayDelete( A, 0, 2 );           // delete 2 elements starting at index 0
// A is now [ 4, 5 ]
```

## Extracting Sub-Arrays

### ArrayExtract

Returns a new array containing a portion of the original:

```slang
A = [ 10, 20, 30, 40, 50 ];
Sub = ArrayExtract( A, 1, 3 );    // 3 elements starting at index 1
// Sub is [ 20, 30, 40 ]
```

## Sorting

### Sort

Sorts an array **in place**:

```slang
Numbers = [ 3, 1, 4, 1, 5, 9, 2, 6 ];
Sort( Numbers );
// Numbers is now [ 1, 1, 2, 3, 4, 5, 6, 9 ]
```

### SortTable

Sorts an array of structures by one or more component keys:

```slang
Data = [
    {| "Name" := "Charlie", "Age" := 25 |},
    {| "Name" := "Alice", "Age" := 35 |},
    {| "Name" := "Bob", "Age" := 30 |}
];
SortTable( Data, [ "Age" ] );
// Data is now sorted by Age: Charlie (25), Bob (30), Alice (35)
```

## Removing Duplicates

### ArrayUnique

Removes duplicate elements. Pass `True` to sort first:

```slang
A = [ 3, 1, 2, 1, 3 ];
ArrayUnique( A, True );
// A is now [ 1, 2, 3 ]
```

## Searching

### Finding by Value

Use the `@Array::FindByValue` library function (from standard libraries) or a manual search:

```slang
/****************************************************************
**  Routine: Private::Find In Array
**
**  Returns the index of Value in Arr, or -1 if not found.
****************************************************************/
Private::Find In Array = Func(
    Array( Arr ),
    Any( Value ),
)
Returns( Double() )
{
    For( I = 0; I < Size( Arr ); I++ )
    {
        If( Arr[ I ] == Value )
        {
            Return( I );
        };
    };
    Return( -1 );
};
```

### ComponentExists on Arrays

Check if an index exists:

```slang
A = [ 10, 20, 30 ];
ComponentExists( A, 1 );          // True (index 1 exists)
ComponentExists( A, 5 );          // False (out of bounds)
```

## Transformation with MapCar

`MapCar` applies a function to every element and returns a new array:

```slang
Numbers = [ 1, 2, 3, 4, 5 ];
Doubled = MapCar( \X -> X * 2, Numbers );
// Doubled is [ 2, 4, 6, 8, 10 ]

Names = [ "alice", "bob" ];
Upper Names = MapCar( \S -> Upper( S ), Names );
```

## TableInit

Creates an array of structures from a tabular format. The first sub-array defines column names:

```slang
Employees = TableInit( [
    [ "Name", "Department", "Salary" ],
    [ "Alice", "Engineering", 120000 ],
    [ "Bob", "Marketing", 95000 ],
    [ "Carol", "Engineering", 115000 ],
] );
// Employees[ 0 ].Name = "Alice"
// Employees[ 1 ].Department = "Marketing"
```

Additional key-value pairs can be appended to any row:

```slang
Employees = TableInit( [
    [ "Name", "Dept" ],
    [ "Alice", "Eng", "Level", "Senior" ],
    [ "Bob", "Mkt" ],
] );
// Employees[ 0 ].Level = "Senior"
// ComponentExists( Employees[ 1 ], "Level" ) => False
```

## Practical Patterns

### Filter an Array

```slang
Numbers = [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ];
Evens = [];
ForEach( N, Numbers )
{
    If( Mod( N, 2 ) == 0 )
    {
        Evens &= N;
    };
};
// Evens is [ 2, 4, 6, 8, 10 ]
```

### Accumulate / Reduce

```slang
Numbers = [ 1, 2, 3, 4, 5 ];
Total = 0;
ForEach( N, Numbers )
{
    Total += N;
};
// Total = 15
```

You can also use the built-in `Sum()`:

```slang
Total = Sum( Numbers );           // 15
```

### Array of Structures -- Common Pattern

```slang
Results = [];
ForEach( Name, [ "Alice", "Bob", "Carol" ] )
{
    Results &= {| "Name" := Name, "Score" := 0 |};
};
// Results is an array of 3 structures
```

### Join Array into String

```slang
Parts = [ "usr", "local", "bin" ];
Path = "";
For( I = 0; I < Size( Parts ); I++ )
{
    If( I > 0 )
    {
        Path &= "/";
    };
    Path &= Parts[ I ];
};
// Path = "usr/local/bin"
```

## Quick Reference

| Task | Function / Operator | Example |
|------|---------------------|---------|
| Create | `[ ... ]` | `A = [ 1, 2, 3 ];` |
| Access | `A[ index ]` | `A[ 0 ]` (0-based) |
| Length | `Size( A )` | `Size( [ 1, 2 ] )` => 2 |
| Concatenate | `++` or `ArrayConcat` | `A ++ B` (new), `ArrayConcat( A, B )` (in place) |
| Append | `&=` | `A &= Value;` |
| Insert | `ArrayInsert( A, Idx, Count )` | Inserts null slots |
| Delete | `ArrayDelete( A, Idx, Count )` | Removes elements |
| Extract | `ArrayExtract( A, Idx, Count )` | Returns sub-array |
| Sort | `Sort( A )` | In-place sort |
| Sort structs | `SortTable( A, [ "Key" ] )` | Sort array of structures |
| Unique | `ArrayUnique( A, True )` | Remove duplicates |
| Iterate | `ForEach( El, A )` | Copy; `&El` for reference |
| Transform | `MapCar( Func, A )` | Returns new array |
| Sum | `Sum( A )` | Numeric sum |
| Table | `TableInit( [ [Headers], [Row]... ] )` | Array of structures |
