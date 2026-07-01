# Working with Structures in Slang

## Overview

Structures in Slang are **key-value containers** similar to dictionaries or hash maps. Keys must be strings; values can be any data type. Slang offers three flavors:

| Type | Case Sensitivity | Syntax | Notes |
|------|------------------|--------|-------|
| **Structure** | Case-insensitive keys | `{\| ... \|}` | Most common, keys sorted alphabetically |
| **StructureCase** | Case-sensitive keys | `{\ ... \}` | When you need exact-case key matching |
| **GStructure** | Case-insensitive keys | `GStructure()` | Preserves insertion order |

There is also **Typed Structure** for defining object-like types with members and functions -- see `.github/typestructures/` for that.

## Creating Structures

### Structure (Case-Insensitive) -- Preferred

```slang
// Literal syntax (preferred)
Person = {| "Name" := "Alice", "Age" := 30, "City" := "New York" |};

// Constructor syntax
Person = Structure();
Person.Name = "Alice";
Person.Age = 30;

// Constructor with inline pairs
Person = Structure( "Name", "Alice", "Age", 30 );
```

### StructureCase (Case-Sensitive)

```slang
// Note: backslashes are syntax, NOT escape characters. Do NOT double them.
Config = {\ "apiKey" := "abc123", "ApiKey" := "different-value" \};
// Config has TWO distinct keys because case matters
```

### GStructure (Insertion-Order)

```slang
G = GStructure();
G.Zebra = 1;
G.Apple = 2;
// Keys maintain insertion order: Zebra, Apple
// (Unlike Structure which would sort to: Apple, Zebra)
```

### StructureFromKeys / GStructureFromKeys

Build from parallel arrays of keys and values:

```slang
Keys   = [ "Red", "Green", "Blue" ];
Values = [ 255, 128, 0 ];
Colors = StructureFromKeys( Keys, Values );
// Colors.Red = 255, Colors.Green = 128, Colors.Blue = 0

// Single value initializes all keys:
Flags = StructureFromKeys( [ "A", "B", "C" ], [ False ] );
// All set to False
```

## Accessing Values

### Dot Notation (Preferred -- Faster)

Use when the key is a known literal:

```slang
Print( Person.Name );              // "Alice"
Print( Person.Age );               // 30
```

### Bracket Notation

Use when the key is in a variable or contains special characters:

```slang
Key = "Name";
Print( Person[ Key ] );            // "Alice"
Print( Person[ "Name" ] );         // "Alice"
```

> **Performance:** Dot notation (`.`) is ~25% faster than bracket notation (`[]`). Prefer `.` when the key is a literal.

> **Do NOT** combine dot and brackets: `Person.[ "Name" ]` is **invalid syntax**.

## Modifying Structures

### Setting Values

```slang
Person.Email = "alice@example.com";       // adds new key
Person.Age = 31;                          // updates existing key
```

### Removing Keys with Destroy

```slang
S = {| "A" := 1, "B" := 2, "C" := 3 |};
Destroy( S.B );
// S is now {| "A" := 1, "C" := 3 |}
```

### Union / Merge with `++`

For keys in both structures, the **left-hand** value wins:

```slang
S1 = {| "A" := 1, "B" := 2 |};
S2 = {| "B" := 99, "C" := 3 |};
Merged = S1 ++ S2;
// Merged = {| "A" := 1, "B" := 2, "C" := 3 |}  (B keeps value from S1)
```

### StructureUnion (In-Place Merge)

Merges `S2` into `S1` without overwriting existing keys in `S1`:

```slang
S1 = {| "A" := 1 |};
S2 = {| "A" := 99, "B" := 2 |};
StructureUnion( S1, S2 );
// S1 is now {| "A" := 1, "B" := 2 |}  (A unchanged)
```

## Size

```slang
Count = Size( Person );            // number of keys
```

## Iteration

### ForComponent -- Iterate Keys

Keys are returned in **alphabetical order** (for Structure and StructureCase):

```slang
ForComponent( Key, Person )
{
    Print( Key, " = ", Person[ Key ], "\n" );
};
```

### ForComponentValue -- Iterate Keys and Values

More convenient -- gives both key and value directly:

```slang
ForComponentValue( Key, Value, Person )
{
    Print( Key, " => ", Value, "\n" );
};
```

Modify values in place with `&`:

```slang
Counts = {| "A" := 1, "B" := 2, "C" := 3 |};
ForComponentValue( Key, &Value, Counts )
{
    Value *= 10;
};
// Counts = {| "A" := 10, "B" := 20, "C" := 30 |}
```

## Key Inspection

### Keys and Values

```slang
S = {| "Name" := "Alice", "Age" := 30 |};
K = S.Keys();                     // [ "Age", "Name" ] (sorted)
V = S.Values();                   // [ 30, "Alice" ] (matching key order)
U = S.UnsortedKeys();             // insertion order
```

## Checking for Keys

### ComponentExists

Case-insensitive search (for Structure):

```slang
If( ComponentExists( Person, "Email" ) )
{
    Print( "Has email\n" );
};
```

### ComponentExistsStrict

Same as `ComponentExists` but throws a redbox if the container is invalid:

```slang
ComponentExistsStrict( Person, "Phone" );   // False, no error
ComponentExistsStrict( 5, "Phone" );        // Redbox! 5 is not a container
```

## Safe Value Access

### ComponentTestAndGet

Returns True/False and stores the value in a variable:

```slang
If( ComponentTestAndGet( Person, "Age", Result ) )
{
    Print( "Age is ", Result, "\n" );
}
:
{
    Print( "Age not found\n" );
};
```

### ComponentExtract

Returns the value or a default if the key is missing:

```slang
Email = ComponentExtract( Person, "Email", "no-email@unknown.com" );
// Returns Person.Email if it exists, else "no-email@unknown.com"
```

### ComponentEnsure

Returns the value if key exists; if not, creates it with the given initial value:

```slang
Count = ComponentEnsure( Stats, "Errors", 0 );
// If Stats.Errors doesn't exist, creates it with value 0 and returns 0
```

### ComponentReplace

Replaces a key's value (different from `[]` for certain specialized types):

```slang
ComponentReplace( Person, "Name", "Bob" );
```

## Arithmetic Operators on Structures

Structures support element-wise arithmetic when values are numeric:

```slang
S1 = {| "X" := 10, "Y" := 20 |};
S2 = {| "X" := 1, "Y" := 2 |};

Sum  = S1 + S2;                   // {| "X" := 11, "Y" := 22 |}
Diff = S1 - S2;                   // {| "X" := 9, "Y" := 18 |}
Prod = S1 * S2;                   // {| "X" := 10, "Y" := 40 |}
Quot = S1 / S2;                   // {| "X" := 10, "Y" := 10 |}

// Scalar operations
Doubled = S1 * 2;                 // {| "X" := 20, "Y" := 40 |}

// In-place
S1 += S2;                         // S1 = {| "X" := 11, "Y" := 22 |}
```

## Comparison

```slang
S1 = {| "A" := 1, "B" := 2 |};
S2 = {| "A" := 1, "B" := 2 |};
Print( S1 == S2 );                // True
Print( S1 != S2 );                // False
```

## Practical Patterns

### Counting Occurrences

```slang
Words = [ "apple", "banana", "apple", "cherry", "banana", "apple" ];
Counts = {||};
ForEach( Word, Words )
{
    ComponentEnsure( Counts, Word, 0 );
    Counts[ Word ] += 1;
};
// Counts = {| "apple" := 3, "banana" := 2, "cherry" := 1 |}
```

### Building a Lookup Table

```slang
Codes = {|
    "US" := "United States",
    "GB" := "United Kingdom",
    "JP" := "Japan"
|};

Country Code = "US";
If( ComponentExists( Codes, Country Code ) )
{
    Print( Codes[ Country Code ], "\n" );  // "United States"
};
```

### Configuration with Defaults

```slang
/****************************************************************
**  Routine: Private::Get Config
**
**  Merges user config with defaults. User values take priority.
****************************************************************/
Private::Get Config = Func(
    Structure( User Config ),
)
Returns( Structure() )
{
    Defaults = {|
        "Timeout"  := 30,
        "Retries"  := 3,
        "Verbose"  := False
    |};

    // User Config wins for overlapping keys (left side of ++)
    Return( User Config ++ Defaults );
};

My Config = @Private::Get Config( {| "Timeout" := 60 |} );
// My Config = {| "Retries" := 3, "Timeout" := 60, "Verbose" := 0 |}
```

### Array of Structures

```slang
Employees = [
    {| "Name" := "Alice", "Dept" := "Eng", "Salary" := 120000 |},
    {| "Name" := "Bob", "Dept" := "Mkt", "Salary" := 95000 |},
    {| "Name" := "Carol", "Dept" := "Eng", "Salary" := 115000 |}
];

// Sort by salary
SortTable( Employees, [ "Salary" ] );

// Filter engineering
Eng = [];
ForEach( E, Employees )
{
    If( E.Dept == "Eng" )
    {
        Eng &= E;
    };
};
```

### Converting Between Types

```slang
// Structure to keys/values
S = {| "A" := 1, "B" := 2 |};
K = S.Keys();                     // [ "A", "B" ]
V = S.Values();                   // [ 1, 2 ]

// Statistics
Stats = StructureStatistics( S );
Print( Stats, "\n" );
```

## Quick Reference

| Task | Function / Operator | Example |
|------|---------------------|---------|
| Create | `{\| ... \|}` | `S = {\| "K" := V \|};` |
| Create (case-sensitive) | `{\ ... \}` | `S = {\ "k" := V \};` |
| Create from arrays | `StructureFromKeys( K, V )` | Two parallel arrays |
| Access (literal key) | `S.Key` | Preferred, faster |
| Access (variable key) | `S[ Var ]` | Dynamic key lookup |
| Size | `Size( S )` | Number of keys |
| Check key | `ComponentExists( S, K )` | Returns True/False |
| Get or default | `ComponentExtract( S, K, Def )` | Returns value or default |
| Get with flag | `ComponentTestAndGet( S, K, V )` | Returns True/False, sets V |
| Ensure key | `ComponentEnsure( S, K, Init )` | Creates if missing |
| Replace | `ComponentReplace( S, K, V )` | Replace value for key |
| Remove key | `Destroy( S.Key )` | Removes key from structure |
| Merge (new) | `S1 ++ S2` | Left-hand values win |
| Merge (in place) | `StructureUnion( S1, S2 )` | S1 gains S2's new keys |
| Iterate keys | `ForComponent( K, S )` | Alphabetical order |
| Iterate key+value | `ForComponentValue( K, V, S )` | Use `&V` to modify |
| Keys array | `S.Keys()` | Sorted keys |
| Values array | `S.Values()` | Values in key order |
| Compare | `==`, `!=` | Deep equality |
| Arithmetic | `+`, `-`, `*`, `/` | Element-wise on numerics |
